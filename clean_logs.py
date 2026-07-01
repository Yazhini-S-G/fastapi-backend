import asyncio

from sqlalchemy import delete

from app.core.database import DBSessionManager
from app.models.activity_log import AdminActivityLog


async def clean_db() -> None:
    async with DBSessionManager.session() as session:
        await session.execute(delete(AdminActivityLog))
        await session.commit()
        print('Activity logs cleared successfully.')


if __name__ == "__main__":
    asyncio.run(clean_db())
