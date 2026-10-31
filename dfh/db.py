import os
from sqlalchemy import create_engine, event

DB_URL = os.getenv("DATABASE_URL", "sqlite:///data/dfh.db")


def get_engine(url=None):
    eng = create_engine(url or DB_URL, future=True)
    if eng.dialect.name == "sqlite":
        @event.listens_for(eng, "connect")
        def _fk(dbapi_con, _):
            dbapi_con.execute("PRAGMA foreign_keys=ON")
    return eng
