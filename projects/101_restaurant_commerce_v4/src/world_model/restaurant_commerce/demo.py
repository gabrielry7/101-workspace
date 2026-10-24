from __future__ import annotations

import argparse

import uvicorn

from .api import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the 101 restaurant-commerce V4 hardened demo")
    parser.add_argument("--db", default="/tmp/101-restaurant-commerce-demo.db")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--operator-token", default="dev-operator")
    args = parser.parse_args()

    app = create_app(
        database_url=f"sqlite:///{args.db}",
        seed=True,
        operator_token=args.operator_token,
    )
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
