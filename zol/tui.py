"""Terminal UI utilities for cc-zol."""

import json
import sys
import tty
import termios
from pathlib import Path
from typing import Optional

from .config import DEFAULT_MODEL


def prompt(message: str, hide_input: bool = False) -> str:
    """Prompt for user input."""
    if hide_input:
        import getpass
        return getpass.getpass(message).strip()

    sys.stdout.write(message)
    sys.stdout.flush()
    return input().strip()


def prompt_email() -> str:
    """Prompt for email address with basic validation."""
    while True:
        email = prompt("Enter your email: ")
        if "@" in email and "." in email:
            return email
        print("Please enter a valid email address.")


def prompt_code() -> str:
    """Prompt for verification code."""
    return prompt("Enter code: ")


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"Error: {message}", file=sys.stderr)


def print_success(message: str) -> None:
    """Print a success message."""
    print(message)


def print_info(message: str) -> None:
    """Print an info message."""
    print(message)


def load_available_models() -> list[dict]:
    """Load available models from models.json."""
    package_dir = Path(__file__).parent.parent
    models_file = package_dir / "models.json"

    if not models_file.exists():
        return []

    try:
        data = json.loads(models_file.read_text())
        return data.get("data", [])
    except (json.JSONDecodeError, OSError):
        return []


def get_popular_models() -> list[str]:
    """Get list of popular/recommended models."""
    return [
        "moonshotai/kimi-k2.5",
        "moonshotai/kimi-k2-thinking",
        "deepseek-ai/deepseek-v3.2",
        "deepseek-ai/deepseek-v3.1",
        "qwen/qwq-32b",
        "qwen/qwen3-235b-a22b",
        "mistralai/mistral-large-3-675b-instruct-2512",
        "meta/llama-3.3-70b-instruct",
        "google/gemma-3-27b-it",
    ]


def getch():
    """Read a single character from stdin without echo."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        # Handle escape sequences (arrow keys)
        if ch == '\x1b':
            ch2 = sys.stdin.read(1)
            ch3 = sys.stdin.read(1)
            if ch2 == '[':
                if ch3 == 'A':
                    return 'UP'
                elif ch3 == 'B':
                    return 'DOWN'
                elif ch3 == 'C':
                    return 'RIGHT'
                elif ch3 == 'D':
                    return 'LEFT'
            return 'ESC'
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def fuzzy_match(query: str, text: str) -> bool:
    """Simple fuzzy matching - all query chars must appear in order."""
    query = query.lower()
    text = text.lower()

    # Simple contains match
    if query in text:
        return True

    # Fuzzy match - chars in order
    qi = 0
    for char in text:
        if qi < len(query) and char == query[qi]:
            qi += 1
    return qi == len(query)


def fuzzy_score(query: str, text: str) -> int:
    """Score for sorting fuzzy matches. Lower is better."""
    query = query.lower()
    text = text.lower()

    # Exact match
    if query == text:
        return 0

    # Starts with
    if text.startswith(query):
        return 1

    # Contains
    if query in text:
        return 2 + text.index(query)

    # Fuzzy
    return 100


def interactive_select(
    items: list[str],
    title: str = "Select an option",
    default: Optional[str] = None,
    current: Optional[str] = None,
) -> Optional[str]:
    """
    Interactive selection with arrow keys and fuzzy search.

    Controls:
    - ↑/↓: Navigate
    - Type: Filter (fuzzy search)
    - Enter: Select
    - Esc/Ctrl+C: Cancel
    - Backspace: Clear filter
    """
    if not items:
        return default

    query = ""
    selected_idx = 0
    visible_count = 15  # Max items to show

    # Find default/current in list
    if current and current in items:
        selected_idx = items.index(current)
    elif default and default in items:
        selected_idx = items.index(default)

    def get_filtered_items():
        if not query:
            return items
        filtered = [i for i in items if fuzzy_match(query, i)]
        # Sort by match quality
        filtered.sort(key=lambda x: fuzzy_score(query, x))
        return filtered

    def render():
        # Clear screen and move cursor to top
        sys.stdout.write('\033[2J\033[H')

        filtered = get_filtered_items()

        # Title
        print(f"\033[1m{title}\033[0m")
        print("─" * 50)

        # Search box
        if query:
            print(f"🔍 Search: {query}_")
        else:
            print("🔍 Type to search...")
        print()

        # Instructions
        print("\033[90m↑/↓ Navigate  Enter Select  Esc Cancel  Type to filter\033[0m")
        print()

        if not filtered:
            print("\033[33mNo matches found\033[0m")
            return filtered

        # Calculate visible window
        total = len(filtered)
        start = max(0, min(selected_idx - visible_count // 2, total - visible_count))
        end = min(start + visible_count, total)

        # Show scroll indicator if needed
        if start > 0:
            print(f"  \033[90m↑ {start} more above\033[0m")

        # Show items
        for i in range(start, end):
            item = filtered[i]
            prefix = "→ " if i == selected_idx else "  "

            # Highlight selected
            if i == selected_idx:
                line = f"\033[7m{prefix}{item}\033[0m"
            else:
                line = f"{prefix}{item}"

            # Mark default/current
            markers = []
            if item == default:
                markers.append("\033[32m(default)\033[0m")
            if item == current:
                markers.append("\033[36m(current)\033[0m")

            if markers:
                line += " " + " ".join(markers)

            print(line)

        # Show scroll indicator if needed
        if end < total:
            print(f"  \033[90m↓ {total - end} more below\033[0m")

        print()
        print(f"\033[90m{len(filtered)}/{len(items)} models\033[0m")

        return filtered

    try:
        while True:
            filtered = render()

            ch = getch()

            if ch == 'UP':
                if filtered:
                    selected_idx = max(0, selected_idx - 1)
            elif ch == 'DOWN':
                if filtered:
                    selected_idx = min(len(filtered) - 1, selected_idx + 1)
            elif ch == '\r' or ch == '\n':  # Enter
                if filtered and 0 <= selected_idx < len(filtered):
                    # Clear screen before returning
                    sys.stdout.write('\033[2J\033[H')
                    return filtered[selected_idx]
            elif ch == 'ESC' or ch == '\x03':  # Esc or Ctrl+C
                sys.stdout.write('\033[2J\033[H')
                return None
            elif ch == '\x7f' or ch == '\x08':  # Backspace
                query = query[:-1]
                selected_idx = 0
            elif ch.isprintable():
                query += ch
                selected_idx = 0

    except KeyboardInterrupt:
        sys.stdout.write('\033[2J\033[H')
        return None


def select_model(current_model: Optional[str] = None) -> str:
    """
    Interactive model selection with fuzzy search.
    Returns the selected model ID.
    """
    all_models = load_available_models()
    popular = get_popular_models()

    # Build model list - popular first, then rest
    model_ids = [m["id"] for m in all_models]

    # Filter popular models to only those available
    available_popular = [m for m in popular if m in model_ids]

    # Get remaining models sorted alphabetically
    other_models = sorted([m for m in model_ids if m not in available_popular])

    # Combine: popular first, then others
    all_sorted = available_popular + other_models

    if not all_sorted:
        # Fallback if no models.json
        print_info(f"No models found. Using default: {DEFAULT_MODEL}")
        return DEFAULT_MODEL

    selected = interactive_select(
        items=all_sorted,
        title="SELECT A MODEL",
        default=DEFAULT_MODEL,
        current=current_model,
    )

    if selected:
        print_success(f"Selected: {selected}")
        return selected
    else:
        print_info(f"Cancelled. Using default: {DEFAULT_MODEL}")
        return current_model or DEFAULT_MODEL
