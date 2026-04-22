import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

print("Initializing sentence-transformer model...")
model = SentenceTransformer('all-MiniLM-L6-v2')

import sqlite3

print("Connecting to SQLite database...")
conn = sqlite3.connect('knowledge_base/isl_database.db')
cursor = conn.cursor()
cursor.execute('SELECT text, file FROM video_metadata')
rows = cursor.fetchall()

texts = [row[0] for row in rows]
filenames = [row[1] for row in rows]
conn.close()

print(f"Found {len(texts)} text phrases to encode.")
print("Encoding text phrases into vectors... (This may take a moment)")
embeddings = model.encode(texts, convert_to_numpy=True)

print(f"Embeddings created with shape: {embeddings.shape}")
embedding_dimension = embeddings.shape[1]

print("Creating FAISS index...")
index = faiss.IndexFlatL2(embedding_dimension) 
index = faiss.IndexIDMap(index)

index.add_with_ids(embeddings, np.arange(len(texts)))

print(f"Total vectors in index: {index.ntotal}")

print("Saving FAISS index to 'video_index.faiss'...")
faiss.write_index(index, 'video_index.faiss')

index_to_filename = {i: filename for i, filename in enumerate(filenames)}
print("Saving index-to-filename mapping to 'index_map.json'...")
with open('index_map.json', 'w') as f:
    json.dump(index_to_filename, f)

print("\n✅ Setup complete! Your vector database is ready.")
