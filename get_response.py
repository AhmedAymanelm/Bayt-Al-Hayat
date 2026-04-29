import asyncio
import httpx
import json
from app.routes.payment import _get_fawaterk_config

async def main():
    api_key, _, api_base = await _get_fawaterk_config()
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{api_base}/api/v2/getInvoiceData/7457131", headers=headers)
        with open("scratch_fawaterk.json", "w") as f:
            json.dump(res.json(), f, indent=4)

asyncio.run(main())
