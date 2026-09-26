"""Chatty Chronos v3 — Knowledge Database Initialization
Creates and populates SQLite database with all project metadata.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "db")


def create_schema(cur):
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        url TEXT,
        language TEXT,
        status TEXT,
        purpose TEXT,
        visibility TEXT DEFAULT 'private'
    );

    CREATE TABLE IF NOT EXISTS dependencies (
        id INTEGER PRIMARY KEY,
        project_id INTEGER REFERENCES projects(id),
        name TEXT NOT NULL,
        version TEXT,
        category TEXT
    );

    CREATE TABLE IF NOT EXISTS features (
        id INTEGER PRIMARY KEY,
        project_id INTEGER REFERENCES projects(id),
        name TEXT NOT NULL,
        description TEXT,
        category TEXT
    );

    CREATE TABLE IF NOT EXISTS commands (
        id INTEGER PRIMARY KEY,
        project_id INTEGER REFERENCES projects(id),
        name TEXT NOT NULL,
        description TEXT,
        syntax TEXT
    );

    CREATE TABLE IF NOT EXISTS llm_providers (
        id INTEGER PRIMARY KEY,
        project_id INTEGER REFERENCES projects(id),
        provider TEXT NOT NULL,
        model TEXT,
        endpoint TEXT,
        is_local INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS storage_methods (
        id INTEGER PRIMARY KEY,
        project_id INTEGER REFERENCES projects(id),
        type TEXT NOT NULL,
        location TEXT,
        description TEXT
    );

    CREATE TABLE IF NOT EXISTS architecture_patterns (
        id INTEGER PRIMARY KEY,
        project_id INTEGER REFERENCES projects(id),
        pattern TEXT NOT NULL,
        description TEXT
    );

    CREATE TABLE IF NOT EXISTS cross_references (
        id INTEGER PRIMARY KEY,
        source_project_id INTEGER REFERENCES projects(id),
        target_project_id INTEGER REFERENCES projects(id),
        relationship TEXT
    );
    """)


def populate_projects(cur):
    projects = [
        ("kiro-cli-autobuild", "https://github.com/georgevpopa/kiro-cli-autobuild",
         "JavaScript", "functional",
         "Spec-driven development agent — turns feature ideas into Requirements, Design, Tasks specs using AI",
         "private"),
        ("KIro_NotionAI_Style", "https://github.com/georgevpopa/KIro_NotionAI_Style",
         "Python", "scaffold",
         "Cross-platform Python CLI project template with CI pipeline, intended for Ollama integration",
         "private"),
        ("chatty-cli-buddy", "https://github.com/georgevpopa/chatty-cli-buddy",
         "Python", "functional",
         "Autonomous DevOps CLI agent using ReAct loop, executes shell commands, manages Docker/GitHub via MCP tools",
         "private"),
        ("chronos", "https://github.com/georgevpopa/chronos",
         "Python", "early-stage",
         "AI-powered desktop file organizer (EMMA) that scans directories and proposes clean folder structures",
         "private"),
        ("Chatty-FreeLLM-AllHandsOnDeck", "https://github.com/georgevpopa/Chatty-FreeLLM-AllHandsOnDeck",
         "Python", "functional",
         "Free multi-provider LLM chat with web UI, rate-limit rotation, and aider integration for code editing",
         "public"),
        ("chatty-local-data-LLM", "https://github.com/georgevpopa/chatty-local-data-LLM",
         "Python", "functional",
         "Privacy-first RAG agent that ingests OneNote notebooks, deduplicates content, and answers questions locally",
         "public"),
        ("Chatty-My-Agent", "https://github.com/georgevpopa/Chatty-My-Agent",
         "Python", "functional",
         "Full CLI AI assistant with 7 LLM providers, 50+ commands, RAG, plugins, voice I/O, and web UI",
         "public"),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO projects (name, url, language, status, purpose, visibility) VALUES (?,?,?,?,?,?)",
        projects
    )


def populate_dependencies(cur):
    deps = [
        # kiro-cli-autobuild — zero deps, uses native fetch
        ("kiro-cli-autobuild", "Node.js 18+", None, "runtime"),
        # chatty-cli-buddy
        ("chatty-cli-buddy", "ollama", ">=0.2.1", "core"),
        ("chatty-cli-buddy", "prompt_toolkit", ">=3.0.43", "ui"),
        ("chatty-cli-buddy", "rich", ">=13.7.1", "ui"),
        ("chatty-cli-buddy", "duckduckgo-search", ">=6.1.7", "tools"),
        ("chatty-cli-buddy", "fastapi", None, "api"),
        ("chatty-cli-buddy", "uvicorn", None, "api"),
        ("chatty-cli-buddy", "pydantic", ">=2.7.1", "validation"),
        # chronos
        ("chronos", "requests", None, "core"),
        ("chronos", "python-dotenv", None, "config"),
        # Chatty-FreeLLM-AllHandsOnDeck
        ("Chatty-FreeLLM-AllHandsOnDeck", "fastapi", ">=0.115.5", "api"),
        ("Chatty-FreeLLM-AllHandsOnDeck", "uvicorn", ">=0.32.1", "api"),
        ("Chatty-FreeLLM-AllHandsOnDeck", "litellm", ">=1.88.0", "core"),
        ("Chatty-FreeLLM-AllHandsOnDeck", "httpx", ">=0.27.0", "http"),
        ("Chatty-FreeLLM-AllHandsOnDeck", "python-dotenv", ">=1.0.1", "config"),
        ("Chatty-FreeLLM-AllHandsOnDeck", "pydantic", ">=2.10.0", "validation"),
        # chatty-local-data-LLM
        ("chatty-local-data-LLM", "fastapi", "0.111.0", "api"),
        ("chatty-local-data-LLM", "chromadb", "0.5.0", "vector_db"),
        ("chatty-local-data-LLM", "msal", "1.28.0", "auth"),
        ("chatty-local-data-LLM", "beautifulsoup4", "4.12.3", "parsing"),
        ("chatty-local-data-LLM", "scikit-learn", "1.5.0", "ml"),
        ("chatty-local-data-LLM", "ollama", "0.2.1", "llm"),
        ("chatty-local-data-LLM", "jinja2", "3.1.4", "templating"),
        # Chatty-My-Agent
        ("Chatty-My-Agent", "google-generativeai", "0.8.3", "llm"),
        ("Chatty-My-Agent", "groq", "1.2.0", "llm"),
        ("Chatty-My-Agent", "cohere", "5.13.0", "llm"),
        ("Chatty-My-Agent", "mistralai", "1.5.0", "llm"),
        ("Chatty-My-Agent", "httpx", "0.28.1", "http"),
        ("Chatty-My-Agent", "rich", "13.9.4", "ui"),
        ("Chatty-My-Agent", "chromadb", "1.0.7", "vector_db"),
        ("Chatty-My-Agent", "sentence-transformers", "4.1.0", "embeddings"),
        ("Chatty-My-Agent", "flask", "3.1.1", "web_ui"),
        ("Chatty-My-Agent", "duckduckgo-search", "7.5.1", "tools"),
    ]
    for name, dep, ver, cat in deps:
        cur.execute(
            "INSERT INTO dependencies (project_id, name, version, category) "
            "SELECT id, ?, ?, ? FROM projects WHERE name=?",
            (dep, ver, cat, name)
        )


def populate_features(cur):
    features = [
        # kiro-cli-autobuild
        ("kiro-cli-autobuild", "Spec generation", "AI-generates requirements, design, and task specs from feature descriptions", "planning"),
        ("kiro-cli-autobuild", "Multi-provider LLM", "Supports OpenAI, Anthropic, Ollama, llama.cpp backends", "llm"),
        ("kiro-cli-autobuild", "STEERING.md injection", "Project context auto-injected into every AI prompt", "context"),
        ("kiro-cli-autobuild", "Dry-run mode", "Preview prompts without calling the model", "debug"),
        # chatty-cli-buddy
        ("chatty-cli-buddy", "ReAct loop", "Iterative reasoning-and-action loop (up to 50 iterations)", "agent"),
        ("chatty-cli-buddy", "Permission model", "3-level: per-command, per-task, per-workspace trust", "security"),
        ("chatty-cli-buddy", "MCP tools", "Docker build/run/ps and GitHub commit/push automation", "devops"),
        ("chatty-cli-buddy", "Sub-agent delegation", "Spawns child agents for complex sub-tasks", "agent"),
        ("chatty-cli-buddy", "Bulletproof tool catcher", "Parses tool calls even from raw JSON in LLM content", "reliability"),
        ("chatty-cli-buddy", "OS-aware commands", "Adapts shell commands for Windows/Linux/macOS", "cross-platform"),
        # chronos
        ("chronos", "Desktop scanning", "Scans directory contents for organization", "automation"),
        ("chronos", "EMMA AI organizer", "AI proposes folder structures without auto-executing", "automation"),
        ("chronos", "Dual AI backend", "Supports local Ollama and Google Gemini", "llm"),
        # Chatty-FreeLLM-AllHandsOnDeck
        ("Chatty-FreeLLM-AllHandsOnDeck", "Provider rotation", "Switch between free LLM providers when rate-limited", "llm"),
        ("Chatty-FreeLLM-AllHandsOnDeck", "Aider integration", "Run aider CLI for autonomous file editing via web UI", "coding"),
        ("Chatty-FreeLLM-AllHandsOnDeck", "Task recommendations", "Suggests best model per task type (code, logs, writing)", "llm"),
        ("Chatty-FreeLLM-AllHandsOnDeck", "Live status dashboard", "Shows provider availability in real-time", "ui"),
        # chatty-local-data-LLM
        ("chatty-local-data-LLM", "OneNote ingestion", "Fetches pages via Microsoft Graph API with device code auth", "data"),
        ("chatty-local-data-LLM", "Content deduplication", "TF-IDF + cosine similarity to cluster and merge similar pages", "ml"),
        ("chatty-local-data-LLM", "RAG pipeline", "Chunk, embed, store in ChromaDB, retrieve top-5 for context", "rag"),
        ("chatty-local-data-LLM", "Privacy-first", "All processing local, no data leaves the machine", "security"),
        # Chatty-My-Agent
        ("Chatty-My-Agent", "50+ slash commands", "File ops, shell, DevOps, search, AI control, productivity, RAG", "cli"),
        ("Chatty-My-Agent", "7 LLM providers", "Gemini, Groq, Cohere, Mistral, OpenRouter, Together, HuggingFace", "llm"),
        ("Chatty-My-Agent", "Autonomous agent mode", "AI plans and executes multi-step tasks (max 10 steps)", "agent"),
        ("Chatty-My-Agent", "Plugin system", "Drop-in Python plugins at ~/.chatty-agent/plugins/", "extensibility"),
        ("Chatty-My-Agent", "Voice I/O", "STT via Groq Whisper, TTS via Windows SAPI", "accessibility"),
        ("Chatty-My-Agent", "Web UI", "Flask dark-theme interface with model/knowledge selector", "ui"),
        ("Chatty-My-Agent", "Persistent memory", "Teach AI facts that persist across sessions", "memory"),
        ("Chatty-My-Agent", "Auto-fallback LLM", "Seamlessly tries next provider if primary fails", "reliability"),
        ("Chatty-My-Agent", "Personas", "5 built-in AI personalities (default, senior_dev, eli5, reviewer, devops)", "ux"),
    ]
    for name, feat, desc, cat in features:
        cur.execute(
            "INSERT INTO features (project_id, name, description, category) "
            "SELECT id, ?, ?, ? FROM projects WHERE name=?",
            (feat, desc, cat, name)
        )


def populate_llm_providers(cur):
    providers = [
        # kiro-cli-autobuild
        ("kiro-cli-autobuild", "OpenAI", "any compatible model", "OpenAI Chat Completions API", 0),
        ("kiro-cli-autobuild", "Anthropic", "any model", "Anthropic Messages API", 0),
        ("kiro-cli-autobuild", "Ollama", "any model", "http://localhost:11434", 1),
        ("kiro-cli-autobuild", "llama.cpp", "any GGUF", "HTTP server or binary spawn", 1),
        # chatty-cli-buddy
        ("chatty-cli-buddy", "Ollama", "qwen2.5-coder", "http://localhost:11434", 1),
        # chronos
        ("chronos", "Ollama", "qwen3-coder:30b", "http://localhost:11434", 1),
        ("chronos", "Google Gemini", "gemini-1.5-flash", "generativelanguage.googleapis.com", 0),
        # Chatty-FreeLLM-AllHandsOnDeck
        ("Chatty-FreeLLM-AllHandsOnDeck", "Ollama", "qwen2.5-coder:14b", "http://localhost:11434", 1),
        ("Chatty-FreeLLM-AllHandsOnDeck", "NVIDIA NIM", "qwen2.5-coder-32b", "integrate.api.nvidia.com", 0),
        ("Chatty-FreeLLM-AllHandsOnDeck", "Groq", "llama-3.1-8b-instant", "api.groq.com", 0),
        ("Chatty-FreeLLM-AllHandsOnDeck", "Cerebras", None, "api.cerebras.ai", 0),
        ("Chatty-FreeLLM-AllHandsOnDeck", "Google Gemini", None, "generativelanguage.googleapis.com", 0),
        ("Chatty-FreeLLM-AllHandsOnDeck", "Mistral", None, "api.mistral.ai", 0),
        ("Chatty-FreeLLM-AllHandsOnDeck", "OpenRouter", None, "openrouter.ai", 0),
        # chatty-local-data-LLM
        ("chatty-local-data-LLM", "Ollama", "mistral", "http://localhost:11434", 1),
        # Chatty-My-Agent
        ("Chatty-My-Agent", "Google Gemini", "gemini-2.0-flash", "generativelanguage.googleapis.com", 0),
        ("Chatty-My-Agent", "Groq", "llama-3.3-70b", "api.groq.com", 0),
        ("Chatty-My-Agent", "Cohere", "command-r-plus", "api.cohere.com", 0),
        ("Chatty-My-Agent", "Mistral", "mistral-small-3.1", "api.mistral.ai", 0),
        ("Chatty-My-Agent", "OpenRouter", "meta-llama/llama-3.3-70b", "openrouter.ai", 0),
        ("Chatty-My-Agent", "Together AI", "llama-3.3-70b-turbo", "api.together.xyz", 0),
        ("Chatty-My-Agent", "HuggingFace", "qwen2.5-72b", "api-inference.huggingface.co", 0),
    ]
    for name, prov, model, endpoint, is_local in providers:
        cur.execute(
            "INSERT INTO llm_providers (project_id, provider, model, endpoint, is_local) "
            "SELECT id, ?, ?, ?, ? FROM projects WHERE name=?",
            (prov, model, endpoint, is_local, name)
        )


def populate_storage(cur):
    storage = [
        ("kiro-cli-autobuild", "filesystem", "specs/<slug>/", "Markdown spec files (requirements, design, tasks)"),
        ("kiro-cli-autobuild", "json_file", "kiro.config.json", "Provider configuration"),
        ("chatty-cli-buddy", "json_file", "src/storage/config.json", "Runtime configuration"),
        ("chatty-cli-buddy", "log_file", "src/storage/logs/chatty_runtime.log", "Runtime telemetry"),
        ("chatty-cli-buddy", "text_file", "~/.chatty_trusted_workspaces", "Trusted workspace paths"),
        ("chatty-cli-buddy", "in_memory", "self.messages", "Conversation history (not persisted)"),
        ("Chatty-FreeLLM-AllHandsOnDeck", "in_memory", "defaultdict(int)", "Per-session usage counts"),
        ("chatty-local-data-LLM", "chromadb", "./chroma_db/", "Vector embeddings for document chunks"),
        ("chatty-local-data-LLM", "json_files", "data/raw/*.json", "Raw OneNote pages"),
        ("chatty-local-data-LLM", "json_files", "data/consolidated/*.json", "Deduplicated merged pages"),
        ("Chatty-My-Agent", "chromadb", "~/.chatty-agent/vectordb/", "RAG vector embeddings"),
        ("Chatty-My-Agent", "json_file", "~/.chatty-agent/config.json", "Settings"),
        ("Chatty-My-Agent", "json_file", "~/.chatty-agent/memory.json", "Persistent AI memory"),
        ("Chatty-My-Agent", "json_file", "~/.chatty-agent/aliases.json", "Command aliases"),
        ("Chatty-My-Agent", "json_file", "~/.chatty-agent/stats.json", "Lifetime usage stats"),
        ("Chatty-My-Agent", "json_file", "~/.chatty-agent/history.json", "Last session history"),
    ]
    for name, stype, loc, desc in storage:
        cur.execute(
            "INSERT INTO storage_methods (project_id, type, location, description) "
            "SELECT id, ?, ?, ? FROM projects WHERE name=?",
            (stype, loc, desc, name)
        )


def populate_patterns(cur):
    patterns = [
        ("kiro-cli-autobuild", "spec-driven-dev", "Requirements → Design → Tasks → Implementation pipeline"),
        ("kiro-cli-autobuild", "provider-registry", "Pluggable provider pattern with index.js registry"),
        ("chatty-cli-buddy", "react-loop", "Reasoning and Action iterative loop with max iterations"),
        ("chatty-cli-buddy", "permission-escalation", "3-tier permission model (once, task, workspace)"),
        ("chatty-cli-buddy", "mcp-tools", "Model Context Protocol wrappers for Docker/GitHub"),
        ("chatty-cli-buddy", "sub-agent", "Child agent delegation for complex tasks"),
        ("chronos", "propose-dont-execute", "AI suggests changes but never auto-executes"),
        ("chronos", "dual-backend", "Local + cloud AI provider switching via config"),
        ("Chatty-FreeLLM-AllHandsOnDeck", "provider-rotation", "Switch providers on rate-limit (429) detection"),
        ("Chatty-FreeLLM-AllHandsOnDeck", "litellm-abstraction", "Unified LLM API via LiteLLM library"),
        ("chatty-local-data-LLM", "rag-pipeline", "Fetch → Deduplicate → Chunk → Embed → Query"),
        ("chatty-local-data-LLM", "tfidf-dedup", "TF-IDF + cosine similarity clustering for content dedup"),
        ("Chatty-My-Agent", "auto-fallback", "Try next provider on failure"),
        ("Chatty-My-Agent", "plugin-system", "Dynamic Python plugin loading from directory"),
        ("Chatty-My-Agent", "persistent-memory", "JSON-based fact storage across sessions"),
        ("Chatty-My-Agent", "autonomous-agent", "JSON action protocol (read/run/search/write/think/done)"),
    ]
    for name, pat, desc in patterns:
        cur.execute(
            "INSERT INTO architecture_patterns (project_id, pattern, description) "
            "SELECT id, ?, ? FROM projects WHERE name=?",
            (pat, desc, name)
        )


def populate_cross_references(cur):
    refs = [
        ("chatty-cli-buddy", "Chatty-My-Agent", "shared_concept: ReAct agent loop"),
        ("chatty-cli-buddy", "Chatty-My-Agent", "shared_concept: slash commands"),
        ("chatty-cli-buddy", "Chatty-My-Agent", "shared_dep: ollama, rich, duckduckgo-search"),
        ("Chatty-FreeLLM-AllHandsOnDeck", "Chatty-My-Agent", "shared_concept: multi-provider LLM"),
        ("Chatty-FreeLLM-AllHandsOnDeck", "chatty-cli-buddy", "shared_concept: FastAPI backend"),
        ("chatty-local-data-LLM", "Chatty-My-Agent", "shared_dep: chromadb"),
        ("chatty-local-data-LLM", "Chatty-My-Agent", "shared_concept: RAG pipeline"),
        ("chronos", "chatty-cli-buddy", "shared_dep: ollama"),
        ("chronos", "Chatty-FreeLLM-AllHandsOnDeck", "shared_concept: dual AI backend"),
        ("kiro-cli-autobuild", "chatty-cli-buddy", "evolution: spec planning feeds agent execution"),
        ("KIro_NotionAI_Style", "kiro-cli-autobuild", "shared_concept: kiro methodology scaffold"),
    ]
    for src, tgt, rel in refs:
        cur.execute(
            "INSERT INTO cross_references (source_project_id, target_project_id, relationship) "
            "SELECT s.id, t.id, ? FROM projects s, projects t WHERE s.name=? AND t.name=?",
            (rel, src, tgt)
        )


def main():
    db_existed = os.path.exists(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    create_schema(cur)
    populate_projects(cur)
    populate_dependencies(cur)
    populate_features(cur)
    populate_llm_providers(cur)
    populate_storage(cur)
    populate_patterns(cur)
    populate_cross_references(cur)

    conn.commit()

    # Print summary
    tables = ["projects", "dependencies", "features", "commands",
              "llm_providers", "storage_methods", "architecture_patterns", "cross_references"]
    print(f"\n{'='*50}")
    print(f"  Chatty Chronos v3 — Knowledge Database")
    print(f"  {'Created' if not db_existed else 'Updated'}: {DB_PATH}")
    print(f"{'='*50}\n")
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        count = cur.fetchone()[0]
        print(f"  {t:<25} {count:>4} records")
    print()

    conn.close()


if __name__ == "__main__":
    main()
