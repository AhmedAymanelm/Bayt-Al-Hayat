import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

async def migrate():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in .env")
        return

    print(f"Connecting to database...")
    engine = create_async_engine(database_url)

    async with engine.begin() as conn:
        print("Renaming column place_of_birth to city_of_birth in 'users' table...")
        try:
            await conn.execute(text("ALTER TABLE users RENAME COLUMN place_of_birth TO city_of_birth;"))
            print("✅ Successfully renamed column in 'users' table.")
        except Exception as e:
            print(f"⚠️ Could not rename column in 'users' table (maybe it was already renamed?): {e}")

        # Also check profile table if exists (some previous versions had it)
        try:
            # Check if profiles table exists first
            result = await conn.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'profiles');"))
            exists = result.scalar()
            if exists:
                await conn.execute(text("ALTER TABLE profiles RENAME COLUMN place_of_birth TO city_of_birth;"))
                print("✅ Successfully renamed column in 'profiles' table.")
        except Exception as e:
            print(f"ℹ️ Profiles table migration skipped or not needed: {e}")

    await engine.dispose()
    print("🚀 Migration complete!")

if __name__ == "__main__":
    asyncio.run(migrate())
