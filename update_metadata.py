import os
import json

# Define the paths to your videos folder and metadata file
VIDEOS_DIR = "knowledge_base/videos"
METADATA_FILE = "knowledge_base/metadata.json"

def update_metadata_from_videos():
    """
    Scans the videos directory, finds new .mp4 files, and
    automatically adds them to the metadata.json file.
    """
    print("Starting metadata update...")

    # --- 1. Get the list of video files from the directory ---
    try:
        # List all files in the directory that end with .mp4
        video_files_on_disk = {f for f in os.listdir(VIDEOS_DIR) if f.endswith('.mp4')}
    except FileNotFoundError:
        print(f"Error: The directory '{VIDEOS_DIR}' was not found. Please create it.")
        return

    # --- 2. Connect to SQLite database ---
    import sqlite3
    DB_PATH = 'knowledge_base/isl_database.db'
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Ensure table exists
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS video_metadata (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file TEXT UNIQUE NOT NULL,
        text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Get existing files for fast lookup
    cursor.execute('SELECT file FROM video_metadata')
    files_in_metadata = {row[0] for row in cursor.fetchall()}
    print(f"Found {len(files_in_metadata)} files already cataloged in SQLite database.")

    # --- 3. Find the new files that need to be added ---
    new_files_to_add = video_files_on_disk - files_in_metadata
    
    if not new_files_to_add:
        print("✅ Metadata is already up-to-date. No new videos found.")
        conn.close()
        return

    print(f"Found {len(new_files_to_add)} new video(s) to add:")

    # --- 4. Generate new entries and insert them ---
    for filename in sorted(list(new_files_to_add)):
        text_phrase = os.path.splitext(filename)[0].replace('_', ' ')
        
        try:
            cursor.execute('INSERT INTO video_metadata (file, text) VALUES (?, ?)', 
                         (filename, text_phrase))
            print(f"  + Added entry for '{filename}' with text '{text_phrase}'")
        except sqlite3.IntegrityError:
            pass

    # --- 5. Save the updated metadata and close ---
    conn.commit()
    conn.close()

    print(f"\n✅ Successfully updated SQLite database with {len(new_files_to_add)} new entries.")

if __name__ == "__main__":
    update_metadata_from_videos()