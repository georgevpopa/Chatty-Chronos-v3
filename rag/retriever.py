"""RAG Retriever — Query ChromaDB for relevant context."""
from pathlib import Path
from rich.console import Console
from core.config import Config
from rag.embeddings import ChronosEmbeddingFunction

console = Console()


def query_knowledge(question: str, collection_name: str = "project", n_results: int = 5, config: Config = None) -> list[dict]:
    """Query the vector database for relevant chunks.

    Returns list of {text, file, score} dicts.
    """
    try:
        import chromadb
    except ImportError:
        return []

    if config is None:
        config = Config()

    db_path = config.dir / "vectordb"
    if not db_path.exists():
        return []

    embed_fn = ChronosEmbeddingFunction(config)
    from chromadb.config import Settings
    client = chromadb.PersistentClient(path=str(db_path), settings=Settings(anonymized_telemetry=False))

    try:
        collection = client.get_collection(name=collection_name, embedding_function=embed_fn)
    except Exception:
        return []

    # Query a larger pool of candidates to allow re-ranking
    candidate_limit = max(15, n_results * 3)
    results = collection.query(query_texts=[question], n_results=candidate_limit)

    if not results or not results["documents"] or not results["documents"][0]:
        return []

    # Extract technical keywords from query
    import re
    words = re.findall(r'[a-zA-Z0-9_\.]+', question)
    STOPWORDS = {"how", "does", "what", "where", "when", "why", "the", "and", "for", "with", "this", "that", "you", "from", "your"}
    keywords = [w for w in words if len(w) > 2 and w.lower() not in STOPWORDS]

    output = []
    for i, doc in enumerate(results["documents"][0]):
        meta = results["metadatas"][0][i] if results["metadatas"] else {}
        distance = results["distances"][0][i] if (results["distances"] and results["distances"][0]) else 0.5
        
        # Re-rank based on technical keyword density
        match_count = 0
        doc_lower = doc.lower()
        for kw in keywords:
            if kw in doc:  # Case-sensitive exact match
                match_count += 1.5
            elif kw.lower() in doc_lower:  # Case-insensitive match
                match_count += 0.5
                
        # Lower score is better. Each keyword match decreases the hybrid score.
        hybrid_score = distance - (match_count * 0.15)
        
        output.append({
            "text": doc,
            "file": meta.get("file", "unknown"),
            "chunk_index": meta.get("chunk_index", 0),
            "distance": distance,
            "hybrid_score": hybrid_score,
        })

    # Sort by hybrid_score and limit to requested n_results
    output.sort(key=lambda x: x["hybrid_score"])
    return output[:n_results]


def get_rag_context(question: str, collection_name: str = "project", n_results: int = 5, config: Config = None) -> str:
    """Get formatted RAG context string for injection into LLM prompt."""
    results = query_knowledge(question, collection_name, n_results, config)

    if not results:
        return ""

    context = "## Relevant context from indexed knowledge:\n\n"
    seen_files = set()
    for r in results:
        source = f"[{r['file']}]"
        if r["file"] not in seen_files:
            seen_files.add(r["file"])
        context += f"--- {source} ---\n{r['text']}\n\n"

    return context

