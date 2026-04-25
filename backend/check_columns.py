import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect('postgresql://noc:noc_dev_password@localhost:5432/noc_db')
    rows = await conn.fetch(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'incidents' ORDER BY ordinal_position"
    )
    print("incidents columns:")
    for r in rows:
        print(" ", r['column_name'])

    # Also check alembic_version
    ver = await conn.fetchval("SELECT version_num FROM alembic_version")
    print("alembic version:", ver)
    await conn.close()

asyncio.run(main())
