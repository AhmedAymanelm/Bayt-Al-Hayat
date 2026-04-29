import asyncio
from sqlalchemy import text
from app.database import engine, Base

# Import all models to ensure they are registered with Base metadata
from app.auth.models import User
from app.models.history import AssessmentHistory
from app.models.payment import PaymentRecord
from app.models.settings import SystemSetting
from app.models.question import AssessmentQuestion
from app.models.subscription import UserSubscription

async def upgrade_db():
    async with engine.begin() as conn:
        print("Creating missing tables (if any)...")
        await conn.run_sync(Base.metadata.create_all)
        
        print("Adding free_trial_used to users table...")
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN free_trial_used BOOLEAN DEFAULT FALSE;"))
            print("Successfully added free_trial_used column.")
        except Exception as e:
            if "already exists" in str(e):
                print("Column free_trial_used already exists.")
            else:
                print(f"Error adding column: {e}")

if __name__ == "__main__":
    asyncio.run(upgrade_db())
