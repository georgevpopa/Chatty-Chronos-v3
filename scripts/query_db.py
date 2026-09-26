"""Chatty Chronos v3 — Query the knowledge database."""
import sqlite3
import sys
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "db")


def query_db(sql, params=()):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return rows


def show_projects():
    rows = query_db("SELECT name, language, status, purpose FROM projects ORDER BY name")
    print(f"\n{'Project':<35} {'Lang':<12} {'Status':<12} Purpose")
    print("-" * 110)
    for r in rows:
        print(f"{r['name']:<35} {r['language'] or '-':<12} {r['status']:<12} {r['purpose'][:50]}")


def show_providers():
    rows = query_db("""
        SELECT p.name as project, lp.provider, lp.model, lp.endpoint, lp.is_local
        FROM llm_providers lp JOIN projects p ON lp.project_id = p.id
        ORDER BY lp.provider, p.name
    """)
    print(f"\n{'Provider':<18} {'Model':<25} {'Local':<6} Project")
    print("-" * 90)
    for r in rows:
        local = "YES" if r['is_local'] else ""
        print(f"{r['provider']:<18} {(r['model'] or '-'):<25} {local:<6} {r['project']}")


def show_features(project=None):
    if project:
        rows = query_db("""
            SELECT f.name, f.description, f.category FROM features f
            JOIN projects p ON f.project_id = p.id WHERE p.name = ?
        """, (project,))
        print(f"\nFeatures for {project}:")
    else:
        rows = query_db("""
            SELECT p.name as project, f.name, f.category FROM features f
            JOIN projects p ON f.project_id = p.id ORDER BY f.category, p.name
        """)
        print(f"\n{'Category':<15} {'Project':<35} Feature")
        print("-" * 90)
    for r in rows:
        if project:
            print(f"  [{r['category']}] {r['name']} — {r['description']}")
        else:
            print(f"{r['category']:<15} {r['project']:<35} {r['name']}")


def show_cross_refs():
    rows = query_db("""
        SELECT s.name as source, t.name as target, cr.relationship
        FROM cross_references cr
        JOIN projects s ON cr.source_project_id = s.id
        JOIN projects t ON cr.target_project_id = t.id
    """)
    print(f"\n{'Source':<35} {'Target':<35} Relationship")
    print("-" * 110)
    for r in rows:
        print(f"{r['source']:<35} {r['target']:<35} {r['relationship']}")


def show_patterns():
    rows = query_db("""
        SELECT p.name as project, ap.pattern, ap.description
        FROM architecture_patterns ap JOIN projects p ON ap.project_id = p.id
        ORDER BY ap.pattern
    """)
    print(f"\n{'Pattern':<25} {'Project':<35} Description")
    print("-" * 110)
    for r in rows:
        print(f"{r['pattern']:<25} {r['project']:<35} {r['description'][:50]}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "help":
        print("Usage: python query_db.py <command> [project_name]")
        print("  projects   — List all projects")
        print("  providers  — List all LLM providers")
        print("  features   — List all features (optionally filter by project)")
        print("  patterns   — List architecture patterns")
        print("  refs       — Show cross-references between projects")
        print("  sql <query> — Run raw SQL")
    elif args[0] == "projects":
        show_projects()
    elif args[0] == "providers":
        show_providers()
    elif args[0] == "features":
        show_features(args[1] if len(args) > 1 else None)
    elif args[0] == "patterns":
        show_patterns()
    elif args[0] == "refs":
        show_cross_refs()
    elif args[0] == "sql" and len(args) > 1:
        rows = query_db(" ".join(args[1:]))
        for r in rows:
            print(dict(r))
