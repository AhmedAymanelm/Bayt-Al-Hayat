import asyncio
from app.utils.settings_helper import get_env_or_db
import httpx
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

async def main():
    try:
        api_key = await get_env_or_db("astrology_api_key")
        print("API Key exists:", bool(api_key))
        if not api_key:
            return
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        url = "https://api.astrology-api.io/api/v3/data/house-cusps"
        payload = {
            "subject": {
                "name": "User",
                "birth_data": {
                    "year": 1998,
                    "month": 1,
                    "day": 15,
                    "hour": 14, # 2 PM
                    "minute": 0,
                    "latitude": 30.0444, # Cairo
                    "longitude": 31.2357, # Cairo
                    "timezone": 2 # Egypt time is UTC+2
                }
            }
        }
        
        async with httpx.AsyncClient() as client:
            res = await client.post(url, json=payload, headers=headers)
            print("Timezone 2 status:", res.status_code)
            try:
                print("Timezone 2 ascendant:", [c for c in res.json().get('data', {}).get('cusps', []) if c.get('house') == 1][0].get('sign'))
            except: pass

        payload["subject"]["birth_data"]["timezone"] = "UTC"
        async with httpx.AsyncClient() as client:
            res = await client.post(url, json=payload, headers=headers)
            print("Timezone UTC status:", res.status_code)
            try:
                print("Timezone UTC ascendant:", [c for c in res.json().get('data', {}).get('cusps', []) if c.get('house') == 1][0].get('sign'))
            except: pass
    except Exception as e:
        print(e)

asyncio.run(main())
