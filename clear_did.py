import asyncio
from sqlalchemy import delete
from app.database import async_session_maker
from app.models.settings import SystemSetting

async def clear_did():
    async with async_session_maker() as session:
        await session.execute(delete(SystemSetting).where(SystemSetting.key.in_(["d_id_api_key", "did_api_key"])))
        await session.commit()
    print("D-ID completely removed from database.")

if __name__ == "__main__":
    asyncio.run(clear_did())
