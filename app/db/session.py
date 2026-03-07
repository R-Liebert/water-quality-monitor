from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings

_engine = None
_AsyncSessionLocal = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(settings.DATABASE_URL, echo=False)
    return _engine

def get_session_factory(engine=None):
    if engine:
        return async_sessionmaker(autocommit=False, autoflush=False, bind=engine)
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        _AsyncSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _AsyncSessionLocal

async def get_db():
    async with get_session_factory()() as session:
        yield session