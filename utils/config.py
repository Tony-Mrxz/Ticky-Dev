import os
import json

CONFIG_FILE = os.path.expanduser("~/.ticky_config.json")

def load_config():
    """Load all config parameters as a dictionary."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_config(config_data):
    """Save/update config parameters."""
    try:
        current = load_config()
        current.update(config_data)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(current, f, indent=4)
    except Exception:
        pass

def load_position(default_x=100, default_y=100):
    """Load the window position (x, y) from configuration."""
    data = load_config()
    return data.get("x", default_x), data.get("y", default_y)

def save_position(x, y):
    """Save the window position (x, y) to configuration."""
    save_config({"x": x, "y": y})

def load_always_on_top(default_value=True):
    """Load the always_on_top boolean setting."""
    return load_config().get("always_on_top", default_value)

def save_always_on_top(value):
    """Save the always_on_top boolean setting."""
    save_config({"always_on_top": value})

def load_accent_color(default_hex="#FF9F0A"):
    """Load the accent color hex value."""
    return load_config().get("accent_color", default_hex)

def save_accent_color(value):
    """Save the accent color hex value."""
    save_config({"accent_color": value})

def load_use_24h(default_value=True):
    """Load whether to use 24-hour clock format."""
    return load_config().get("use_24h", default_value)

def save_use_24h(value):
    """Save whether to use 24-hour clock format."""
    save_config({"use_24h": value})

def load_show_date(default_value=True):
    """Load whether to display the date."""
    return load_config().get("show_date", default_value)

def save_show_date(value):
    """Save whether to display the date."""
    save_config({"show_date": value})

def load_task_font_size(default_value=13):
    """Load task font size."""
    return load_config().get("task_font_size", default_value)

def save_task_font_size(value):
    """Save task font size."""
    save_config({"task_font_size": value})

def load_pin_position(default_value=False):
    """Load whether main window position dragging is pinned/locked."""
    return load_config().get("pin_position", default_value)

def save_pin_position(value):
    """Save whether main window position dragging is pinned/locked."""
    save_config({"pin_position": value})

def load_spotify_credentials():
    """Load Spotify API Client ID and Secret."""
    data = load_config()
    return data.get("spotify_client_id", ""), data.get("spotify_client_secret", "")

def save_spotify_credentials(client_id, client_secret):
    """Save Spotify API Client ID and Secret."""
    save_config({
        "spotify_client_id": client_id,
        "spotify_client_secret": client_secret
    })

def load_spotify_tokens():
    """Load saved access and refresh tokens."""
    data = load_config()
    return data.get("spotify_access_token", ""), data.get("spotify_refresh_token", "")

def save_spotify_tokens(access_token, refresh_token):
    """Save access and refresh tokens."""
    save_config({
        "spotify_access_token": access_token,
        "spotify_refresh_token": refresh_token
    })

def load_spotify_demo_mode(default_value=False):
    """Load whether Spotify demo mode is enabled."""
    return load_config().get("spotify_demo_mode", default_value)

def save_spotify_demo_mode(value):
    """Save whether Spotify demo mode is enabled."""
    save_config({"spotify_demo_mode": value})

def load_theme(default_value="Obsidian"):
    """Load the selected UI color theme name."""
    return load_config().get("ui_theme", default_value)

def save_theme(value):
    """Save the selected UI color theme name."""
    save_config({"ui_theme": value})

def load_tasks():
    """Load the list of active tasks."""
    return load_config().get("tasks", [])

def save_tasks(tasks_list):
    """Save the list of active tasks."""
    save_config({"tasks": tasks_list})

def load_font_family(default_value="Inter"):
    """Load the selected font family."""
    return load_config().get("font_family", default_value)

def save_font_family(value):
    """Save the selected font family."""
    save_config({"font_family": value})

def load_clock_weight(default_value="700"):
    """Load the clock font weight."""
    return load_config().get("clock_weight", default_value)

def save_clock_weight(value):
    """Save the clock font weight."""
    save_config({"clock_weight": value})

def load_show_seconds(default_value=True):
    """Load whether to show seconds on clock."""
    return load_config().get("show_seconds", default_value)

def save_show_seconds(value):
    """Save whether to show seconds on clock."""
    save_config({"show_seconds": value})

def load_clock_style(default_value="neon"):
    """Load the selected clock display style."""
    return load_config().get("clock_style", default_value)

def save_clock_style(value):
    """Save the selected clock display style."""
    save_config({"clock_style": value})

def load_clock_box_bg(default_value=False):
    """Load whether to show the glass background box behind the clock."""
    return load_config().get("clock_box_bg", default_value)

def save_clock_box_bg(value):
    """Save whether to show the glass background box behind the clock."""
    save_config({"clock_box_bg": value})

def load_stick_on_desktop(default_value=False):
    """Load whether stick on desktop mode is enabled."""
    return load_config().get("stick_on_desktop", default_value)

def save_stick_on_desktop(value):
    """Save whether stick on desktop mode is enabled."""
    save_config({"stick_on_desktop": value})

def load_minimize_on_idle(default_value=False):
    """Load whether to minimize the widget on user idle."""
    return load_config().get("minimize_on_idle", default_value)

def save_minimize_on_idle(value):
    """Save whether to minimize the widget on user idle."""
    save_config({"minimize_on_idle": value})

def load_idle_minutes(default_value=5):
    """Load the number of minutes of idle time before minimizing."""
    return load_config().get("idle_minutes", default_value)

def save_idle_minutes(value):
    """Save the number of minutes of idle time before minimizing."""
    save_config({"idle_minutes": value})

def load_start_on_startup(default_value=True):
    """Load whether Ticky should start automatically on Windows startup."""
    return load_config().get("start_on_startup", default_value)

def save_start_on_startup(value):
    """Save whether Ticky should start automatically on Windows startup."""
    save_config({"start_on_startup": value})

def load_gemini_api_key():
    """Load saved Gemini API Key."""
    return load_config().get("gemini_api_key", "")

def save_gemini_api_key(api_key):
    """Save Gemini API Key."""
    save_config({"gemini_api_key": api_key})

def load_ai_provider(default_value="Gemini"):
    """Load selected AI Provider."""
    return load_config().get("ai_provider", default_value)

def save_ai_provider(value):
    """Save selected AI Provider."""
    save_config({"ai_provider": value})

def load_ai_api_key():
    """Load saved AI API Key (falls back to Gemini API key for backward compatibility)."""
    data = load_config()
    return data.get("ai_api_key", data.get("gemini_api_key", ""))

def save_ai_api_key(value):
    """Save AI API Key."""
    save_config({"ai_api_key": value})

def load_ai_model(default_value="gemini-1.5-flash"):
    """Load selected AI Model."""
    return load_config().get("ai_model", default_value)

def save_ai_model(value):
    """Save selected AI Model."""
    save_config({"ai_model": value})
