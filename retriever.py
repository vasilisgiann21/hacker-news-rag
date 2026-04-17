import chromadb 
from chromadb.utils import embedding_functions
import requests

class ReconRetriever:
    def __init__(self, db_path, collection_name="target_intel"):
        print("[*] Initializing local retrieval engine...")
        self.client = chromadb.PersistentClient(path=db_path)
        self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="BAAI/bge-base-en-v1.5")
        self.collection = self.client.get_collection(name=collection_name, embedding_function=self.ef)
        print("[+] Engine armed and database connected.")
        
    def search(self, query, top_n=5): 
        return self.collection.query( 
            query_texts=[query],
            n_results=top_n
        )

    def format_context(self, search_results):
        documents = search_results['documents'][0]
        return "\n\n---\n\n".join(documents)

    def ask_ai(self, query, context):
        prompt_template = f"""You are a cyber-intel analyst. Use the following context to answer the user query. If the context doesn't contain the answer, say 'Insufficient Intel'. Do not hallucinate.

Context: 
{context}

User Query: {query}"""

        payload = {
            "model": "dolphin-phi",
            "prompt": prompt_template,
            "stream": False 
        }

        try:
            response = requests.post("http://localhost:11434/api/generate", json=payload)
            return response.json().get("response", "Error: No response text found.")
        except Exception as e:
            return f"[*] CRITICAL FAILURE: Cannot reach local LLM. {e}"


if __name__ == "__main__":
    db_path = "/home/cyberdork21/recon_chroma_db"
    retriever = ReconRetriever(db_path=db_path)

    while True:
        user_query = input("\n[?] Enter search query (or 'exit' to quit): ")
        if user_query.strip().lower() == 'exit':
            break

        if user_query.strip():
            print("\n[*] Engaging Vector Database...")
            raw_results = retriever.search(user_query)
            
            print("[*] Stitching Context Payload...")
            context_string = retriever.format_context(raw_results)
            
            print("[*] Transmitting to Dolphin-Phi Engine...\n")
            ai_answer = retriever.ask_ai(user_query, context_string)
            
            print("="*60)
            print(">> ANALYST REPORT")
            print("="*60)
            print(ai_answer)
            print("="*60)