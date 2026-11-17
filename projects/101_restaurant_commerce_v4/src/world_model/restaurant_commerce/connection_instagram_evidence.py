"""Credential-owned interface for a separate, explicit Instagram evidence import.

This is not the dashboard's bounded summary sync. The caller supplies an existing
staff permission check on every operation; no tokens leave this module. Live use
is disabled unless the owning worker is explicitly qualified/enabled.
"""

import json
import os
import re
from pathlib import Path
from uuid import uuid4

from . import connections as connections
from .connection_google import ConnectionFailure


def refresh_evidence_token(adapter, tokens, now):
    """Opt-in lifecycle for the archive worker; the summary adapter is unchanged.

    Contract: Instagram Login business-login/access-token exchange and refresh.
    Fixture-qualified only; verify with an owned account before live enablement.
    """
    from datetime import datetime, timedelta

    from .staff import aware

    expires = aware(datetime.fromisoformat(tokens["expires_at"]))
    if expires <= now + timedelta(seconds=30):
        raise ConnectionFailure("reconnect_required")
    if tokens.get("evidence_token_kind") == "long_lived":
        if expires - now > timedelta(days=7):
            return tokens
        issued = aware(datetime.fromisoformat(tokens["evidence_token_issued_at"]))
        if now - issued < timedelta(days=1):
            raise ConnectionFailure("token_not_refreshable_yet")
        result = adapter.request(
            "GET",
            "/refresh_access_token",
            params={"grant_type": "ig_refresh_token", "access_token": tokens["access_token"]},
        )
    else:
        result = adapter.request(
            "GET",
            "/access_token",
            params={
                "grant_type": "ig_exchange_token",
                "client_secret": adapter.client_secret,
                "access_token": tokens["access_token"],
            },
        )
    lifetime = result.get("expires_in")
    token = result.get("access_token")
    if (
        not isinstance(token, str)
        or not token
        or type(lifetime) is not int
        or not 60 < lifetime <= 60 * 86400
    ):
        raise ConnectionFailure("invalid_provider_response")
    return {
        **tokens,
        "access_token": token,
        "expires_at": (now + timedelta(seconds=lifetime)).isoformat(),
        "evidence_token_kind": "long_lived",
        "evidence_token_issued_at": now.isoformat(),
    }


class EvidenceClient:
    def __init__(
        self,
        factory,
        runtime,
        *,
        business_id,
        account_id,
        generation,
        permission,
        enable_live=False,
        downloader=None,
        state_path=None,
        manage_token_lifecycle=False,
    ):
        if runtime.provider != "instagram":
            raise ValueError("Instagram runtime required")
        if runtime.mode == "live" and not enable_live:
            raise ConnectionFailure("evidence_import_not_qualified")
        if not callable(permission):
            raise ValueError("A current staff permission check is required")
        self.factory, self.runtime = factory, runtime
        self.business_id, self.account_id = str(business_id), str(account_id)
        self.generation, self.permission = generation, permission
        self.downloader = downloader
        self.manage_token_lifecycle = manage_token_lifecycle
        self.allowed_media = set()
        self.allowed_urls = set()
        self.state_path = Path(state_path) if state_path else None
        if self.state_path and self.state_path.exists():
            saved = json.loads(self.state_path.read_text())
            if saved["scope"] != self.scope():
                raise ConnectionFailure("connection_changed")
            self.allowed_media = set(saved["media"])
            self.allowed_urls = set(saved["urls"])

    def scope(self):
        return dict(
            business_id=self.business_id, account_id=self.account_id, generation=self.generation
        )

    def save(self):
        if not self.state_path:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.state_path.with_name("." + uuid4().hex + ".tmp")
        try:
            with temp.open("x") as f:
                json.dump(
                    dict(
                        scope=self.scope(),
                        media=sorted(self.allowed_media),
                        urls=sorted(self.allowed_urls),
                    ),
                    f,
                )
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp, self.state_path)
        finally:
            temp.unlink(missing_ok=True)

    def _row(self, session):
        self.permission(session, self.business_id, "settings.write")
        row = connections.find(session, self.business_id, self.runtime)
        if (
            row is None
            or row.generation != self.generation
            or row.selected != self.account_id
            or row.state not in {"connected", "partial", "sync_error"}
            or not row.secret
        ):
            raise ConnectionFailure("connection_changed")
        return row

    def authorize(self):
        with self.factory() as session:
            row = self._row(session)
            original = self.runtime.open(row.secret)
            tokens = original
            tokens = (
                refresh_evidence_token(self.runtime.adapter, tokens, self.runtime.clock())
                if self.manage_token_lifecycle
                else self.runtime.adapter.refresh(tokens, self.runtime.clock())
            )
            if str(tokens.get("user_id")) != self.account_id:
                raise ConnectionFailure("account_identity_mismatch")
            # Refresh may involve network; fence against a simultaneous disconnect
            # before saving the updated encrypted token.
            if tokens != original:
                row = connections.lock(session, row.id)
                self._row(session)
                row.secret = self.runtime.seal(tokens)
                session.commit()
        return dict(
            business_id=self.business_id, account_id=self.account_id, generation=self.generation
        )

    def _token(self):
        self.authorize()
        with self.factory() as session:
            return self.runtime.open(self._row(session).secret)["access_token"]

    def get(self, resource, params):
        if not re.fullmatch(r"[0-9]+(?:/(?:media|children))?", resource):
            raise ConnectionFailure("invalid_provider_resource")
        native = resource.split("/")[0]
        if native != self.account_id and native not in self.allowed_media:
            raise ConnectionFailure("unobserved_media_resource")
        if set(params) - {"fields", "limit", "after"}:
            raise ConnectionFailure("invalid_provider_resource")
        fields = set(str(params.get("fields", "")).split(","))
        allowed = {
            "id",
            "user_id",
            "username",
            "name",
            "profile_picture_url",
            "caption",
            "media_type",
            "media_url",
            "thumbnail_url",
            "permalink",
            "timestamp",
        }
        if not fields <= allowed:
            raise ConnectionFailure("invalid_provider_resource")
        value = self.runtime.adapter.request(
            "GET", f"/{self.runtime.adapter.version}/{resource}", token=self._token(), params=params
        )
        self.authorize()
        rows = value.get("data", [value])
        if not isinstance(rows, list):
            raise ConnectionFailure("invalid_provider_response")
        for item in rows:
            if not isinstance(item, dict):
                raise ConnectionFailure("invalid_provider_response")
            if item.get("id") and re.fullmatch(r"[0-9]+", str(item["id"])):
                self.allowed_media.add(str(item["id"]))
            for field in ("media_url", "thumbnail_url", "profile_picture_url"):
                if item.get(field):
                    self.allowed_urls.add(item[field])
        self.save()
        return value

    def download(self, url, path):
        self.authorize()
        if url not in self.allowed_urls:
            raise ConnectionFailure("unobserved_media_location")
        # The archive worker injects its pinned-public-IP, bounded media downloader.
        # Do not forward the Instagram token to a media/CDN URL.
        if self.downloader is None:
            raise ConnectionFailure("media_downloader_unavailable")
        result = self.downloader(url, path)
        self.authorize()
        return result


def run_import(
    factory,
    runtime,
    *,
    config,
    runs,
    permission,
    downloader,
    run_id=None,
    enable_live=False,
    execute_models=False,
    model_options=None,
    manage_token_lifecycle=True,
):
    """Called by an explicitly authorized worker with both packages installed.

    Root coordinator receives only this scoped client. Credential reads, refresh,
    permission checks and connection-generation fences remain with commerce.
    No merchant route or automatic job starts this operation yet.
    """
    from world_model.business_evidence.official import OfficialAdapter
    from world_model.business_evidence.pipeline import execute

    if (
        not config.instagram
        or config.instagram.route != "official"
        or config.instagram.mode != "collect"
    ):
        raise ValueError("An explicit official collection configuration is required")
    business = str(config.business_id)
    with factory() as session:
        permission(session, business, "settings.write")
        row = connections.find(session, business, runtime)
        if not row or row.selected != config.instagram.account_id:
            raise ConnectionFailure("account_identity_mismatch")
        generation = row.generation
    client = EvidenceClient(
        factory,
        runtime,
        business_id=business,
        account_id=config.instagram.account_id,
        generation=generation,
        permission=permission,
        enable_live=enable_live,
        downloader=downloader,
        state_path=config.instagram.archive / "analysis" / f"official-scope-{generation}.json",
        manage_token_lifecycle=manage_token_lifecycle,
    )
    adapter = OfficialAdapter(
        client,
        business_id=business,
        account_id=config.instagram.account_id,
        generation=generation,
        max_requests=config.instagram.max_requests,
    )
    if run_id:
        saved = runs.get(run_id)
        if saved["config"] != config.model_dump(mode="json"):
            raise ValueError("Resume must use the saved configuration")
    else:
        run_id = runs.create(config)
    return execute(
        runs,
        run_id,
        acquire=True,
        execute_models=execute_models,
        adapters={"instagram": adapter},
        model_options=model_options,
    )
