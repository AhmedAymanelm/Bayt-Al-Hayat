from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "❌ DATABASE_URL environment variable is required but not set. "
        "Please configure it in your .env file."
    )

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300
)

async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass

async def get_db():
    async with async_session_maker() as session:
        yield session


async def init_db():
    # Import models here to avoid circular imports
    from app.auth.models import User
    from app.models.history import AssessmentHistory
    from app.models.payment import PaymentRecord
    from app.models.settings import SystemSetting
    from app.models.video_cache import VideoCache
    from app.models.question import AssessmentQuestion

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed default questions if table is empty
    await seed_default_questions()


async def seed_default_questions():
    """Seed the database with default psychology & neuroscience questions if none exist."""
    from sqlalchemy import select, func
    from app.models.question import AssessmentQuestion

    async with async_session_maker() as session:
        count = (await session.execute(
            select(func.count(AssessmentQuestion.id))
        )).scalar_one_or_none() or 0

        if count > 0:
            return  # Questions already seeded

        # ── Psychology default questions ──────────────────────────────────
        psychology_questions = [
            {"text": "كيف هو نومك؟", "options": ["مريح ومنتظم", "متقطع أحيانًا", "سيئ أو غير منتظم"]},
            {"text": "إحساسك العام في يومك؟", "options": ["مرتاح ومتوازن", "محتمل", "مستنزف ومتعب"]},
            {"text": "الإحساس المسيطر عليك مؤخرًا؟", "options": ["هدوء واطمئنان", "قلق أو توتر", "حزن أو ثِقل نفسي"]},
            {"text": "قدرتك على الاستمتاع بالأشياء؟", "options": ["طبيعية", "أقل من المعتاد", "شبه معدومة"]},
            {"text": "مستوى القلق أو التفكير الزائد؟", "options": ["قليل", "متوسط", "شديد ومزعج"]},
            {"text": "طاقتك النفسية والجسدية؟", "options": ["جيدة", "متوسطة", "ضعيفة جدًا"]},
            {"text": "نظرتك لنفسك؟", "options": ["إيجابية أو متوازنة", "متذبذبة", "سلبية أو قاسية على نفسي"]},
        ]

        for i, q in enumerate(psychology_questions):
            session.add(AssessmentQuestion(
                assessment_type="psychology",
                order_index=i + 1,
                text=q["text"],
                options=q["options"],
                options_text=None,
                is_active=True,
            ))

        # ── Neuroscience default questions ────────────────────────────────
        neuroscience_questions = [
            {"text": "شدّ العضلات الآن؟", "options": ["A", "B", "C", "D"], "options_text": {"A": "مرتخي في أغلب الجسم", "B": "شدّ متوسط في أكثر من مكان", "C": "شدّ قوي أو تيبّس واضح", "D": "تهدئة ومحاولة استرخاء الآخرين أو النفس"}},
            {"text": "حالة الفك والأسنان الآن؟", "options": ["A", "B", "C", "D"], "options_text": {"A": "الفك مرتخي", "B": "شدّ بسيط", "C": "شدّ قوي أو جزّ", "D": "محاولة تهدئة أو تقليل التوتر"}},
            {"text": "شكل الانتباه البصري الآن؟", "options": ["A", "B", "C", "D"], "options_text": {"A": "نظرة هادئة", "B": "مراقبة نشطة", "C": "تجمّد أو انسحاب بصري", "D": "مراقبة الآخرين لاحتواء الموقف"}},
            {"text": "حالة النبض الآن؟", "options": ["A", "B", "C", "D"], "options_text": {"A": "طبيعي", "B": "أسرع قليلًا", "C": "بطء أو تجمّد", "D": "تغير حسب الآخرين"}},
            {"text": "حالة الهضم الآن؟", "options": ["A", "B", "C", "D"], "options_text": {"A": "هادئ", "B": "انزعاج بسيط", "C": "انزعاج قوي", "D": "تأثر حسب الحالة الاجتماعية"}},
            {"text": "الدافع للحركة الآن؟", "options": ["A", "B", "C", "D"], "options_text": {"A": "حركة حاسمة ومباشرة", "B": "رغبة قوية في الحركة", "C": "انسحاب أو تجمّد", "D": "تهدئة الوضع"}},
            {"text": "مستوى الطاقة الآن؟", "options": ["A", "B", "C", "D"], "options_text": {"A": "طاقة حاسمة", "B": "طاقة عالية", "C": "طاقة منخفضة أو انسحاب", "D": "طاقة موجهة للآخرين"}},
            {"text": "وضوح الذهن الآن؟", "options": ["A", "B", "C", "D"], "options_text": {"A": "تركيز حاسم", "B": "أفكار سريعة", "C": "بطء أو تشوّش", "D": "تركيز على الآخرين"}},
            {"text": "الميل للتواصل الآن؟", "options": ["A", "B", "C", "D"], "options_text": {"A": "مواجهة مباشرة", "B": "تجنب عبر الانشغال", "C": "انسحاب", "D": "تهدئة الآخرين"}},
        ]

        for i, q in enumerate(neuroscience_questions):
            session.add(AssessmentQuestion(
                assessment_type="neuroscience",
                order_index=i + 1,
                text=q["text"],
                options=q["options"],
                options_text=q.get("options_text"),
                is_active=True,
            ))

        await session.commit()
        print("✅ Default assessment questions seeded successfully.")
