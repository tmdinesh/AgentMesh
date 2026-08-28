import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

logger = logging.getLogger(__name__)

# SQLite configuration
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DEBUG
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI Dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate_columns():
    """Safely adds new columns to existing SQLite database if they don't already exist."""
    with engine.connect() as conn:
        try:
            # Check columns in messages table
            res = conn.execute(text("PRAGMA table_info(messages);")).fetchall()
            existing_cols = [r[1] for r in res]
            if existing_cols:
                if "model_name" not in existing_cols:
                    conn.execute(text("ALTER TABLE messages ADD COLUMN model_name VARCHAR(64);"))
                    conn.commit()
                if "provider" not in existing_cols:
                    conn.execute(text("ALTER TABLE messages ADD COLUMN provider VARCHAR(32);"))
                    conn.commit()

            # Check columns in experiments table
            exp_res = conn.execute(text("PRAGMA table_info(experiments);")).fetchall()
            existing_exp_cols = [r[1] for r in exp_res]
            if existing_exp_cols:
                if "human_audited" not in existing_exp_cols:
                    conn.execute(text("ALTER TABLE experiments ADD COLUMN human_audited BOOLEAN DEFAULT 0;"))
                    conn.commit()
                if "human_notes" not in existing_exp_cols:
                    conn.execute(text("ALTER TABLE experiments ADD COLUMN human_notes TEXT;"))
                    conn.commit()
        except Exception as e:
            logger.debug(f"Column migration check note: {e}")


def init_db():
    """Initializes tables and seeds default benchmark tasks if empty."""
    import app.models  # Ensure all models are registered on Base.metadata
    Base.metadata.create_all(bind=engine)
    migrate_columns()
    
    # Auto-seed tasks
    from app.tasks.seed_tasks import seed_default_tasks
    db = SessionLocal()
    try:
        seed_default_tasks(db)
    finally:
        db.close()


# Ensure tables exist upon database module load
import app.models  # noqa: E402, F401
Base.metadata.create_all(bind=engine)
migrate_columns()
db_init_session = SessionLocal()
try:
    from app.tasks.seed_tasks import seed_default_tasks
    seed_default_tasks(db_init_session)
finally:
    db_init_session.close()
