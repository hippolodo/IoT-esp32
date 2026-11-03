"""Database engine and session factory. Models live in app.models."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# Nhận URL database, trả engine và hàm tạo Session; không tự tạo hay sửa bảng.
def make_database(url):
    options = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    engine = create_engine(url, **options)
    return engine, sessionmaker(engine, expire_on_commit=False)
