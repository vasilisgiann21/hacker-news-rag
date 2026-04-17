import json
import os
import chromadb
from chromadb.utils import embedding_functions

# --- settings ---
INPUT_FILE = "chunks.jsonl"
DB_PATH = "./simple_chroma_db"
COLLECTION_NAME = "target_intel"
BATCH_SIZE = 500
MODEL_NAME = "BAAI/bge-base-en-v1.5"

def main():
    # check if input file exists
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    # set up chroma and embedding model
    print("Starting ChromaDB...")
    client = chromadb.PersistentClient(path=DB_PATH)
    embedder = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=MODEL_NAME)

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedder,
        metadata={"hnsw:space": "cosine"}
    )

    # read chunks and batch them
    ids_batch = []
    docs_batch = []
    metas_batch = []
    total_added = 0

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            chunk = json.loads(line)
            chunk_id = chunk.get("chunk_id")
            chunk_text = chunk.get("chunk_text")

            # skip if missing id or text
            if not chunk_id or not chunk_text:
                continue

            # build simple metadata
            meta = {
                "url": chunk.get("url", "unknown"),
                "title": chunk.get("title", "unknown"),
                "depth": chunk.get("depth", 0),
                "chunk_type": chunk.get("chunk_type", "text")
            }

            ids_batch.append(chunk_id)
            docs_batch.append(chunk_text)
            metas_batch.append(meta)

            # when batch is full, send to chroma
            if len(ids_batch) >= BATCH_SIZE:
                try:
                    collection.upsert(
                        ids=ids_batch,
                        documents=docs_batch,
                        metadatas=metas_batch
                    )
                    total_added += len(ids_batch)
                    print(f"Added {len(ids_batch)} chunks (total: {total_added})")
                except Exception as e:
                    print(f"Batch failed: {e}")

                # clear for next batch
                ids_batch = []
                docs_batch = []
                metas_batch = []

    # add any leftovers
    if ids_batch:
        try:
            collection.upsert(
                ids=ids_batch,
                documents=docs_batch,
                metadatas=metas_batch
            )
            total_added += len(ids_batch)
            print(f"Added final {len(ids_batch)} chunks")
        except Exception as e:
            print(f"Final batch failed: {e}")

    print(f"\nDone. Total chunks stored: {total_added}")
    print(f"Collection count: {collection.count()}")

if __name__ == "__main__":
    main()
