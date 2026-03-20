import asyncio
import asyncpg
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/subscription_bot")

async def reset_db():
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        print("Clearing tables...")
        await conn.execute("TRUNCATE TABLE subscriptions CASCADE;")
        await conn.execute("TRUNCATE TABLE payments CASCADE;")
        await conn.execute("TRUNCATE TABLE users CASCADE;")
        print("✅ Database reset complete!")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(reset_db())
