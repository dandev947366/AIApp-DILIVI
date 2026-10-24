import os
from langchain_core.tools import tool
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

CHROMA_PATH = "/app/data/chroma_db"
DATA_PATH = "/app/data/rag/thesis_rules.txt"


@tool
def add_thesis_rule(rule_text: str) -> str:
    """Add a new university thesis rule to the knowledge base."""
    try:
        # 1. Append to the text file
        with open(DATA_PATH, "a") as f:
            f.write(f"\n- {rule_text}")

        # 2. Add ONLY the new rule to ChromaDB
        embeddings = OllamaEmbeddings(
            model="nomic-embed-text", base_url="http://ollama:11434"
        )
        db = Chroma(
            persist_directory=CHROMA_PATH,
            embedding_function=embeddings,
            collection_name="thesis_guide",
        )
        db.add_texts([rule_text])

        return f"✅ Success: Rule added to Knowledge Base -> '{rule_text}'"
    except Exception as e:
        return f"❌ Failed to update database: {str(e)}"
