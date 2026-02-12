"""cc-zol CLI entry point."""

import os
import sys
import asyncio
from typing import Optional

import click
import httpx

from .config import LocalConfig, DEFAULT_MODEL, AUTH_SERVER_URL
from .server_manager import ServerManager
from .tui import (
    prompt_email,
    prompt_code,
    print_error,
    print_success,
    print_info,
    select_model,
)


def run_async(coro):
    """Run an async coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


async def send_verification_code(server_url: str, email: str) -> bool:
    """Request verification code from server."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{server_url}/auth/send-code",
                json={"email": email},
                timeout=30.0,
            )
            return response.status_code == 200
        except httpx.RequestError as e:
            print_error(f"Failed to connect to server: {e}")
            return False


async def verify_code_and_get_token(
    server_url: str, email: str, code: str
) -> Optional[str]:
    """Verify code and get token from server."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{server_url}/auth/verify",
                json={"email": email, "code": code},
                timeout=30.0,
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("token")
            else:
                error = response.json().get("detail", "Verification failed")
                print_error(error)
                return None
        except httpx.RequestError as e:
            print_error(f"Failed to connect to server: {e}")
            return None


async def fetch_provider_config(server_url: str, token: str) -> Optional[dict]:
    """Fetch provider configuration from auth server.

    Returns dict with provider_api_key, provider_base_url, model.
    User never stores these locally - fetched fresh each session.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{server_url}/auth/config",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30.0,
            )
            if response.status_code == 200:
                return response.json()
            else:
                error = response.json().get("detail", "Failed to get config")
                print_error(f"Config error: {error}")
                return None
        except httpx.RequestError as e:
            print_error(f"Failed to connect to server: {e}")
            return None


def start_claude(token: str, port: int, model: str, extra_args: list = None) -> None:
    """Start Claude Code with the proxy environment variables.

    Args:
        token: Auth token for the proxy
        port: Local proxy port
        model: Model name
        extra_args: Additional CLI arguments to pass through to claude
    """
    env = os.environ.copy()
    env["ANTHROPIC_AUTH_TOKEN"] = token
    env["ANTHROPIC_BASE_URL"] = f"http://localhost:{port}"
    env["MODEL"] = model

    args = ["claude", f"--model={model}"] + (extra_args or [])

    # Replace current process with claude
    try:
        os.execvpe("claude", args, env)
    except FileNotFoundError:
        print_error("Claude Code CLI not found. Please install it first.")
        print_info("Visit: https://docs.anthropic.com/claude-code")
        sys.exit(1)


def do_login(config: LocalConfig, with_model_selection: bool = True) -> Optional[str]:
    """
    Perform interactive login flow against remote auth server.
    Returns token on success, None on failure.
    """
    email = prompt_email()

    # Send verification code (to remote auth server)
    print_info("Sending verification code...")
    if not run_async(send_verification_code(AUTH_SERVER_URL, email)):
        print_error("Failed to send verification code")
        return None

    print_info("Verification code sent! Check your email.")
    code = prompt_code()

    # Verify and get token (from remote auth server)
    token = run_async(verify_code_and_get_token(AUTH_SERVER_URL, email, code))
    if not token:
        return None

    # Model selection on first login
    model = None
    if with_model_selection:
        model = select_model()

    # Save credentials
    config.save(email, token, model)
    print_success(f"Logged in as {email}")
    return token


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """cc-zol - Claude Code with email verification"""
    if ctx.invoked_subcommand is None:
        main_flow()


# Known cc-zol subcommand names (kept in sync with @cli.command definitions below)
_SUBCOMMANDS = {"login", "logout", "status", "stop", "model", "test", "update"}


def entry():
    """Entry point that passes unknown args through to Claude Code.

    If the first argument is a known cc-zol subcommand or --help,
    delegate to Click. Otherwise treat all args as Claude Code flags
    and pass them through (e.g. cc-zol -p "explain this code").
    """
    args = sys.argv[1:]
    if not args or args[0] in _SUBCOMMANDS or args[0] in ("--help", "-h"):
        cli()
    else:
        main_flow(args)


@cli.command()
def login():
    """Force re-login with a new email."""
    config = LocalConfig.load()
    server_manager = ServerManager()

    # Perform login with model selection (against remote auth server)
    token = do_login(config, with_model_selection=True)
    if token:
        # Fetch provider config from auth server
        print_info("Fetching configuration...")
        provider_config = run_async(fetch_provider_config(AUTH_SERVER_URL, token))
        if not provider_config:
            print_error("Failed to get provider configuration")
            sys.exit(1)

        # User's local model selection takes precedence over server default
        model = config.get_model() or provider_config.get("model")

        # Override the provider_config model with user's selection for the server
        provider_config["model"] = model

        # Start/restart server with provider config
        if server_manager.is_running():
            server_manager.stop()
        print_info("Starting server...")
        port = server_manager.start(provider_config=provider_config)

        print_info("Starting Claude...")
        start_claude(token, port, model)


@cli.command()
def logout():
    """Clear saved credentials."""
    config = LocalConfig.load()

    if config.is_logged_in():
        email = config.email
        config.clear()
        print_success(f"Logged out from {email}")
    else:
        print_info("Not logged in")


@cli.command()
def status():
    """Show current user and server status."""
    config = LocalConfig.load()
    server_manager = ServerManager()

    # User status
    if config.is_logged_in():
        print_info(f"Logged in as: {config.email}")
    else:
        print_info("Not logged in")

    # Model status
    print_info(f"Model: {config.get_model()}")

    # Server status
    if server_manager.is_running():
        print_info(f"Server: running on port {server_manager.get_port()}")
    else:
        print_info("Server: not running")


@cli.command()
def stop():
    """Stop the background server."""
    server_manager = ServerManager()

    if server_manager.stop():
        print_success("Server stopped")
    else:
        print_info("Server was not running")


@cli.command()
def model():
    """Change the model."""
    config = LocalConfig.load()
    current = config.get_model()

    # Select new model
    new_model = select_model(current_model=current)

    if new_model != current:
        config.save_model(new_model)
        print_success(f"Model changed to: {new_model}")
        print_info("Restart Claude Code to use the new model.")
    else:
        print_info(f"Model unchanged: {new_model}")


async def send_test_prompt(port: int, prompt: str, model: str) -> tuple[bool, str]:
    """Send a test prompt to the local proxy and check for response.

    Returns (success, message) tuple.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"http://localhost:{port}/v1/messages",
                json={
                    "model": model,
                    "max_tokens": 256,
                    "messages": [{"role": "user", "content": prompt}],
                },
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": "test",
                },
                timeout=60.0,
            )

            if response.status_code == 200:
                data = response.json()
                content = data.get("content", [])

                if content:
                    # Extract text and thinking from response
                    text = ""
                    thinking = ""
                    for block in content:
                        if block.get("type") == "text":
                            text += block.get("text", "")
                        elif block.get("type") == "thinking":
                            thinking += block.get("thinking", "")

                    # Show text if available, otherwise show thinking preview
                    text = text.strip()
                    thinking = thinking.strip()

                    if text:
                        return True, text
                    elif thinking:
                        preview = thinking[:150] + "..." if len(thinking) > 150 else thinking
                        return True, f"[Thinking] {preview}"

                return False, "Empty response from API"
            else:
                error = response.json().get("error", {}).get("message", response.text)
                return False, f"API error ({response.status_code}): {error}"

        except httpx.TimeoutException:
            return False, "Request timed out (60s)"
        except httpx.RequestError as e:
            return False, f"Connection error: {e}"
        except Exception as e:
            return False, f"Error: {e}"


@cli.command()
@click.argument("prompt", default="Say 'hello' in one word", required=False)
def test(prompt: str):
    """Test the API with a prompt and check if it responds."""
    config = LocalConfig.load()
    server_manager = ServerManager()

    if not config.is_logged_in():
        print_error("Not logged in. Run 'cc-zol login' first.")
        sys.exit(1)

    # Fetch provider config
    print_info("Fetching configuration...")
    provider_config = run_async(fetch_provider_config(AUTH_SERVER_URL, config.token))
    if not provider_config:
        print_error("Failed to get provider configuration.")
        sys.exit(1)

    # User's local model selection takes precedence
    model = config.get_model() or provider_config.get("model")
    provider_config["model"] = model

    # Ensure server is running (don't restart if already running)
    if not server_manager.is_running():
        print_info("Starting server...")
        port = server_manager.start(provider_config=provider_config)
    else:
        port = server_manager.get_port()
        print_info(f"Using existing server on port {port}")

    print_info(f"Model: {model}")
    print_info(f"Prompt: {prompt}")
    print_info("Sending test request...")

    success, result = run_async(send_test_prompt(port, prompt, model))

    if success:
        print_success("API is working!")
        print_info(f"Response: {result[:200]}{'...' if len(result) > 200 else ''}")
    else:
        print_error(f"API test failed: {result}")
        sys.exit(1)


def get_latest_commit_sha() -> Optional[str]:
    """Fetch the latest commit SHA from GitHub."""
    try:
        response = run_async(_fetch_latest_commit())
        return response
    except Exception:
        return None


async def _fetch_latest_commit() -> Optional[str]:
    """Async fetch latest commit SHA from GitHub API."""
    async with httpx.AsyncClient() as client:
        try:
            from .config import GITHUB_REPO
            response = await client.get(
                f"https://api.github.com/repos/{GITHUB_REPO}/commits/main",
                headers={"Accept": "application/vnd.github.v3+json"},
                timeout=10.0,
            )
            if response.status_code == 200:
                return response.json().get("sha")
        except Exception:
            pass
    return None


def format_update_time(iso_time: str) -> str:
    """Format ISO timestamp to human-readable string."""
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(iso_time)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return iso_time


@cli.command()
def update():
    """Update cc-zol to the latest version."""
    import subprocess
    from .config import GITHUB_REPO

    config = LocalConfig.load()
    last_commit, last_time = config.get_update_info()

    # Show last update time if available
    if last_time:
        print_info(f"Last updated: {format_update_time(last_time)}")

    # Fetch latest commit from GitHub
    print_info("Checking for updates...")
    latest_commit = get_latest_commit_sha()

    if latest_commit and last_commit:
        if latest_commit == last_commit:
            print_success("Already up to date!")
            return

    print_info("Updating cc-zol...")

    # Use uv tool install with --force to update
    repo_url = f"git+https://github.com/{GITHUB_REPO}.git"

    try:
        result = subprocess.run(
            ["uv", "tool", "install", repo_url, "--force"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            # Save the new commit SHA and timestamp
            if latest_commit:
                config.save_update_info(latest_commit)
            print_success("cc-zol updated successfully!")
            print_info("Restart your terminal or run 'cc-zol' to use the new version.")
        else:
            # Check if uv is not installed
            if "uv" in result.stderr.lower() or result.returncode == 127:
                print_error("uv is not installed. Installing uv first...")
                # Try to install uv
                uv_install = subprocess.run(
                    ["sh", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"],
                    capture_output=True,
                    text=True,
                )
                if uv_install.returncode == 0:
                    print_info("uv installed. Retrying update...")
                    # Retry the update
                    result = subprocess.run(
                        ["uv", "tool", "install", repo_url, "--force"],
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode == 0:
                        if latest_commit:
                            config.save_update_info(latest_commit)
                        print_success("cc-zol updated successfully!")
                        return
            print_error(f"Update failed: {result.stderr or result.stdout}")

    except FileNotFoundError:
        print_error("uv not found. Please install uv first:")
        print_info("  curl -LsSf https://astral.sh/uv/install.sh | sh")


def main_flow(extra_args: list = None):
    """Main flow: login if needed, then start Claude.

    Args:
        extra_args: Additional CLI arguments to pass through to claude
    """
    config = LocalConfig.load()
    server_manager = ServerManager()

    if not config.is_logged_in():
        # Need to login first (against remote auth server)
        token = do_login(config, with_model_selection=True)
        if not token:
            sys.exit(1)

    # Fetch provider config from auth server (never stored locally)
    print_info("Fetching configuration...")
    provider_config = run_async(fetch_provider_config(AUTH_SERVER_URL, config.token))
    if not provider_config:
        print_error("Failed to get provider configuration. Try logging in again.")
        sys.exit(1)

    # User's local model selection takes precedence over server default
    model = config.get_model() or provider_config.get("model")

    # Override the provider_config model with user's selection for the server
    provider_config["model"] = model

    # Ensure local proxy server is running with provider config
    if not server_manager.is_running():
        print_info("Starting server...")
        port = server_manager.start(provider_config=provider_config)
    else:
        # Server already running - restart to use fresh config
        print_info("Restarting server with fresh config...")
        server_manager.stop()
        port = server_manager.start(provider_config=provider_config)
    print_info(f"Welcome back, {config.email}")
    print_info(f"Model: {model}")
    print_info("Starting Claude...")
    start_claude(config.token, port, model, extra_args)


if __name__ == "__main__":
    entry()
