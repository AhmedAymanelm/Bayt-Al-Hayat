import asyncio
from app.utils.settings_helper import set_dynamic_setting
from app.database import async_session_maker

async def main():
    async with async_session_maker() as session:
        await set_dynamic_setting(session, 'runway_api_key', 'key_69c2d8c91431027ea7cb1c4eb4e832ba498ecfd5bd7f6499cb9675a00ef240d50107c6dbc39fac4654d573156bbbd68fc9de9b4c94e0dda20dc5bd7fc74e47ed')
        await session.commit()
        print("Updated in DB")

asyncio.run(main())
