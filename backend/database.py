"""Database setup — SQLite for the prototype, swappable for PostgreSQL later."""

from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "foodflow.db"

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def migrate_sqlite() -> None:
    """Add columns that create_all will not alter on an existing SQLite file."""
    statements = [
        "ALTER TABLE dishes ADD COLUMN cv_class VARCHAR(60) DEFAULT ''",
        "ALTER TABLE feedback ADD COLUMN rating INTEGER",
    ]
    with engine.begin() as conn:
        for sql in statements:
            try:
                conn.execute(text(sql))
            except Exception:
                pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
