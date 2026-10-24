from __future__ import annotations

import argparse
from pathlib import Path
import shutil


def main() -> None:
    parser = argparse.ArgumentParser(description="Copy the Restaurant Commerce V4 bundle into a 101 checkout")
    parser.add_argument("repo", type=Path, help="Path to 101-world-model")
    parser.add_argument("--force", action="store_true", help="Allow replacing an existing restaurant_commerce directory")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    source = root / "src" / "world_model" / "restaurant_commerce"
    target = args.repo.resolve() / "src" / "world_model" / "restaurant_commerce"

    if not (args.repo / "src" / "world_model").exists():
        raise SystemExit(f"Not a recognized 101 checkout: {args.repo}")
    if target.exists() and not args.force:
        raise SystemExit(f"Refusing to overwrite existing {target}; inspect/diff it or pass --force explicitly")

    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)

    test_map = {
        "test_restaurant_commerce.py": "test_restaurant_commerce_v1.py",
        "test_growth_v2.py": "test_restaurant_growth_v2.py",
        "test_delivery_v3.py": "test_restaurant_delivery_v3.py",
        "test_payment_boundary.py": "test_restaurant_payment_boundary.py",
        "test_hardening_v4.py": "test_restaurant_hardening_v4.py",
    }
    for src_name, dst_name in test_map.items():
        shutil.copy2(root / "tests" / src_name, args.repo.resolve() / "tests" / dst_name)

    print(f"Copied package to: {target}")
    print("Copied V1/V2/V3/V4 focused test slices into tests/.")
    print("Next: adapt Business FK/Alembic/auth/provider seams described in INTEGRATE_INTO_101.md before committing.")


if __name__ == "__main__":
    main()
