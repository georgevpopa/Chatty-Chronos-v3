"""Visual themes ported from Chatty Nemotron.

7 themes with glassmorphism support. Each theme defines:
- file: background image name (in static/)
- text: text color
- chat_bg: chat bubble background (rgba)
- chat_border: chat bubble border (rgba)
- input_bg: input field background (rgba)
- accent: accent color for highlights
- overlay: overlay gradient (rgba)
- text_shadow: CSS text-shadow
"""

THEMES = {
    "Minimal Light": {
        "file": "white.png",
        "text": "#2a2522",
        "chat_bg": "rgba(255, 255, 255, 0.55)",
        "chat_border": "rgba(200, 190, 175, 0.6)",
        "input_bg": "rgba(255, 255, 255, 0.8)",
        "accent": "#8b7355",
        "overlay": "rgba(255,255,255,0.08)",
        "text_shadow": "0 1px 2px rgba(0,0,0,0.1)",
    },
    "Cyber Dark": {
        "file": "dark.jpeg",
        "text": "#e0e0e0",
        "chat_bg": "rgba(0, 0, 0, 0.45)",
        "chat_border": "rgba(0, 255, 255, 0.25)",
        "input_bg": "rgba(0, 0, 0, 0.6)",
        "accent": "#00ffff",
        "overlay": "rgba(0,0,0,0.40)",
        "text_shadow": "0 1px 3px rgba(0,0,0,0.5)",
    },
    "Deep Purple": {
        "file": "purple.jpeg",
        "text": "#f0e6ff",
        "chat_bg": "rgba(30, 0, 50, 0.5)",
        "chat_border": "rgba(180, 100, 255, 0.35)",
        "input_bg": "rgba(20, 0, 35, 0.6)",
        "accent": "#b464ff",
        "overlay": "rgba(0,0,0,0.35)",
        "text_shadow": "0 1px 3px rgba(0,0,0,0.5)",
    },
    "Cybertron": {
        "file": "cybertron.jpeg",
        "text": "#e0f7fa",
        "chat_bg": "rgba(0, 20, 40, 0.6)",
        "chat_border": "rgba(0, 200, 255, 0.35)",
        "input_bg": "rgba(0, 25, 50, 0.75)",
        "accent": "#00c8ff",
        "overlay": "rgba(0,0,0,0.40)",
        "text_shadow": "0 1px 3px rgba(0,0,0,0.5)",
    },
    "Midnight Navy": {
        "file": "navy.jpeg",
        "text": "#e8eaf6",
        "chat_bg": "rgba(15, 25, 50, 0.55)",
        "chat_border": "rgba(100, 149, 237, 0.35)",
        "input_bg": "rgba(20, 30, 60, 0.7)",
        "accent": "#6495ed",
        "overlay": "rgba(0,0,0,0.35)",
        "text_shadow": "0 1px 3px rgba(0,0,0,0.5)",
    },
    "Forest Sage": {
        "file": "sage.jpeg",
        "text": "#f1f8e9",
        "chat_bg": "rgba(30, 50, 35, 0.5)",
        "chat_border": "rgba(129, 199, 132, 0.4)",
        "input_bg": "rgba(35, 55, 40, 0.65)",
        "accent": "#81c784",
        "overlay": "rgba(0,0,0,0.30)",
        "text_shadow": "0 1px 3px rgba(0,0,0,0.5)",
    },
    "Solar Gold": {
        "file": "gold.jpeg",
        "text": "#fff8e1",
        "chat_bg": "rgba(30, 20, 5, 0.55)",
        "chat_border": "rgba(255, 193, 7, 0.3)",
        "input_bg": "rgba(40, 25, 5, 0.7)",
        "accent": "#ffc107",
        "overlay": "rgba(0,0,0,0.40)",
        "text_shadow": "0 1px 3px rgba(0,0,0,0.5)",
    },
}


def get_theme(name: str) -> dict:
    """Get theme config by name. Falls back to Cybertron."""
    return THEMES.get(name, THEMES["Cybertron"])


def list_themes() -> list[str]:
    """Return list of available theme names."""
    return list(THEMES.keys())


def generate_theme_css(name: str) -> str:
    """Generate CSS for a given theme."""
    cfg = get_theme(name)
    return f"""
    :root {{
        --theme-text: {cfg['text']};
        --theme-chat-bg: {cfg['chat_bg']};
        --theme-chat-border: {cfg['chat_border']};
        --theme-input-bg: {cfg['input_bg']};
        --theme-accent: {cfg['accent']};
        --theme-overlay: {cfg['overlay']};
        --theme-text-shadow: {cfg['text_shadow']};
    }}
    .chat-bubble {{
        background: var(--theme-chat-bg);
        border: 1px solid var(--theme-chat-border);
        color: var(--theme-text);
        text-shadow: var(--theme-text-shadow);
        backdrop-filter: blur(12px);
        border-radius: 12px;
        padding: 12px 16px;
        margin: 8px 0;
    }}
    .chat-input {{
        background: var(--theme-input-bg);
        border: 1px solid var(--theme-chat-border);
        color: var(--theme-text);
        backdrop-filter: blur(12px);
        border-radius: 8px;
        padding: 10px 14px;
    }}
    .accent {{ color: var(--theme-accent); }}
    """
