import asyncio
from app.routes.payment import _get_setting

async def main():
    service_type = "final_report_video"
    price_str = await _get_setting(f"price_{service_type}", default="250.00")
    print("Fetched price:", repr(price_str))

asyncio.run(main())
