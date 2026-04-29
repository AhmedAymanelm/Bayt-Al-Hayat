import os
from sqlalchemy import select
from app.database import async_session_maker
from app.models.settings import SystemSetting

async def get_env_or_db(key_name: str, env_override: str = None) -> str:
    """
    Tries to retrieve the value from the DB. 
    If not in the DB, falls back to the .env file.
    key_name is typically the lowercase DB key matching the uppercase ENV variable, 
    e.g., 'openai_api_key' for 'OPENAI_API_KEY'.
    """
    db_key = key_name.lower()
    env_key = env_override or key_name.upper()
    
    try:
        async with async_session_maker() as session:
            result = await session.execute(select(SystemSetting).where(SystemSetting.key == db_key))
            setting = result.scalar_one_or_none()
            if setting and setting.value:
                return setting.value
    except Exception as e:
        print(f"Warning: Failed to fetch {db_key} from DB, falling back to .env: {e}")
        
    return os.getenv(env_key) or ""


async def get_random_setting_item(key_name: str) -> str:
    """Retrieves a comma-separated setting and returns one random item from it."""
    import random
    raw_value = await get_env_or_db(key_name)
    if not raw_value:
        return ""
    items = [v.strip() for v in raw_value.split(",") if v.strip()]
    if not items:
        return ""
    return random.choice(items)
