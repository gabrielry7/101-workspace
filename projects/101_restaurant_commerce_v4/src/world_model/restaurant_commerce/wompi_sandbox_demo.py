"""Run a fresh, loopback-only Wompi sandbox with synthetic restaurant data."""

import argparse
import json
import os
import secrets
from pathlib import Path

import uvicorn

from .api import create_app
from .db import init_schema, make_engine, session_factory
from .models import RestaurantCommerceProfile
from .seed import DEMO_BUSINESS_ID, seed_demo
from .wompi_sandbox import NAME, SandboxKeys, WompiSandboxProvider


def application(
    run_dir: Path, keys_path: Path, port: int, *, resume=False, return_url=None, api_only=False, receiver_config=None
):
    keys = SandboxKeys.load(keys_path)
    if not resume and not return_url and not api_only:
        raise ValueError(
            "Hosted checkout requires --return-url with a public HTTPS origin; "
            "use --api-only only for protocol tests"
        )
    if return_url:
        from urllib.parse import urlsplit

        parsed = urlsplit(return_url)
        if parsed.scheme != "https" or parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("Wompi hosted checkout requires a public HTTPS return URL")
    if resume:
        config = json.loads((run_dir / "local-config.json").read_text())
        if config["port"] != port:
            raise ValueError("Resume must use the original port to preserve browser recovery")
    else:
        run_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
        config = {
            "port": port,
            "access_secret": secrets.token_hex(32),
            "return_url": return_url or f"http://127.0.0.1:{port}/",
            "api_only": api_only,
        }
        fd = os.open(run_dir / "local-config.json", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(config, stream)
    engine = make_engine("sqlite:///" + str((run_dir / "sandbox.db").resolve()))
    if not resume:
        init_schema(engine)
        with session_factory(engine)() as session:
            seed_demo(session)
            profile = session.get(RestaurantCommerceProfile, DEMO_BUSINESS_ID)
            profile.payment_provider = NAME
            profile.display_name = "Restaurante de prueba · Sin dinero real"
            profile.delivery_enabled = False
            session.commit()
    adapter = WompiSandboxProvider(
        keys,
        business_id=DEMO_BUSINESS_ID,
        return_url=config.get("return_url", f"http://127.0.0.1:{port}/"),
    )
    if receiver_config:
        from .wompi_receiver import SandboxReceiver
        adapter.receiver = SandboxReceiver.load(receiver_config)
    return create_app(
        engine=engine,
        auto_init_schema=False,
        environment="sandbox",
        demo_mode=False,
        public_access_secret=config["access_secret"],
        wompi_sandbox=adapter,
        payment_recovery_interval_seconds=5,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument(
        "--keys-file",
        type=Path,
        default=Path.home() / ".config/101-world-model/wompi-sandbox/credentials.json",
    )
    parser.add_argument("--port", type=int, default=8876)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--receiver-config", type=Path, help="Private HTTPS sandbox inbox configuration")
    parser.add_argument(
        "--return-url", help="Public HTTPS storefront origin, for example a temporary test tunnel"
    )
    parser.add_argument(
        "--api-only",
        action="store_true",
        help="Protocol tests only; loopback return URLs cannot load Wompi hosted checkout",
    )
    args = parser.parse_args()
    app = application(
        args.run_dir,
        args.keys_file,
        args.port,
        resume=args.resume,
        return_url=args.return_url,
        api_only=args.api_only,
        receiver_config=args.receiver_config,
    )
    uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
