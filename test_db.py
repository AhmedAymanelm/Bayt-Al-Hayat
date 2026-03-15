import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.auth.models import User
import os

from dotenv import load_dotenv
load_dotenv()

engine = create_async_engine(os.getenv("DATABASE_URL"))
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def test():
    async with async_session() as session:
        result = await session.execute(select(User.email).limit(5))
        users = result.scalars().all()
        print("Users in DB:", users)

asyncio.run(test())
