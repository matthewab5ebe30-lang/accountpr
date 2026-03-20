import asyncio
import asyncpg
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/subscription_bot")

async def migrate():
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        print("Adding last_name column to users table...")
        await conn.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS last_name VARCHAR(255)
        """)
        print("✅ Migration complete!")
    except Exception as e:
        if "already exists" in str(e):
            print("✅ Column already exists")
        else:
            print(f"❌ Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate())
