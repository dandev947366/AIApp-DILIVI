import os
import shutil
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

CHROMA_PATH = "/app/data/chroma_db"
DATA_PATH = "/app/data/rag/thesis_rules.txt"


def init_rag_db():
    """Checks if ChromaDB exists. If not, builds it from the data folder."""

    if os.path.exists(CHROMA_PATH) and os.listdir(CHROMA_PATH):
        print("[RAG] ChromaDB already exists. Skipping ingestion.")
        return

    print("[RAG] First run detected. Building ChromaDB...")

    if not os.path.exists(DATA_PATH):
        print(f"❌ [RAG] File not found: {DATA_PATH}. Cannot build Knowledge Base.")
        return

    try:
        with open(DATA_PATH, "r") as f:
            text = f.read()

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)
        chunks = text_splitter.split_text(text)

        embeddings = OllamaEmbeddings(
            model="nomic-embed-text", base_url="http://ollama:11434"
        )

        Chroma.from_texts(
            chunks,
            embeddings,
            persist_directory=CHROMA_PATH,
            collection_name="thesis_guide",
        )
        print(f"✅ [RAG] Ingested {len(chunks)} chunks into ChromaDB.")

    except Exception as e:
        print(f"❌ [RAG] Failed to build ChromaDB: {e}")
        if os.path.exists(CHROMA_PATH):
            shutil.rmtree(CHROMA_PATH)
