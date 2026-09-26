"""Spec Generator — AI-assisted spec-driven development.

Workflow: /spec new "feature" → generates requirements.md, design.md, tasks.md
Each phase can be AI-generated using the active LLM model.
"""
import os
import re
from pathlib import Path
from rich.console import Console

from core.config import Config
from llm import ollama_provider

console = Console()

TEMPLATES_DIR = Path(__file__).parent / "templates"
SPECS_DIR = Path("specs")


def slugify(text: str) -> str:
    """Convert feature name to folder-safe slug."""
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[\s_]+", "-", slug).strip("-")


def get_steering_context() -> str:
    """Load STEERING.md if it exists in the project root."""
    steering = Path("STEERING.md")
    if steering.exists():
        return f"\n## Project Context (from STEERING.md):\n{steering.read_text(encoding='utf-8')}\n"
    return ""


def create_spec(feature_name: str, ai_generate: bool = False, config: Config = None):
    """Create a new spec folder with templates (optionally AI-generated)."""
    slug = slugify(feature_name)
    spec_dir = SPECS_DIR / slug
    spec_dir.mkdir(parents=True, exist_ok=True)

    files_created = []

    if ai_generate and config:
        steering = get_steering_context()

        # Generate requirements
        console.print(f"  [dim]Generating requirements...[/dim]")
        req_content = _generate_phase(
            feature_name, "requirements", steering, config
        )
        (spec_dir / "requirements.md").write_text(req_content, encoding="utf-8")
        files_created.append("requirements.md")

        # Generate design
        console.print(f"  [dim]Generating design...[/dim]")
        design_content = _generate_phase(
            feature_name, "design", steering + f"\n## Requirements:\n{req_content}\n", config
        )
        (spec_dir / "design.md").write_text(design_content, encoding="utf-8")
        files_created.append("design.md")

        # Generate tasks
        console.print(f"  [dim]Generating tasks...[/dim]")
        tasks_content = _generate_phase(
            feature_name, "tasks", steering + f"\n## Design:\n{design_content}\n", config
        )
        (spec_dir / "tasks.md").write_text(tasks_content, encoding="utf-8")
        files_created.append("tasks.md")

    else:
        # Copy templates with feature name substituted
        for template_name in ["requirements.md", "design.md", "tasks.md"]:
            template = TEMPLATES_DIR / template_name
            content = template.read_text(encoding="utf-8")
            content = content.replace("{feature_name}", feature_name)
            (spec_dir / template_name).write_text(content, encoding="utf-8")
            files_created.append(template_name)

    return str(spec_dir), files_created


def _generate_phase(feature_name: str, phase: str, context: str, config: Config) -> str:
    """Use LLM to generate a spec phase."""
    prompts = {
        "requirements": (
            f"Generate a detailed requirements document for: '{feature_name}'\n"
            "Include: overview, user stories, functional requirements, "
            "non-functional requirements, acceptance criteria, and out of scope.\n"
            "Use markdown format with checkboxes for requirements."
        ),
        "design": (
            f"Generate a technical design document for: '{feature_name}'\n"
            "Include: architecture, components, data model, API/interface design, "
            "error handling, security considerations, dependencies, and alternatives.\n"
            "Use markdown format."
        ),
        "tasks": (
            f"Generate an implementation task breakdown for: '{feature_name}'\n"
            "Include: phased tasks (setup, core, testing, polish), "
            "specific actionable items with checkboxes, and definition of done.\n"
            "Use markdown format."
        ),
    }

    messages = [
        {"role": "system", "content": (
            "You are a senior software architect. Generate clear, actionable spec documents. "
            "Be specific and practical. Use markdown formatting."
            + context
        )},
        {"role": "user", "content": prompts[phase]},
    ]

    provider = config.get("provider", "ollama")
    model = config.get("model")
    
    # Check if provider is a cloud provider
    from llm.fallback import get_available_providers
    cloud_provider = None
    for p in get_available_providers():
        if p["name"] == provider:
            cloud_provider = p
            break

    if provider == "llamacpp":
        from llm import llamacpp_provider
        host = config.get("llamacpp_host", "http://localhost:8080")
        llamacpp_timeout = int(config.get("llamacpp_timeout", 600))
        response = llamacpp_provider.chat(messages, host, model, timeout=llamacpp_timeout)
    elif cloud_provider:
        from llm import openai_provider
        active_model = config.get("model") or cloud_provider.get("model")
        response = openai_provider.chat(
            messages,
            base_url=cloud_provider["base_url"],
            api_key_name=cloud_provider["env_key"],
            model=active_model
        )
    else:
        host = config.get("ollama_host", "http://localhost:11434")
        response = ollama_provider.chat(messages, model, host)
    return response.message.content or ""


def list_specs() -> list[dict]:
    """List all existing specs."""
    if not SPECS_DIR.exists():
        return []
    specs = []
    for d in sorted(SPECS_DIR.iterdir()):
        if d.is_dir():
            files = [f.name for f in d.iterdir() if f.suffix == ".md"]
            specs.append({"name": d.name, "path": str(d), "files": files})
    return specs
