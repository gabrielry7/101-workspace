"""Explicit offline evidence upgrade; never fabricates historical costs."""

from sqlalchemy import inspect, text

from .loyalty_assignment_migrations import assignment_schema_ready
from .loyalty_measurement_models import MEASUREMENT_TABLES
from .loyalty_migrations import configuration_schema_ready
from .models import Base

TABLE = next(iter(MEASUREMENT_TABLES))
SQLITE, POSTGRES = {}, {}
for op, kind in (("UPDATE", 19), ("DELETE", 11)):
    name = TABLE + "_" + op.lower()
    SQLITE[name] = (
        f"CREATE TRIGGER {name} BEFORE {op} ON {TABLE} BEGIN SELECT RAISE(ABORT, 'Immutable measurement evidence'); END"
    )
    POSTGRES[name] = (
        TABLE,
        "BEGIN RAISE EXCEPTION 'Immutable measurement evidence'; END",
        kind,
    )

check = f"""((NEW.order_id IS NOT NULL AND NEW.target='order:' || NEW.order_id
 AND EXISTS (SELECT 1 FROM restaurant_orders o WHERE o.id=NEW.order_id AND o.business_id=NEW.business_id))
 OR (NEW.variant_id IS NOT NULL AND NEW.target='variant:' || NEW.variant_id
 AND EXISTS (SELECT 1 FROM restaurant_loyalty_experiment_variants v WHERE v.id=NEW.variant_id AND v.business_id=NEW.business_id)))
 AND ((NEW.revision=1 AND NEW.supersedes_id IS NULL) OR EXISTS
 (SELECT 1 FROM {TABLE} p WHERE p.id=NEW.supersedes_id AND p.business_id=NEW.business_id
 AND p.target=NEW.target AND p.revision=NEW.revision-1))
 AND NOT EXISTS (SELECT 1 FROM {TABLE} existing WHERE existing.id=NEW.id
 OR (existing.business_id=NEW.business_id AND existing.target=NEW.target AND existing.revision=NEW.revision)
 OR (existing.business_id=NEW.business_id AND existing.request_key=NEW.request_key)
 OR (NEW.supersedes_id IS NOT NULL AND existing.supersedes_id=NEW.supersedes_id))"""
name = TABLE + "_scope"
SQLITE[name] = (
    f"CREATE TRIGGER {name} BEFORE INSERT ON {TABLE} WHEN NOT ({check}) BEGIN SELECT RAISE(ABORT, 'Invalid measurement scope or revision'); END"
)
POSTGRES[name] = (
    TABLE,
    f"BEGIN IF NOT ({check}) THEN RAISE EXCEPTION 'Invalid measurement scope or revision'; END IF; RETURN NEW; END",
    7,
)


def measurement_schema_ready(connection, *, required=False, known_tables=None):
    return configuration_schema_ready(
        connection,
        required=required,
        known_tables=known_tables,
        tables=MEASUREMENT_TABLES,
        sqlite_protections=SQLITE,
        postgres_protections=POSTGRES,
    )


def upgrade_loyalty_measurement(engine):
    with engine.begin() as conn:
        if conn.dialect.name == "sqlite":
            conn.exec_driver_sql("BEGIN IMMEDIATE")
        elif conn.dialect.name == "postgresql":
            conn.execute(text("SELECT pg_advisory_xact_lock(101, 31)"))
        else:
            raise RuntimeError(
                "Measurement upgrade supports SQLite and PostgreSQL only"
            )
        if not assignment_schema_ready(conn, required=True):
            raise RuntimeError("Complete the assignment upgrade before measurement")
        if set(inspect(conn).get_table_names()) & MEASUREMENT_TABLES:
            if not measurement_schema_ready(conn, required=True):
                raise RuntimeError("Partial measurement schema requires offline repair")
            return
        Base.metadata.create_all(conn, tables=[Base.metadata.tables[TABLE]])
        for name, sql in SQLITE.items():
            if conn.dialect.name == "sqlite":
                conn.exec_driver_sql(sql)
            else:
                table, body, kind = POSTGRES[name]
                operation = {19: "UPDATE", 11: "DELETE", 7: "INSERT"}[kind]
                conn.exec_driver_sql(
                    f"CREATE FUNCTION {name}() RETURNS trigger LANGUAGE plpgsql AS $$ {body} $$"
                )
                conn.exec_driver_sql(
                    f"CREATE TRIGGER {name} BEFORE {operation} ON {table} FOR EACH ROW EXECUTE FUNCTION {name}()"
                )
        if not measurement_schema_ready(conn, required=True):
            raise RuntimeError("Measurement schema verification failed")
