from dataclasses import dataclass

from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from postnatal_pulse.config import AppSettings


METADATA = MetaData()


@dataclass(frozen=True, slots=True)
class DatabaseHandle:
    engine: AsyncEngine
    pool_state: str


def _normalise_database_url(raw_url: str) -> str:
    if raw_url.startswith("postgres://"):
        return "postgresql+psycopg://" + raw_url[len("postgres://"):]
    if raw_url.startswith("postgresql://") and "+" not in raw_url.split("://", 1)[0]:
        return "postgresql+psycopg://" + raw_url[len("postgresql://"):]
    return raw_url


async def create_database_handle(settings: AppSettings) -> DatabaseHandle | None:
    if settings.database_url is None or settings.database_url.strip() == "":
        return None

    engine = create_async_engine(
        _normalise_database_url(settings.database_url),
        pool_recycle=300,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
    )
    try:
        async with engine.begin() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        await engine.dispose()
        return DatabaseHandle(engine=engine, pool_state="error")

    return DatabaseHandle(engine=engine, pool_state="connected")


async def dispose_database_handle(handle: DatabaseHandle | None) -> None:
    if handle is None:
        return
    await handle.engine.dispose()
