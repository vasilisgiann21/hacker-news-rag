import json
import os
import chromadb
from chromadb.utils import embedding_functions
from tqdm import tqdm

# ==================== CONFIGURATION ====================
INPUT_FILE = "chunks.jsonl"       # Output from your LangChain splitter
DB_PATH = "./recon_chroma_db"     # Local directory to store the database
COLLECTION_NAME = "target_intel"
BATCH_SIZE = 500                  # Safe batch size to prevent SQLite/memory limits
MODEL_NAME = "BAAI/bge-base-en-v1.5"
# =======================================================

def chunk_generator(filepath):
    """
    Generator that yields data line-by-line.
    Crucial for OOM (Out of Memory) prevention on massive datasets.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"[!] Target file {filepath} does not exist.")
        
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)

def robust_upsert(collection, ids, docs, metas):
    """
    Attempts a batch upsert. If the batch fails due to a 'poison pill' 
    (corrupted text/metadata), it shifts to isolation mode to save the valid vectors.
    Returns the number of successfully ingested chunks.
    """
    try:
        # The happy path: batch succeeds instantly
        collection.upsert(ids=ids, documents=docs, metadatas=metas)
        return len(ids)
    except Exception as e:
        print(f"\n[!] Batch failure detected. Engaging fault isolation. Error: {e}")
        success_count = 0
        
        # The fallback: process 1-by-1 to isolate the bad payload
        for i in range(len(ids)):
            try:
                collection.upsert(
                    ids=[ids[i]],
                    documents=[docs[i]],
                    metadatas=[metas[i]]
                )
                success_count += 1
            except Exception as inner_e:
                print(f"\n[x] POISON PILL ISOLATED | Dropped ID: {ids[i]}")
                print(f"    Reason: {inner_e}")
                
        return success_count

def main():
    print(f"[*] Initializing persistent ChromaDB at {DB_PATH}...")
    
    # 1. Initialize Persistent Client
    client = chromadb.PersistentClient(path=DB_PATH)

    # 2. Initialize the Local Embedding Engine
    print(f"[*] Loading local embedding model: {MODEL_NAME}")
    sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=MODEL_NAME)

    # 3. Create or Connect to the Collection
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=sentence_transformer_ef,
        metadata={"hnsw:space": "cosine"}
    )

    # 4. Prepare Batching Variables
    ids_batch = []
    documents_batch = []
    metadatas_batch = []
    
    total_inserted = 0

    print("[*] Commencing resilient vector ingestion pipeline...")
    
    # We use a dynamic progress bar since we don't know the exact line count without loading to RAM
    progress_bar = tqdm(desc="Vectors Upserted", unit="chunk")

    # 5. Stream, Batch, and Upsert
    for chunk in chunk_generator(INPUT_FILE):
        chunk_id = chunk.get("chunk_id")
        chunk_text = chunk.get("chunk_text")
        
        # ChromaDB metadata strictly requires str, int, float, or bool. No nested dicts/lists.
        metadata = {
            "url": str(chunk.get("url", "unknown")),
            "title": str(chunk.get("title", "unknown")),
            "depth": int(chunk.get("depth", 0)),
            "chunk_type": str(chunk.get("chunk_type", "text"))
        }

        # Safety check: drop completely empty chunks before they even hit the batch
        if not chunk_id or not chunk_text:
            continue

        ids_batch.append(chunk_id)
        documents_batch.append(chunk_text)
        metadatas_batch.append(metadata)

        # Execute robust upsert when batch is full
        if len(ids_batch) >= BATCH_SIZE:
            inserted = robust_upsert(collection, ids_batch, documents_batch, metadatas_batch)
            total_inserted += inserted
            progress_bar.update(inserted)
            
            # Flush batches from RAM
            ids_batch.clear()
            documents_batch.clear()
            metadatas_batch.clear()

    # 6. Flush Remaining Fragments
    if ids_batch:
        inserted = robust_upsert(collection, ids_batch, documents_batch, metadatas_batch)
        total_inserted += inserted
        progress_bar.update(inserted)

    progress_bar.close()
    
    final_count = collection.count()
    # System Verification
    print("\n==================================================")
    print("[+] Ingestion Pipeline Terminated Successfully.")
    print(f"[+] Total chunks processed in this run: {total_inserted}")
    print(f"[+] Total vectors currently residing in database: {final_count}")
    print("==================================================")

if name == "__main__":
    main()