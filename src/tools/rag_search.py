from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.tools import tool

CHROMA_PATH = "/app/data/chroma_db"


@tool
def search_thesis_guide(query: str) -> str:
    """Search the university handbook for thesis policies, rules, deadlines, and guidelines."""
    embeddings = OllamaEmbeddings(
        model="nomic-embed-text", base_url="http://ollama:11434"
    )
    db = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=embeddings,
        collection_name="thesis_guide",
    )
    results = db.similarity_search(query, k=2)
    if not results:
        return "No relevant information found in the thesis guidelines."
    return "\n\n".join([doc.page_content for doc in results])
