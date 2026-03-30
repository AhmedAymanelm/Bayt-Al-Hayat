import asyncio
from sqlalchemy import select
from app.database import async_session_maker
from app.models.settings import SystemSetting

async def list_models():
    async with async_session_maker() as session:
        res = await session.execute(select(SystemSetting).where(SystemSetting.group == "ai_models"))
        rows = res.scalars().all()
        for r in rows:
            print(f"Key: {r.key}, Label: {r.label}")

if __name__ == "__main__":
    asyncio.run(list_models())
