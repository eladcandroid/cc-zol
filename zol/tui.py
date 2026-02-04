"""Terminal UI utilities for cc-zol."""

import json
import os
import sys
from pathlib import Path
from typing import Optional

from .config import DEFAULT_MODEL


def prompt(message: str, hide_input: bool = False) -> str:
    """
    Prompt for user input.

    Args:
        message: The prompt message to display
        hide_input: If True, don't echo input (for passwords)

    Returns:
        The user's input, stripped of whitespace
    """
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
    # Look for models.json in the package directory
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


def select_model(current_model: Optional[str] = None) -> str:
    """
    Interactive model selection.
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

    print("\n" + "=" * 60)
    print("SELECT A MODEL")
    print("=" * 60)

    if current_model:
        print(f"\nCurrent model: {current_model}")

    print(f"\nDefault: {DEFAULT_MODEL}")
    print("\n--- Popular Models ---\n")

    # Display popular models
    for i, model in enumerate(available_popular, 1):
        marker = " (default)" if model == DEFAULT_MODEL else ""
        current = " *" if model == current_model else ""
        print(f"  {i:2}. {model}{marker}{current}")

    print("\n--- Other Models ---\n")
    print("  Type a number, model name, or press Enter for default")
    print(f"  ({len(other_models)} more models available)")
    print()

    # Show a few other models as examples
    for i, model in enumerate(other_models[:5], len(available_popular) + 1):
        print(f"  {i:2}. {model}")
    if len(other_models) > 5:
        print(f"  ... and {len(other_models) - 5} more")

    print()
    print("  0. Show all models")
    print()

    while True:
        choice = prompt("Select model [Enter for default]: ").strip()

        # Default selection
        if not choice:
            print(f"\nSelected: {DEFAULT_MODEL}")
            return DEFAULT_MODEL

        # Show all models
        if choice == "0":
            print("\n--- All Available Models ---\n")
            all_sorted = available_popular + other_models
            for i, model in enumerate(all_sorted, 1):
                marker = " (default)" if model == DEFAULT_MODEL else ""
                current = " *" if model == current_model else ""
                print(f"  {i:3}. {model}{marker}{current}")
            print()
            continue

        # Numeric selection
        if choice.isdigit():
            idx = int(choice) - 1
            all_sorted = available_popular + other_models
            if 0 <= idx < len(all_sorted):
                selected = all_sorted[idx]
                print(f"\nSelected: {selected}")
                return selected
            print("Invalid number. Try again.")
            continue

        # Direct model name input
        if choice in model_ids:
            print(f"\nSelected: {choice}")
            return choice

        # Fuzzy search
        matches = [m for m in model_ids if choice.lower() in m.lower()]
        if len(matches) == 1:
            print(f"\nSelected: {matches[0]}")
            return matches[0]
        elif len(matches) > 1:
            print(f"\nMultiple matches found:")
            for i, m in enumerate(matches[:10], 1):
                print(f"  {i}. {m}")
            if len(matches) > 10:
                print(f"  ... and {len(matches) - 10} more")
            continue

        print("Model not found. Try again or press Enter for default.")
