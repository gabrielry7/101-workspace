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


def application(run_dir: Path, keys_path: Path, port: int, *, resume=False):
    keys = SandboxKeys.load(keys_path)
    if resume:
        config = json.loads((run_dir / "local-config.json").read_text())
        if config["port"] != port:
            raise ValueError("Resume must use the original port to preserve browser recovery")
    else:
        run_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
        config = {"port": port, "access_secret": secrets.token_hex(32)}
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
        keys, business_id=DEMO_BUSINESS_ID, return_url=f"http://127.0.0.1:{port}/"
    )
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
    args = parser.parse_args()
    app = application(args.run_dir, args.keys_file, args.port, resume=args.resume)
    uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
