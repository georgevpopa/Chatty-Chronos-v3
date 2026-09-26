"""Custom embedding functions for ChromaDB RAG.

Supports local CPU sentence-transformers, Ollama, and llama-server (llama.cpp) embedding endpoints.
"""
import httpx
from core.config import Config

class ChronosEmbeddingFunction:
    def __init__(self, config: Config):
        self.config = config

    def name(self) -> str:
        """Return a custom name to satisfy newer ChromaDB collection validation protocol."""
        return "chronos_default"

    def embed_documents(self, input: list[str]) -> list[list[float]]:
        """ChromaDB protocol for embedding multiple documents."""
        return self.__call__(input)

    def embed_query(self, input: list[str]) -> list[list[float]]:
        """ChromaDB protocol for embedding search queries."""
        return self.__call__(input)

    def __call__(self, input: list[str]) -> list[list[float]]:
        provider = self.config.get("embedding_provider", "local")
        model = self.config.get("embedding_model", "all-MiniLM-L6-v2")

        if provider == "ollama":
            import ollama
            host = self.config.get("ollama_host", "http://localhost:11434")
            client = ollama.Client(host=host)
            try:
                # Use client.embed for batch embeddings in newer ollama versions
                response = client.embed(model=model, input=input)
                return response.embeddings
            except Exception:
                # Fallback to single-prompt embeddings loop if batch fails
                embeddings = []
                for text in input:
                    res = client.embeddings(model=model, prompt=text)
                    embeddings.append(res["embedding"])
                return embeddings

        elif provider == "llamacpp":
            host = self.config.get("llamacpp_host", "http://localhost:8080")
            url = f"{host}/v1/embeddings"
            payload = {
                "model": model,
                "input": input
            }
            try:
                with httpx.Client(timeout=60) as client:
                    response = client.post(url, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    # llama-server returns standard OpenAI format
                    return [item["embedding"] for item in data["data"]]
            except Exception as e:
                raise RuntimeError(f"llama-server embedding error: {e}")

        else:  # "local" or default
            # Use ChromaDB's built-in SentenceTransformerEmbeddingFunction (runs offline via sentence-transformers/onnx)
            try:
                from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
            except ImportError:
                raise ImportError("chromadb is required. Run: pip install chromadb sentence-transformers")
            
            # Default to all-MiniLM-L6-v2 (fast and light CPU embeddings)
            fn = SentenceTransformerEmbeddingFunction(model_name=model)
            return fn(input)