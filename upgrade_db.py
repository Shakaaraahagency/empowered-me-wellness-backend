from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        db.session.execute(text("ALTER TABLE products ADD COLUMN category VARCHAR(100) DEFAULT 'ebook';"))
        db.session.commit()
        print("Successfully added category column to products table.")
    except Exception as e:
        print(f"Error: {e}")
        db.session.rollback()
