"""Current approved manual handoff, complete file hashes, no external action."""

import hashlib
import io
import zipfile
from pathlib import Path

from sqlalchemy import select

from .social_production import asset_check, owned, require
from .social_reviews import canonical, current_time, events, locked_current, scope, technical


def package(session, business, pack_id, app):
    # Serialize against material edits and review decisions; revalidate every export.
    _, rev, doc, approval = locked_current(session, business, pack_id)
    require(approval is not None and approval.digest == rev.digest, "approval_required")
    require(technical(rev,session)["status"] == "passed", "export_output_changed")
    asset, meta = asset_check(session, doc["brief"]["asset_id"], business, current_time())
    require(
        hashlib.sha256(asset.original).hexdigest() == doc["asset_sha256"] == meta["sha256"],
        "export_source_changed",
    )
    files = {
        "post.jpg": rev.image,
        "original": asset.original,
        "caption.txt": doc["caption"],
        "editable.json": rev.document,
    }
    if doc.get("video_output"):
        from .social_video import output, clip_check
        video=output(session,rev,doc)
        files.update({"video.mp4":video.final,"preview.mp4":video.preview,"cover.jpg":video.cover,
                      "timeline.json":canonical(doc["brief"]["video"]),"video-sources.json":canonical(doc["video_sources"])})
        for source in doc["video_sources"]:
            take,_=clip_check(session,business,source["asset_id"])
            files[f"originals/{take.id}.mp4"]=take.original
    if doc.get("design"):
        files.update(
            {
                "design.json": canonical(doc["design"]),
                "fonts.json": canonical(doc["design"]["fonts"]),
                "INTER-LICENSE.txt": (
                    Path(__file__).parent / "web" / "workspace" / "assets" / "INTER-LICENSE.txt"
                ).read_text(),
            }
        )
    files["approval.json"] = canonical(
        {
            "digest": rev.digest,
            "actor_id": approval.actor_id,
            "at": approval.approved_at,
            "scope": "manual_export",
            "binding": scope(rev, doc),
            "mode": getattr(approval, "mode", "legacy_checkbox"),
            "review_id": getattr(approval, "review_id", None),
            "approval_event_id": getattr(approval, "event_id", None),
        }
    )
    files["review.json"] = canonical(
        {
            "contract": doc.get("review_contract"),
            "events": events(session, rev.id),
            "technical": technical(rev,session),
            "commercial": {"value": None, "reason": "not_measured"},
            "legacy_notice": None
            if getattr(approval, "mode", None) == "structured"
            else "Historical checkbox approval; no structured judgments recorded.",
        }
    )
    from .social_job_models import ProductionJob
    from .social_jobs import info as job_info

    production = session.scalar(
        select(ProductionJob)
        .where(
            ProductionJob.business_id == business,
            ProductionJob.result_revision == rev.id,
            ProductionJob.state == "succeeded",
        )
        .order_by(ProductionJob.created_at.desc())
        .limit(1)
    )
    files["production.json"] = canonical(
        job_info(session, production)
        if production
        else {"state": "legacy_synchronous", "attempts": None, "total_cost_microusd": None}
    )
    provider_cost = 0
    if doc.get("proposal_snapshot"):
        from .social_proposal_models import Proposal
        from .social_proposals import proposal_info

        proposal = owned(session, Proposal, doc["proposal_snapshot"]["proposal_id"], business)
        generation_info = job_info(session, session.get(ProductionJob, proposal.job_id))
        files["proposal.json"] = canonical(
            {"proposal": proposal_info(session, proposal, app), "generation": generation_info}
        )
        micro = generation_info["cost"]["provider_microusd"]
        provider_cost = micro / 1_000_000 if micro is not None else None
    files["measurement.json"] = canonical(
        {
            "primary": doc["brief"]["primary_measure"],
            "value": None,
            "reason": "not_published",
            "provider_cost_usd": provider_cost,
            "compute_cost_usd": None,
        }
    )
    from .social_results import pack_receipt_summary, report
    receipt=pack_receipt_summary(session,business,pack_id,rev.id)
    if receipt['post_id']:
        results=report(session,business,receipt['publication_id'])
        files['results.json']=canonical(results)
        measurement=__import__('json').loads(files['measurement.json'])
        primary=results['primary']
        measurement.update(value=primary['value'],reason=primary['reason'],availability=primary['availability'],reporting_basis='owner_report',publication_id=receipt['publication_id'],observation=primary,receipt_count=receipt['receipt_count'])
        files['measurement.json']=canonical(measurement)
    files["README.txt"] = (
        "Paquete para publicación manual\n\n"
        "Usa post.jpg y caption.txt en el destino indicado en approval.json.\n"
        "Revisa el destino; este ZIP no publica ni autoriza una conexión.\n"
        "La aprobación corresponde solo a esta versión y sus archivos.\n"
        "Si cambias el contenido, vuelve a revisarlo.\n"
        "editable.json y design.json conservan las instrucciones.\n"
        "original conserva la fotografía autorizada.\n"
        "No se incluyen fuentes. INTER-LICENSE.txt describe la licencia cuando corresponde.\n"
        "manifest.json enumera bytes y SHA-256 de los archivos excepto el manifiesto.\n"
        "Si existe results.json, contiene observaciones declaradas y sus límites.\n"
        "La aprobación creativa no demuestra un resultado comercial.\n"
    )
    if doc.get("video_output"):
        files["README.txt"] += ("\nEste paquete contiene un montaje de tomas reales: usa video.mp4, cover.jpg y caption.txt.\n"
            "preview.mp4 es una copia pequeña; post.jpg es solo una miniatura para el espacio de trabajo.\n"
            "timeline.json conserva tomas, tiempos, encuadre y sonido; originals/ conserva las tomas autorizadas.\n"
            "No se generaron escenas, música ni transcripción. La revisión completa de sonido y significado es humana.\n")
    files = {
        name: value.encode("utf-8") if isinstance(value, str) else value
        for name, value in files.items()
    }
    files["manifest.json"] = canonical(
        {
            "schema_version": "1",
            "business_id": business,
            "pack_id": pack_id,
            "revision_id": rev.id,
            "digest": rev.digest,
            "approved_scope": scope(rev, doc),
            "source": {
                "asset_id": asset.id,
                "sha256": meta["sha256"],
                "rights_statement": meta["rights_statement"],
                "expires_at": meta["expires_at"],
                "fixture": meta["fixture"],
                "permitted_use": meta["permitted_use"],
                "uploaded_at": meta.get("uploaded_at"),
                "captured_at": meta.get("captured_at"),
            },
            "files": {
                name: {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                for name, data in sorted(files.items())
            },
            "manifest_self_hash": "excluded; not a signature or external authenticity certificate",
        }
    ).encode()
    result = io.BytesIO()
    with zipfile.ZipFile(result, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    session.commit()
    return result.getvalue()
