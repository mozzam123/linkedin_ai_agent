import sqlite3
from datetime import datetime

DB_PATH = "./linkedin_ai.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Check if column already exists
cursor.execute("PRAGMA table_info(linkedin_posts)")
columns = [row[1] for row in cursor.fetchall()]

if "created_at" not in columns:

    # Add column WITHOUT dynamic default
    cursor.execute(
        "ALTER TABLE linkedin_posts ADD COLUMN created_at DATETIME"
    )

    # Backfill existing rows
    now = datetime.utcnow().isoformat()

    cursor.execute(
        """
        UPDATE linkedin_posts
        SET created_at = ?
        WHERE created_at IS NULL
        """,
        (now,)
    )

    conn.commit()

    print(f"✅ created_at column added successfully.")

else:
    print("✅ created_at already exists.")

conn.close()