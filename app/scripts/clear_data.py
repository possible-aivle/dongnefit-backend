import asyncio
import logging

from sqlalchemy import delete

from app.database import async_session_maker
from app.models import (
    AdminActivity,
    BlogPost,
    Discussion,
    DiscussionLike,
    DiscussionReply,
    FileStorage,
    Neighborhood,
    Notification,
    NotificationSettings,
    Report,
    ReportCategory,
    ReportReview,
    User,
    UserRole,
    ViolationComplaint,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def clear_database():
    """Clear database data while preserving admin users."""
    logger.info("🧹 Clearing database...")

    async with async_session_maker() as session:
        try:
            # Order based on foreign key dependencies
            tables_to_clear = [
                DiscussionLike,
                ReportReview,
                DiscussionReply,
                ViolationComplaint,
                Report,
                Notification,
                NotificationSettings,
                FileStorage,
                Discussion,
                BlogPost,
                AdminActivity,
            ]

            for table in tables_to_clear:
                await session.execute(delete(table))
                logger.info(f"✓ Cleared {table.__tablename__}")

            # Special case: Users (preserve admins)
            await session.execute(delete(User).where(User.role != UserRole.ADMIN.value))
            logger.info("✓ Cleared users (admin users preserved)")

            # Other tables
            for table in [ReportCategory, Neighborhood]:
                await session.execute(delete(table))
                logger.info(f"✓ Cleared {table.__tablename__}")

            await session.commit()
            logger.info("✅ Database cleared successfully!")
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Database clearing failed: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(clear_database())