import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sbp.config import settings

Base = sqlalchemy.orm.declarative_base()

engine = create_engine(
    f"sqlite:///{settings.repository.path / 'db.sqlite'}",
    echo_pool=True,
    pool_pre_ping=True,
    pool_use_lifo=True,
    pool_reset_on_return="rollback",
)
session_factory = sessionmaker(bind=engine)
