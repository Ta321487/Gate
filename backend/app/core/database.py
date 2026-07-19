from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
url = settings.database_url
# 兼容 .env 中的 mysql+pymysql → 异步驱动
if url.startswith("mysql+pymysql://"):
    url = url.replace("mysql+pymysql://", "mysql+aiomysql://", 1)

engine = create_async_engine(url, echo=False, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_project_columns)


def _migrate_project_columns(sync_conn) -> None:
    """create_all 不补旧表缺列；幂等 ALTER。"""
    from sqlalchemy import text

    dialect = sync_conn.dialect.name
    cols: set[str] = set()
    try:
        if dialect == "sqlite":
            rows = sync_conn.execute(text("PRAGMA table_info(projects)")).fetchall()
            cols = {r[1] for r in rows}
        else:
            rows = sync_conn.execute(
                text(
                    "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='projects'"
                )
            ).fetchall()
            cols = {r[0] for r in rows}
    except Exception:  # noqa: BLE001
        return
    if "password_hash" not in cols:
        try:
            sync_conn.execute(
                text("ALTER TABLE projects ADD COLUMN password_hash VARCHAR(32) DEFAULT 'none'")
            )
        except Exception:  # noqa: BLE001
            pass
