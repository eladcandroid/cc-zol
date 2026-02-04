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


def start_claude(token: str, port: int, model: str) -> None:
    """Start Claude Code with the proxy environment variables."""
    env = os.environ.copy()
    env["ANTHROPIC_AUTH_TOKEN"] = token
    env["ANTHROPIC_BASE_URL"] = f"http://localhost:{port}"
    env["MODEL"] = model

    # Replace current process with claude
    try:
        os.execvpe("claude", ["claude"], env)
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
        # Default behavior: login if needed, then start Claude
        main_flow()


@cli.command()
def login():
    """Force re-login with a new email."""
    config = LocalConfig.load()
    server_manager = ServerManager()

    # Perform login with model selection (against remote auth server)
    token = do_login(config, with_model_selection=True)
    if token:
        # Ensure local proxy server is running
        if not server_manager.is_running():
            print_info("Starting server...")
            port = server_manager.start()
        else:
            port = server_manager.get_port()

        print_info("Starting Claude...")
        start_claude(token, port, config.get_model())


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


def main_flow():
    """Main flow: login if needed, then start Claude."""
    config = LocalConfig.load()
    server_manager = ServerManager()

    if not config.is_logged_in():
        # Need to login first (against remote auth server)
        token = do_login(config, with_model_selection=True)
        if not token:
            sys.exit(1)

    # Ensure local proxy server is running
    if not server_manager.is_running():
        print_info("Starting server...")
        port = server_manager.start()
    else:
        port = server_manager.get_port()

    print_info(f"Welcome back, {config.email}")
    print_info(f"Model: {config.get_model()}")
    print_info("Starting Claude...")
    start_claude(config.token, port, config.get_model())


if __name__ == "__main__":
    cli()
