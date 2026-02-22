import asyncio
import logging
import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from faker import Faker
from geoalchemy2 import WKTElement
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import async_session_maker
from app.models import (
    Discussion,
    DiscussionReply,
    DiscussionType,
    FileStorage,
    Neighborhood,
    Notification,
    NotificationType,
    Report,
    ReportCategory,
    ReportComment,
    ReportReview,
    ReportStatus,
    User,
    UserRole,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

fake = Faker(["ko_KR"])

KOREAN_CITIES_DATA = [
    {"city": "서울특별시", "district": "강남구", "name": "역삼동", "lat": 37.5009, "lng": 127.0365, "pnu": "1168010100"},
    {"city": "서울특별시", "district": "송파구", "name": "잠실동", "lat": 37.5144, "lng": 127.1026, "pnu": "1171010100"},
    {"city": "서울특별시", "district": "마포구", "name": "홍대입구", "lat": 37.5563, "lng": 126.9226, "pnu": "1144012200"},
    {"city": "부산광역시", "district": "해운대구", "name": "우동", "lat": 35.1631, "lng": 129.1635, "pnu": "2635010300"},
    {"city": "부산광역시", "district": "부산진구", "name": "서면", "lat": 35.1579, "lng": 129.06, "pnu": "2623010100"},
    {"city": "대구광역시", "district": "중구", "name": "동성로", "lat": 35.8686, "lng": 128.5934, "pnu": "2711010100"},
    {"city": "인천광역시", "district": "연수구", "name": "송도국제도시", "lat": 37.3946, "lng": 126.6434, "pnu": "2818510100"},
    {"city": "광주광역시", "district": "서구", "name": "충장로", "lat": 35.1547, "lng": 126.9127, "pnu": "2914010100"},
    {"city": "대전광역시", "district": "유성구", "name": "대덕연구단지", "lat": 36.3722, "lng": 127.3605, "pnu": "3020010100"},
    {"city": "울산광역시", "district": "남구", "name": "삼산동", "lat": 35.5372, "lng": 129.3183, "pnu": "3114010300"},
    {"city": "세종특별자치시", "district": "한솔동", "name": "정부세종청사", "lat": 36.48, "lng": 127.289, "pnu": "3611025300"},
    {"city": "경기도", "district": "수원시", "name": "영통구", "lat": 37.2571, "lng": 127.0447, "pnu": "4111510100"},
    {"city": "경기도", "district": "성남시", "name": "분당구", "lat": 37.3825, "lng": 127.1197, "pnu": "4113510100"},
    {"city": "경기도", "district": "고양시", "name": "일산동구", "lat": 37.6583, "lng": 126.7747, "pnu": "4128510100"},
    {"city": "경기도", "district": "용인시", "name": "수지구", "lat": 37.3246, "lng": 127.0983, "pnu": "4146310100"},
    {"city": "경기도", "district": "부천시", "name": "원미구", "lat": 37.4989, "lng": 126.7831, "pnu": "4119010100"},
    {"city": "경기도", "district": "안산시", "name": "단원구", "lat": 37.3219, "lng": 126.8309, "pnu": "4127310100"},
    {"city": "경기도", "district": "안양시", "name": "만안구", "lat": 37.3943, "lng": 126.9568, "pnu": "4117110100"},
    {"city": "경기도", "district": "남양주시", "name": "호평동", "lat": 37.6369, "lng": 127.2183, "pnu": "4136010100"},
    {"city": "충청남도", "district": "천안시", "name": "서북구", "lat": 36.8151, "lng": 127.1139, "pnu": "4413310100"},
    {"city": "전라북도", "district": "전주시", "name": "완산구", "lat": 35.8242, "lng": 127.148, "pnu": "4511110100"},
    {"city": "경상남도", "district": "창원시", "name": "성산구", "lat": 35.2541, "lng": 128.6424, "pnu": "4812510100"},
    {"city": "충청북도", "district": "청주시", "name": "서원구", "lat": 36.6424, "lng": 127.489, "pnu": "4311410100"},
    {"city": "강원도", "district": "춘천시", "name": "소양로", "lat": 37.8813, "lng": 127.7298, "pnu": "5111010100"},
    {"city": "제주특별자치도", "district": "제주시", "name": "연동", "lat": 33.4996, "lng": 126.5312, "pnu": "5011025000"},
]


async def seed_data():
    """Seed database with dummy data."""
    logger.info("🚀 Starting database seeding...")

    async with async_session_maker() as session:
        try:
            # 1. Neighborhoods
            logger.info("Creating neighborhoods...")
            neighborhoods = []
            for _ in range(10):
                city_data = random.choice(KOREAN_CITIES_DATA)
                lat_offset = random.uniform(-0.01, 0.01)
                lng_offset = random.uniform(-0.01, 0.01)

                neighborhood = Neighborhood(
                    name=city_data["name"],
                    district=city_data["district"],
                    city=city_data["city"],
                    coordinates={
                        "lat": city_data["lat"] + lat_offset,
                        "lng": city_data["lng"] + lng_offset,
                    },
                    description=f"{city_data['city']} {city_data['district']} {city_data['name']}의 부동산 투자 지역입니다. {fake.sentence()}",
                )
                session.add(neighborhood)
                neighborhoods.append(neighborhood)
            await session.flush()

            # 2. Report Categories
            logger.info("Creating report categories...")
            categories = []
            category_names = ["인프라 분석", "학군 분석", "교통 호재", "상권 분석", "거주 환경"]
            for name in category_names:
                category = ReportCategory(
                    name=name,
                    slug=fake.slug(),
                    description=fake.sentence(),
                )
                session.add(category)
                categories.append(category)
            await session.flush()

            # 3. Users
            logger.info("Creating users...")

            async def get_or_create_user(session, user_data):
                stmt = select(User).where(User.id == user_data.id)
                result = await session.execute(stmt)
                existing_user = result.scalar_one_or_none()
                if existing_user:
                    logger.info(f"User {user_data.id} already exists, skipping.")
                    return existing_user
                session.add(user_data)
                return user_data

            # Real Admin
            admin_user = await get_or_create_user(
                session,
                User(
                    id="google:102949502583098476522",
                    email="kimyoo04@gmail.com",
                    name="유자",
                    profile_image_url="https://lh3.googleusercontent.com/a/ACg8ocJ21568xqp9Js29H2Ty-sfdcm6VOiI5McatsaPZk_801JDoo70m=s96-c",
                    role=UserRole.ADMIN.value,
                    provider="google",
                    is_active=True,
                ),
            )

            # Test Admin
            await get_or_create_user(
                session,
                User(
                    id="admin_test_001",
                    email="admin@example.com",
                    name="관리자",
                    role=UserRole.ADMIN.value,
                    provider="local",
                    is_active=True,
                ),
            )

            # Regular Users
            users = []
            for i in range(10):
                user = await get_or_create_user(
                    session,
                    User(
                        id=f"user_{i + 1:03d}",
                        email=fake.email(),
                        name=fake.name(),
                        role=UserRole.USER.value,
                        provider="local",
                        is_active=True,
                    ),
                )
                users.append(user)
            await session.flush()

            # 4. Reports
            logger.info("Creating reports...")
            reports = []
            for _ in range(20):
                neighborhood = random.choice(neighborhoods)
                category = random.choice(categories)
                city_data = random.choice(KOREAN_CITIES_DATA)
                lat = city_data["lat"] + random.uniform(-0.005, 0.005)
                lng = city_data["lng"] + random.uniform(-0.005, 0.005)
                pnu_suffix = f"{random.randint(1, 9999):04d}{random.randint(1, 9999):04d}0"
                pnu = city_data["pnu"] + pnu_suffix
                # ~60m×60m 사각형 폴리곤 생성
                d_lat = 0.00027  # ~30m
                d_lng = 0.00034  # ~30m
                wkt = (
                    f"POLYGON(({lng - d_lng} {lat - d_lat},"
                    f"{lng + d_lng} {lat - d_lat},"
                    f"{lng + d_lng} {lat + d_lat},"
                    f"{lng - d_lng} {lat + d_lat},"
                    f"{lng - d_lng} {lat - d_lat}))"
                )
                report = Report(
                    author_id=admin_user.id,
                    neighborhood_id=neighborhood.id,
                    category_id=category.id,
                    pnu=pnu,
                    latitude=round(lat, 7),
                    longitude=round(lng, 7),
                    geometry=WKTElement(wkt, srid=4326),
                    title=fake.sentence(nb_words=4),
                    subtitle=fake.sentence(),
                    price=Decimal(random.randint(100, 1000) * 100),
                    summary=fake.paragraph(),
                    content=f"# {fake.sentence()}\n\n" + "\n\n".join(fake.paragraphs(nb=5)),
                    status=ReportStatus.PUBLISHED.value,
                    published_at=datetime.now(UTC).replace(tzinfo=None)
                    - timedelta(days=random.randint(1, 30)),
                    tags=fake.words(nb=5),
                )
                session.add(report)
                reports.append(report)
            await session.flush()

            # 5. File Storages
            logger.info("Creating file storages...")
            for _ in range(5):
                user = random.choice(users)
                file = FileStorage(
                    file_name=fake.file_name(),
                    original_name=fake.file_name(),
                    mime_type="application/octet-stream",
                    file_size=random.randint(1000, 1000000),
                    s3_key=fake.uuid4(),
                    s3_bucket="test-bucket",
                    s3_url=fake.url(),
                    uploaded_by=user.id,
                    is_public=False,
                )
                session.add(file)
            await session.flush()

            # 6. Notifications
            logger.info("Creating notifications...")
            for _ in range(10):
                user = random.choice(users)
                notif = Notification(
                    user_id=user.id,
                    type=random.choice(list(NotificationType)).value,
                    title=fake.sentence(),
                    message=fake.paragraph(),
                    is_read=fake.boolean(),
                )
                session.add(notif)
            await session.flush()

            # 7. Discussions
            logger.info("Creating discussions...")
            discussions = []
            for _ in range(15):
                user = random.choice(users)
                neighborhood = random.choice(neighborhoods)
                discussion = Discussion(
                    user_id=user.id,
                    neighborhood_id=neighborhood.id,
                    title=fake.sentence(),
                    content=fake.paragraph(),
                    type=random.choice(list(DiscussionType)).value,
                )
                session.add(discussion)
                discussions.append(discussion)
            await session.flush()

            # 8. Discussion Replies
            logger.info("Creating discussion replies...")
            for _ in range(30):
                discussion = random.choice(discussions)
                user = random.choice(users)
                reply = DiscussionReply(
                    discussion_id=discussion.id,
                    user_id=user.id,
                    content=fake.paragraph(),
                )
                session.add(reply)
            await session.flush()

            # 9. Report Reviews
            logger.info("Creating report reviews...")
            for _ in range(15):
                report = random.choice(reports)
                user = random.choice(users)
                review = ReportReview(
                    report_id=report.id,
                    user_id=user.id,
                    rating=random.randint(1, 5),
                    content=fake.paragraph(),
                )
                session.add(review)
            await session.flush()

            # 10. Report Comments
            logger.info("Creating report comments...")
            for _ in range(30):
                report = random.choice(reports)
                user = random.choice(users)
                comment = ReportComment(
                    report_id=report.id,
                    user_id=user.id,
                    content=fake.paragraph(),
                )
                session.add(comment)
            await session.flush()

            await session.commit()
            logger.info("✅ Database seeding completed successfully!")

        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Database seeding failed: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(seed_data())
