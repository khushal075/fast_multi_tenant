from sqlalchemy import create_engine, text
import os

engine = create_engine(os.getenv("DATABASE_URL"))
with engine.connect() as conn:
    res = conn.execute(text("SELECT 1")).scalar()
    print(f"Stand-alone test success: {res}")
