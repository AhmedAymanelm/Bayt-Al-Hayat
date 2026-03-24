import asyncio
import os
import uuid
import bcrypt
from datetime import date, datetime
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

async def run():
    if not DATABASE_URL:
        print("❌ Error: DATABASE_URL is not set.")
        return

    print("🔌 Connecting to database...")
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Check if user exists by querying the table directly
        res = await session.execute(text("SELECT id FROM users WHERE email = 'admin@baytalhayat.com'"))
        row = res.fetchone()
        
        hp = get_password_hash("123456")
        if not row:
            uid = str(uuid.uuid4())
            await session.execute(text(
                "INSERT INTO users (id, email, hashed_password, fullname, date_of_birth, place_of_birth, is_active, is_verified, is_admin, created_at) "
                "VALUES (:id, :email, :hp, :fullname, :dob, :pob, :ia, :iv, :is_admin, :ca)"
            ), {
                "id": uid, "email": "admin@baytalhayat.com", "hp": hp, "fullname": "Super Admin", 
                "dob": date(1990, 1, 1), "pob": "Cairo", "ia": True, "iv": True, "is_admin": True, "ca": datetime.utcnow()
            })
            print("✅ Admin user CREATED successfully. (Email: admin@baytalhayat.com | Pass: 123456)")
        else:
            await session.execute(text(
                "UPDATE users SET hashed_password = :hp, is_active = :ia, is_verified = :iv, is_admin = :is_admin WHERE email = 'admin@baytalhayat.com'"
            ), {"hp": hp, "ia": True, "iv": True, "is_admin": True})
            print("✅ Admin user UPDATED successfully. (Email: admin@baytalhayat.com | Pass: 123456)")
        await session.commit()
    print("🎉 Done!")

if __name__ == "__main__":
    asyncio.run(run())
