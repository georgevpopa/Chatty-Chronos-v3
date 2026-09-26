"""RAG Indexer — Chunk files, generate embeddings, store in ChromaDB."""
import os
from pathlib import Path
from rich.console import Console
from core.config import Config
from rag.embeddings import ChronosEmbeddingFunction

console = Console()

# Default patterns to skip
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".egg-info", "dist", "build"}
SKIP_EXTENSIONS = {".pyc", ".exe", ".dll", ".so", ".bin", ".jpg", ".png", ".gif", ".zip", ".tar", ".gz"}
MAX_FILE_SIZE = 100_000  # 100KB


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks

def extract_pdf_text(fp: Path) -> str:
    """Extract clean text from a PDF file."""
    try:
        import pypdf
        reader = pypdf.PdfReader(fp)
        text = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
        return "\n".join(text)
    except Exception as e:
        console.print(f"  [red]Error reading PDF {fp.name}: {e}[/red]")
        return ""


def extract_docx_text(fp: Path) -> str:
    """Extract clean text from a Word document."""
    try:
        import docx
        doc = docx.Document(fp)
        text = []
        for paragraph in doc.paragraphs:
            if paragraph.text:
                text.append(paragraph.text)
        return "\n".join(text)
    except Exception as e:
        console.print(f"  [red]Error reading Word document {fp.name}: {e}[/red]")
        return ""

def load_gitignore_patterns(base_path: Path) -> list:
    """Load gitignore rules and compile them into regex patterns."""
    gitignore_path = base_path / ".gitignore"
    if not gitignore_path.exists():
        return []
    
    patterns = []
    try:
        lines = gitignore_path.read_text(encoding="utf-8", errors="replace").splitlines()
        import re
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            # Simple conversion of glob to regex
            # e.g., "dist/" -> ".*dist/.*", "*.log" -> ".*\.log$"
            regex_pat = re.escape(line).replace(r'\*', '.*')
            if line.endswith('/'):
                regex_pat = f".*{regex_pat}.*"
            else:
                regex_pat = f".*{regex_pat}$"
            patterns.append(re.compile(regex_pat))
    except Exception:
        pass
    return patterns


def is_ignored(fp: Path, base: Path, ignore_patterns: list) -> bool:
    """Check if file or directory path matches any compiled gitignore pattern."""
    if not ignore_patterns:
        return False
    try:
        rel_path = str(fp.relative_to(base)).replace('\\', '/')
        for pattern in ignore_patterns:
            if pattern.match(rel_path) or any(pattern.match(part) for part in rel_path.split('/')):
                return True
    except Exception:
        pass
    return False


def collect_files(path: str, include: str = None) -> list[Path]:
    """Collect indexable files from a directory, respecting base ignores and .gitignore."""
    base = Path(path).expanduser().resolve()
    files = []

    if base.is_file():
        return [base]

    ignore_patterns = load_gitignore_patterns(base)

    for root, dirs, filenames in os.walk(base):
        # Skip hidden/unwanted directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        
        # Filter directories dynamically using gitignore
        dirs[:] = [d for d in dirs if not is_ignored(Path(root) / d, base, ignore_patterns)]

        for fname in filenames:
            fp = Path(root) / fname
            # Skip by extension
            if fp.suffix.lower() in SKIP_EXTENSIONS:
                continue
            # Skip large files (allow larger limits for PDF/DOCX due to binary packaging)
            try:
                limit = 10_000_000 if fp.suffix.lower() in {".pdf", ".docx"} else MAX_FILE_SIZE
                if fp.stat().st_size > limit:
                    continue
            except OSError:
                continue
            # Apply include filter
            if include and not fp.match(include):
                continue
            # Apply gitignore filter
            if is_ignored(fp, base, ignore_patterns):
                continue
            files.append(fp)

    return files


def index_directory(path: str, collection_name: str = "project", include: str = None, config: Config = None):
    """Index a directory into ChromaDB with differential indexing support.

    Returns (num_files, num_chunks) on success.
    """
    try:
        import chromadb
    except ImportError:
        console.print("[red]  chromadb not installed. Run: pip install chromadb[/red]")
        return 0, 0

    if config is None:
        config = Config()

    base = Path(path).expanduser().resolve()
    db_path = config.dir / "vectordb"
    db_path.mkdir(parents=True, exist_ok=True)

    # Use configurable embeddings function
    embed_fn = ChronosEmbeddingFunction(config)
    from chromadb.config import Settings
    client = chromadb.PersistentClient(path=str(db_path), settings=Settings(anonymized_telemetry=False))
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=embed_fn,
    )

    files = collect_files(path, include)
    if not files:
        console.print(f"  [yellow]No indexable files found in {base}[/yellow]")
        return 0, 0

    # Differential indexing: load existing document metadata
    indexed_files_mtime = {}
    try:
        existing = collection.get(include=["metadatas"])
        if existing and "metadatas" in existing:
            for meta in existing["metadatas"]:
                if meta and "file" in meta and "mtime" in meta:
                    indexed_files_mtime[meta["file"]] = meta["mtime"]
    except Exception as e:
        console.print(f"  [dim]Could not load indexing cache: {e}. Performing full index.[/dim]")

    total_chunks = 0
    indexed_files = 0
    skipped_files = 0

    for fp in files:
        rel_path = str(fp.relative_to(base))
        try:
            mtime = fp.stat().st_mtime
        except OSError:
            continue

        # Check if file is unmodified
        if rel_path in indexed_files_mtime and indexed_files_mtime[rel_path] == mtime:
            skipped_files += 1
            continue

        ext = fp.suffix.lower()
        if ext == ".pdf":
            try:
                import pypdf
                content = extract_pdf_text(fp)
            except ImportError:
                console.print(f"  [yellow]Skipping PDF {fp.name}: install 'pypdf' to index PDF files.[/yellow]")
                continue
        elif ext == ".docx":
            try:
                import docx
                content = extract_docx_text(fp)
            except ImportError:
                console.print(f"  [yellow]Skipping Word file {fp.name}: install 'python-docx' to index Word files.[/yellow]")
                continue
        else:
            try:
                content = fp.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

        if not content.strip():
            continue

        # If file is modified, delete its existing chunks first
        if rel_path in indexed_files_mtime:
            try:
                collection.delete(where={"file": rel_path})
            except Exception:
                pass

        chunks = chunk_text(content)

        ids = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            doc_id = f"{rel_path}::chunk_{i}"
            ids.append(doc_id)
            documents.append(chunk)
            metadatas.append({
                "file": rel_path,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "mtime": mtime,
            })

        # Upsert in batches
        batch_size = 50
        for b in range(0, len(ids), batch_size):
            collection.upsert(
                ids=ids[b:b+batch_size],
                documents=documents[b:b+batch_size],
                metadatas=metadatas[b:b+batch_size],
            )

        total_chunks += len(chunks)
        indexed_files += 1

    if skipped_files > 0:
        console.print(f"  [dim]Skipped {skipped_files} unmodified files.[/dim]")

    return indexed_files, total_chunks


def index_url(url: str, collection_name: str = "project", config: Config = None):
    """Descarcă o pagină web, extrage textul curat și îl adaugă în ChromaDB."""
    try:
        import chromadb
        import requests
        from bs4 import BeautifulSoup
    except ImportError as e:
        console.print(f"[red] Lipsește o dependență. Run: pip install chromadb requests beautifulsoup4. Error: {e}[/red]")
        return 0

    if config is None:
        config = Config()

    db_path = config.dir / "vectordb"
    db_path.mkdir(parents=True, exist_ok=True)

    # 1. Descărcare conținut web nativ
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        console.print(f"  [red]Eroare la descărcarea URL-ului: {e}[/red]")
        return 0

    # 2. Curățare HTML (Eliminăm scripturi, stiluri CSS și meniuri)
    soup = BeautifulSoup(response.text, "html.parser")
    for script in soup(["script", "style", "nav", "footer", "header"]):
        script.decompose()

    text_curat = soup.get_text(separator="\n")
    
    # Curățăm spațiile goale multiple rămase din HTML
    lines = [line.strip() for line in text_curat.splitlines() if line.strip()]
    text_final = "\n".join(lines)

    if not text_final.strip():
        console.print("  [yellow]Atenție: Nu s-a putut extrage text util din pagină.[/yellow]")
        return 0

    # 3. Conexiune la baza de date RAG locală
    embed_fn = ChronosEmbeddingFunction(config)
    from chromadb.config import Settings
    client = chromadb.PersistentClient(path=str(db_path), settings=Settings(anonymized_telemetry=False))
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=embed_fn,
    )

    # 4. Stergem versiunea veche a acestui URL dacă fusese deja indexat
    try:
        collection.delete(where={"file": url})
    except Exception:
        pass

    # 5. Spargere în bucăți (reutilizăm funcția ta existentă chunk_text)
    chunks = chunk_text(text_final)

    ids = []
    documents = []
    metadatas = []

    # Folosim titlul paginii în metadate dacă există, altfel URL-ul generic
    titlu_pagina = soup.title.string.strip() if soup.title else url

    for i, chunk in enumerate(chunks):
        doc_id = f"url_{url}::chunk_{i}"
        ids.append(doc_id)
        documents.append(chunk)
        metadatas.append({
            "file": url,  # Salvăm URL-ul ca identificator sursă
            "title": titlu_pagina,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "mtime": 0.0  # URL-urile nu au un mtime local pe Windows
        })

    # 6. Upsert în ChromaDB
    batch_size = 50
    for b in range(0, len(ids), batch_size):
        collection.upsert(
            ids=ids[b:b+batch_size],
            documents=documents[b:b+batch_size],
            metadatas=metadatas[b:b+batch_size],
        )

    console.print(f"  [green]Succes: Am indexat URL-ul în RAG! Extrase {len(chunks)} bucăți de cunoștințe.[/green]")
    return len(chunks)