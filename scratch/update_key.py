import asyncio
import asyncpg

async def update_key():
    conn = await asyncpg.connect("postgresql://neondb_owner:npg_2DruTd0mzpOY@ep-dry-darkness-amhazwtt-pooler.c-5.us-east-1.aws.neon.tech/abrag?sslmode=require")
    await conn.execute(
        """
        INSERT INTO system_settings (key, value, description)
        VALUES ($1, $2, $3)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """,
        "runway_api_key",
        "key_69c2d8c91431027ea7cb1c4eb4e832ba498ecfd5bd7f6499cb9675a00ef240d50107c6dbc39fac4654d573156bbbd68fc9de9b4c94e0dda20dc5bd7fc74e47ed",
        "RunwayML API Key"
    )
    await conn.close()
    print("Database Updated!")

asyncio.run(update_key())
