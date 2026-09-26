import os
import json
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None

# Global memory client
_memory_client = None
_collection = None

# Fallback simple dict memory if chroma is not installed
_fallback_memory_file = Path.home() / ".chatty-chronos" / "memory.json"
_fallback_facts = []

def init_memory():
    global _memory_client, _collection, _fallback_facts
    
    if chromadb is not None:
        try:
            db_path = Path.home() / ".chatty-chronos" / "vectordb"
            db_path.mkdir(parents=True, exist_ok=True)
            _memory_client = chromadb.PersistentClient(path=str(db_path), settings=Settings(anonymized_telemetry=False))
            _collection = _memory_client.get_or_create_collection(name="agent_memory")
            return True
        except Exception:
            pass # Fallback

    if _fallback_memory_file.exists():
        try:
            with open(_fallback_memory_file, "r", encoding="utf-8") as f:
                _fallback_facts = json.load(f)
        except Exception:
            pass
    return True

def store_memory(key: str, content: str, metadata: dict = None):
    """Store an item in the long-term vector memory."""
    meta = metadata or {}
    meta["key"] = key
    
    if _collection is not None:
        _collection.add(
            documents=[content],
            metadatas=[meta],
            ids=[key]
        )
        return True
    else:
        _fallback_facts.append({"key": key, "content": content, "metadata": meta})
        _fallback_memory_file.parent.mkdir(exist_ok=True, parents=True)
        with open(_fallback_memory_file, "w", encoding="utf-8") as f:
            json.dump(_fallback_facts, f, indent=2, ensure_ascii=False)
        return True

def search_memory(query: str, n_results: int = 3):
    """Search the vector memory for semantic matches."""
    if _collection is not None:
        try:
            results = _collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            if not results or not results["documents"] or not results["documents"][0]:
                return []
                
            found = []
            for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
                found.append({
                    "content": doc,
                    "metadata": meta
                })
            return found
        except Exception:
            return []
    else:
        # Fallback simple search: just return everything or naive keyword match
        found = []
        for fact in _fallback_facts:
            if query.lower() in fact["content"].lower() or query.lower() in fact["key"].lower():
                found.append(fact)
        return found[:n_results]

# Compatibility methods for old agent usage
class Memory:
    def __init__(self):
        init_memory()
        self.facts = [] # Deprecated, use search_memory instead
        
    def add(self, fact: str):
        store_memory(str(hash(fact)), fact)
        
    def get_context(self) -> str:
        # We don't automatically dump all context anymore, agent uses search_memory tool
        return ""
