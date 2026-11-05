"""A coherent committed view for passive financial and experiment reads."""

from contextlib import contextmanager

from sqlalchemy.orm import Session


@contextmanager
def committed_snapshot(session):
    with session.get_bind().connect() as conn:
        if conn.dialect.name == "postgresql":
            conn = conn.execution_options(isolation_level="REPEATABLE READ")
        with conn.begin():
            if conn.dialect.name == "sqlite":
                conn.exec_driver_sql("BEGIN")
            elif conn.dialect.name == "postgresql":
                conn.exec_driver_sql("SET TRANSACTION READ ONLY")
            with Session(bind=conn, autoflush=False) as snapshot:
                yield snapshot
