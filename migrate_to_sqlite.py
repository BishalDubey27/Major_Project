import sqlite3
import json
import os

DB_PATH = 'knowledge_base/isl_database.db'
JSON_PATH = 'knowledge_base/metadata.json'

def migrate():
    if not os.path.exists(JSON_PATH):
        print(f"Error: {JSON_PATH} not found.")
        return

    # Connect to SQLite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS video_metadata (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file TEXT UNIQUE NOT NULL,
        text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Load JSON
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    # Insert data
    count = 0
    for item in metadata:
        try:
            cursor.execute('INSERT INTO video_metadata (file, text) VALUES (?, ?)', 
                         (item['file'], item['text']))
            count += 1
        except sqlite3.IntegrityError:
            # Skip duplicates
            pass

    conn.commit()
    conn.close()
    print(f"✅ Migrated {count} entries from JSON to SQLite database.")

if __name__ == '__main__':
    migrate()
