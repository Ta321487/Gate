from collections.abc import AsyncGenerator

from sqlalchemy import event
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

_is_sqlite = url.startswith("sqlite")
_engine_kwargs: dict = {"echo": False, "pool_pre_ping": True}
if _is_sqlite:
    # 默认 busy 等待仅约 5s；生成 Job 与列表轮询同写 projects 时易 database is locked
    _engine_kwargs["connect_args"] = {"timeout": 60}

engine = create_async_engine(url, **_engine_kwargs)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

if _is_sqlite:

    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_on_connect(dbapi_conn, _connection_record) -> None:  # noqa: ANN001
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=60000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


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
    if "delivery_mark" not in cols:
        try:
            sync_conn.execute(
                text("ALTER TABLE projects ADD COLUMN delivery_mark VARCHAR(16) DEFAULT 'none'")
            )
        except Exception:  # noqa: BLE001
            pass
    if "persistence" not in cols:
        try:
            sync_conn.execute(
                text("ALTER TABLE projects ADD COLUMN persistence VARCHAR(16) DEFAULT 'jdbc'")
            )
        except Exception:  # noqa: BLE001
            pass
    if "recommended_persistence" not in cols:
        try:
            sync_conn.execute(
                text(
                    "ALTER TABLE projects ADD COLUMN recommended_persistence "
                    "VARCHAR(16) DEFAULT 'jdbc'"
                )
            )
        except Exception:  # noqa: BLE001
            pass
    if "spring_security" not in cols:
        try:
            sync_conn.execute(
                text(
                    "ALTER TABLE projects ADD COLUMN spring_security "
                    "BOOLEAN DEFAULT 0"
                )
            )
        except Exception:  # noqa: BLE001
            pass
    if "recommended_spring_security" not in cols:
        try:
            sync_conn.execute(
                text(
                    "ALTER TABLE projects ADD COLUMN recommended_spring_security "
                    "BOOLEAN DEFAULT 0"
                )
            )
        except Exception:  # noqa: BLE001
            pass
    if "delivery_review" not in cols:
        try:
            if dialect == "sqlite":
                sync_conn.execute(
                    text("ALTER TABLE projects ADD COLUMN delivery_review JSON DEFAULT '{}'")
                )
            else:
                sync_conn.execute(
                    text("ALTER TABLE projects ADD COLUMN delivery_review JSON")
                )
        except Exception:  # noqa: BLE001
            pass
    try:
        sync_conn.execute(
            text(
                "UPDATE projects SET delivery_mark = 'none' "
                "WHERE delivery_mark IS NULL OR delivery_mark = ''"
            )
        )
    except Exception:  # noqa: BLE001
        pass

    # jobs.kind / jobs.units（答辩 PPT 旁路任务）
    job_cols: set[str] = set()
    try:
        if dialect == "sqlite":
            rows = sync_conn.execute(text("PRAGMA table_info(jobs)")).fetchall()
            job_cols = {r[1] for r in rows}
        else:
            rows = sync_conn.execute(
                text(
                    "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='jobs'"
                )
            ).fetchall()
            job_cols = {r[0] for r in rows}
    except Exception:  # noqa: BLE001
        job_cols = set()
    if job_cols and "kind" not in job_cols:
        try:
            sync_conn.execute(
                text("ALTER TABLE jobs ADD COLUMN kind VARCHAR(32) DEFAULT 'bake'")
            )
        except Exception:  # noqa: BLE001
            pass
    if job_cols and "units" not in job_cols:
        try:
            if dialect == "sqlite":
                sync_conn.execute(text("ALTER TABLE jobs ADD COLUMN units JSON DEFAULT '[]'"))
            else:
                sync_conn.execute(text("ALTER TABLE jobs ADD COLUMN units JSON"))
        except Exception:  # noqa: BLE001
            pass
    try:
        sync_conn.execute(
            text("UPDATE jobs SET kind = 'bake' WHERE kind IS NULL OR kind = ''")
        )
    except Exception:  # noqa: BLE001
        pass
