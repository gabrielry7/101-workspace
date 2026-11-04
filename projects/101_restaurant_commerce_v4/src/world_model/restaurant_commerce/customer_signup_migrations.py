"""Explicit offline upgrade supporting real email-only canonical customers."""
from sqlalchemy import inspect
from .models import Base
from .customer_signup_models import TABLES


def ready(engine):
    inspector = inspect(engine)
    return TABLES <= set(inspector.get_table_names()) and next(
        c['nullable'] for c in inspector.get_columns('restaurant_customers') if c['name'] == 'phone')


def upgrade_signup(engine):
    inspector = inspect(engine)
    columns = inspector.get_columns('restaurant_customers')
    if not next(c['nullable'] for c in columns if c['name'] == 'phone'):
        if engine.dialect.name == 'postgresql':
            with engine.begin() as conn:
                conn.exec_driver_sql('ALTER TABLE restaurant_customers ALTER COLUMN phone DROP NOT NULL')
        elif engine.dialect.name == 'sqlite':
            # Preserve the original schema, extra columns, indexes, triggers and
            # inbound FK targets. Do not rename the old table (SQLite rewrites FKs).
            raw = engine.raw_connection()
            try:
                raw.commit()
                raw.execute('PRAGMA foreign_keys=OFF')
                raw.execute('BEGIN IMMEDIATE')
                sql = raw.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='restaurant_customers'").fetchone()[0]
                if 'phone VARCHAR(40) NOT NULL' not in sql:
                    raise RuntimeError('Unexpected customer phone schema; review migration')
                extra = raw.execute("SELECT sql FROM sqlite_master WHERE tbl_name='restaurant_customers' AND type IN ('index','trigger') AND sql IS NOT NULL").fetchall()
                altered = sql.replace('restaurant_customers', 'restaurant_customers_signup_upgrade', 1).replace('phone VARCHAR(40) NOT NULL', 'phone VARCHAR(40)', 1)
                raw.execute(altered)
                names = ','.join('"' + c['name'].replace('"', '""') + '"' for c in columns)
                raw.execute(f'INSERT INTO restaurant_customers_signup_upgrade ({names}) SELECT {names} FROM restaurant_customers')
                raw.execute('DROP TABLE restaurant_customers')
                raw.execute('ALTER TABLE restaurant_customers_signup_upgrade RENAME TO restaurant_customers')
                for (statement,) in extra:
                    raw.execute(statement)
                if raw.execute('PRAGMA foreign_key_check').fetchall():
                    raise RuntimeError('Customer migration would break foreign keys')
                raw.commit()
            except Exception:
                raw.rollback()
                raise
            finally:
                raw.execute('PRAGMA foreign_keys=ON')
                raw.close()
        else:
            raise RuntimeError('Unsupported offline migration backend')
    Base.metadata.create_all(engine, tables=[Base.metadata.tables[t] for t in TABLES])
