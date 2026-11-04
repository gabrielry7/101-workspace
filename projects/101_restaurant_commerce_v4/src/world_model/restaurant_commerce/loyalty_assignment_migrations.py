"""Optional, explicit offline assignment upgrade. Historical cohorts are never invented."""

from sqlalchemy import inspect, text

from .loyalty_assignment_models import (
    ASSIGNMENT_TABLES,
    LoyaltyAssignment,
    LoyaltyAssignmentOrder,
    LoyaltyEnrollmentDecision,
    LoyaltyExperimentRun,
)
from .loyalty_migrations import configuration_schema_ready
from .models import Base

SQLITE = {}
POSTGRES = {}
for table in sorted(ASSIGNMENT_TABLES):
    for op, kind in (("UPDATE", 19), ("DELETE", 11)):
        name = table + "_" + op.lower()
        SQLITE[name] = (
            f"CREATE TRIGGER {name} BEFORE {op} ON {table} "
            "BEGIN SELECT RAISE(ABORT, 'Immutable loyalty assignment history'); END"
        )
        POSTGRES[name] = (
            table,
            "BEGIN RAISE EXCEPTION 'Immutable loyalty assignment history'; END",
            kind,
        )

# Composite scope binds both observations and causal assignment to canonical owners.
assignment_check = """SELECT 1 FROM restaurant_loyalty_experiment_runs r
 JOIN restaurant_loyalty_experiment_versions e ON e.id=r.experiment_version_id
 JOIN restaurant_loyalty_experiment_variants v ON v.experiment_version_id=e.id
 JOIN restaurant_customers c ON c.id=NEW.customer_id
 JOIN restaurant_loyalty_enrollment_decisions d ON d.id=NEW.eligibility_decision_id
 WHERE r.experiment_id=NEW.experiment_id AND r.business_id=NEW.business_id
 AND e.id=NEW.experiment_version_id AND e.experiment_id=r.experiment_id
 AND v.id=NEW.variant_id AND v.business_id=NEW.business_id
 AND c.business_id=NEW.business_id AND d.business_id=NEW.business_id
 AND d.experiment_version_id=e.id AND d.customer_id=NEW.customer_id AND d.eligible
 AND v.strategy_version_id {null_equal} NEW.strategy_version_id"""
order_check = """SELECT 1 FROM restaurant_orders o WHERE o.id=NEW.order_id
 AND o.business_id=NEW.business_id AND o.customer_id=NEW.customer_id
 AND (NEW.assignment_id IS NULL OR EXISTS (SELECT 1 FROM restaurant_loyalty_assignments a
 WHERE a.id=NEW.assignment_id AND a.experiment_id=NEW.experiment_id
 AND a.business_id=NEW.business_id AND a.customer_id=NEW.customer_id))
 AND (NEW.execution_order_id IS NULL OR EXISTS (
 SELECT 1 FROM restaurant_loyalty_order_snapshots s
 JOIN restaurant_loyalty_assignments a ON a.id=NEW.assignment_id
 WHERE s.order_id=NEW.execution_order_id AND s.version_id=a.strategy_version_id))"""
run_check = """SELECT 1 FROM restaurant_loyalty_experiment_versions e
 WHERE e.id=NEW.experiment_version_id AND e.experiment_id=NEW.experiment_id
 AND e.business_id=NEW.business_id"""
decision_check = """SELECT 1 WHERE NEW.customer_id IS NULL OR EXISTS (
 SELECT 1 FROM restaurant_customers c WHERE c.id=NEW.customer_id
 AND c.business_id=NEW.business_id)"""
for table, check in (
    (LoyaltyAssignment.__tablename__, assignment_check),
    (LoyaltyAssignmentOrder.__tablename__, order_check),
    (LoyaltyExperimentRun.__tablename__, run_check),
    (LoyaltyEnrollmentDecision.__tablename__, decision_check),
):
    name = table + "_insert_scope"
    SQLITE[name] = (
        f"CREATE TRIGGER {name} BEFORE INSERT ON {table} BEGIN SELECT CASE WHEN NOT EXISTS "
        f"({check.format(null_equal='IS')}) "
        "THEN RAISE(ABORT, 'Invalid loyalty assignment scope') END; END"
    )
    body = (
        f"BEGIN IF NOT EXISTS ({check.format(null_equal='IS NOT DISTINCT FROM')}) THEN "
        "RAISE EXCEPTION 'Invalid loyalty assignment scope'; END IF; RETURN NEW; END"
    )
    POSTGRES[name] = (table, body, 7)


def assignment_schema_ready(connection, *, required=False, known_tables=None):
    return configuration_schema_ready(
        connection,
        required=required,
        known_tables=known_tables,
        tables=ASSIGNMENT_TABLES,
        sqlite_protections=SQLITE,
        postgres_protections=POSTGRES,
    )


def installed(session):
    return inspect(session.connection()).has_table("restaurant_loyalty_assignments")


def upgrade_loyalty_assignment(engine):
    from .db import database_ready
    from .loyalty_execution_migrations import execution_schema_ready

    if not database_ready(engine, require_loyalty=True):
        raise RuntimeError(
            "Complete loyalty configuration/execution upgrades; partial schema requires repair"
        )
    with engine.begin() as conn:
        if engine.dialect.name == "sqlite":
            conn.exec_driver_sql("BEGIN IMMEDIATE")
        elif engine.dialect.name == "postgresql":
            conn.execute(text("SELECT pg_advisory_xact_lock(101, 31)"))
        else:
            raise RuntimeError("Assignment upgrade supports SQLite and PostgreSQL only")
        if not execution_schema_ready(conn, required=True):
            raise RuntimeError("Complete the execution upgrade before assignment")
        if set(inspect(conn).get_table_names()) & ASSIGNMENT_TABLES:
            if not assignment_schema_ready(conn, required=True):
                raise RuntimeError("Partial assignment schema requires offline repair")
            return
        Base.metadata.create_all(
            conn, tables=[t for t in Base.metadata.sorted_tables if t.name in ASSIGNMENT_TABLES]
        )
        for name, sql in SQLITE.items():
            if engine.dialect.name == "sqlite":
                conn.exec_driver_sql(sql)
            else:
                table, body, kind = POSTGRES[name]
                operation = {19: "UPDATE", 11: "DELETE", 7: "INSERT"}[kind]
                conn.exec_driver_sql(
                    f"CREATE FUNCTION {name}() RETURNS trigger LANGUAGE plpgsql AS $$ {body} $$"
                )
                conn.exec_driver_sql(
                    f"CREATE TRIGGER {name} BEFORE {operation} ON {table} "
                    f"FOR EACH ROW EXECUTE FUNCTION {name}()"
                )
        if not assignment_schema_ready(conn, required=True):
            raise RuntimeError("Assignment schema verification failed")
