"""Offline, additive configuration upgrade. Never snapshots invented legacy rules."""

from sqlalchemy import CheckConstraint, UniqueConstraint, inspect, text

from .loyalty_models import LOYALTY_TABLES, POSTGRES_PROTECTIONS, SQLITE_PROTECTIONS
from .models import Base


def configuration_schema_ready(
    connection,
    *,
    required=False,
    known_tables=None,
    tables=LOYALTY_TABLES,
    sqlite_protections=SQLITE_PROTECTIONS,
    postgres_protections=POSTGRES_PROTECTIONS,
):
    inspector = inspect(connection)
    present = set(inspector.get_table_names() if known_tables is None else known_tables) & tables
    if not present:
        return not required
    if present != tables:
        return False
    names = sorted(tables)
    columns = inspector.get_multi_columns(filter_names=names)
    uniques = inspector.get_multi_unique_constraints(filter_names=names)
    primary_keys = inspector.get_multi_pk_constraint(filter_names=names)
    check_constraints = inspector.get_multi_check_constraints(filter_names=names)
    foreign_keys = inspector.get_multi_foreign_keys(filter_names=names)
    for name in names:
        table = Base.metadata.tables[name]
        actual = {c["name"]: c for c in columns[(None, name)]}
        if set(actual) != set(table.columns.keys()):
            return False
        for column in table.columns:
            reflected = actual[column.name]
            if reflected["type"]._type_affinity != column.type._type_affinity:
                return False
            if not column.nullable and reflected["nullable"] and not column.primary_key:
                return False
        unique = {tuple(c["column_names"]) for c in uniques[(None, name)]}
        if tuple(primary_keys[(None, name)]["constrained_columns"]) != tuple(
            table.primary_key.columns.keys()
        ):
            return False
        checks = {c["name"] for c in check_constraints[(None, name)]}
        if any(c.name not in checks for c in table.constraints if isinstance(c, CheckConstraint)):
            return False
        if any(
            tuple(c.columns.keys()) not in unique
            for c in table.constraints
            if isinstance(c, UniqueConstraint)
        ):
            return False
        foreign = {
            (tuple(f["constrained_columns"]), f["referred_table"], tuple(f["referred_columns"]))
            for f in foreign_keys[(None, name)]
        }
        for constraint in table.foreign_key_constraints:
            expected = (
                tuple(constraint.column_keys),
                constraint.referred_table.name,
                tuple(e.column.name for e in constraint.elements),
            )
            if expected not in foreign:
                return False

    def normalize(value):
        return " ".join(value.split()).strip().rstrip(";")

    if connection.dialect.name == "sqlite":
        triggers = dict(
            connection.execute(
                text("SELECT name, sql FROM sqlite_master WHERE type='trigger'")
            ).all()
        )
        return all(
            normalize(triggers.get(name, "")) == normalize(sql)
            for name, sql in sqlite_protections.items()
        )
    if connection.dialect.name == "postgresql":
        rows = connection.execute(
            text(
                "SELECT t.tgname, c.relname, t.tgenabled, t.tgtype, p.prosrc, t.tgqual "
                "FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid "
                "JOIN pg_namespace n ON n.oid=c.relnamespace "
                "JOIN pg_proc p ON p.oid=t.tgfoid WHERE n.nspname=current_schema()"
            )
        ).all()
        triggers = {row[0]: row[1:] for row in rows}
        for name, (table, body, trigger_type) in postgres_protections.items():
            actual = triggers.get(name)
            if actual is None or actual[:3] != (table, "O", trigger_type):
                return False
            if normalize(actual[3]) != normalize(body) or actual[4] is not None:
                return False
        return True
    return False


def upgrade_loyalty_configuration(engine):
    from .db import database_ready

    if engine.dialect.name not in {"sqlite", "postgresql"}:
        raise RuntimeError("Loyalty upgrade supports SQLite and PostgreSQL only")
    if not database_ready(engine):
        raise RuntimeError(
            "Complete the existing commerce upgrades; "
            "partial loyalty schema requires offline repair"
        )
    with engine.begin() as connection:
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        else:
            connection.execute(text("SELECT pg_advisory_xact_lock(101, 31)"))
        present = set(inspect(connection).get_table_names()) & LOYALTY_TABLES
        if present:
            if not configuration_schema_ready(connection, required=True):
                raise RuntimeError(
                    "Incomplete loyalty configuration schema; restore or repair offline"
                )
            return
        Base.metadata.create_all(
            connection, tables=[t for t in Base.metadata.sorted_tables if t.name in LOYALTY_TABLES]
        )
        if not configuration_schema_ready(connection, required=True):
            raise RuntimeError("Loyalty schema verification failed")
