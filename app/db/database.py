from sqlalchemy import create_engine, Engine
from sqlmodel import SQLModel

from app.config import Config

config = Config.get_config()


def get_engine() -> Engine:
    sql_db_url = f"postgresql+psycopg2://{config.POSTGRESQL_USERNAME}:{config.POSTGRESQL_PASSWORD}@{config.POSTGRESQL_HOST}/autoplex"
    return create_engine(sql_db_url)


engine: Engine = get_engine()


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
