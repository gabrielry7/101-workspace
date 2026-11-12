"""Explicit additive social schema upgrade for the existing workspace database."""

from fastapi import HTTPException
from sqlalchemy import inspect


def social_tables():
    from .social_production import Approval, Asset, Pack, Revision
    from .social_uploads import Upload

    from .social_context import Context, ContextVersion, FactDependency
    return [model.__table__ for model in (Asset, Pack, Revision, Approval, Upload, Context, ContextVersion, FactDependency)]


def schema_ready(bind):
    inspector = inspect(bind)
    names = set(inspector.get_table_names())
    return all(
        table.name in names
        and set(table.columns.keys()) <= {c["name"] for c in inspector.get_columns(table.name)}
        for table in social_tables()
    )


def require_ready(session):
    if not schema_ready(session.connection()):
        raise HTTPException(503, "Contenido aún no está disponible. Contacta al equipo de 101.")


def upgrade_social(engine):
    """Run offline after backup. Existing incomplete tables require manual review."""
    tables = social_tables()
    with engine.begin() as connection:
        inspector = inspect(connection)
        names = set(inspector.get_table_names())
        if "restaurant_commerce_profiles" not in names:
            raise RuntimeError("Initialize the existing commerce schema first")
        for table in tables:
            if table.name in names:
                actual = {c["name"] for c in inspector.get_columns(table.name)}
                if not set(table.columns.keys()) <= actual:
                    raise RuntimeError("Incomplete social schema; review before upgrade")
        for table in tables:
            table.create(connection, checkfirst=True)
        if not schema_ready(connection):
            raise RuntimeError("Social schema is not ready")

        from .social_context import backfill_legacy
        backfill_legacy(connection)
