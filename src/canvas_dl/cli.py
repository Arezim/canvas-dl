from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional

import questionary
import typer
from rich import box
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from . import __version__
from .api import CanvasAPIError, CanvasClient
from .config import AppConfig, DEFAULT_API_URL
from .download import DownloadOptions, download_course_files
from .utils import get_app_dirs, mask_token

app = typer.Typer(add_completion=False)
console = Console()


def _build_client(cfg: AppConfig, api_url: Optional[str], token: Optional[str]) -> CanvasClient:
    base = api_url or cfg.api_url or DEFAULT_API_URL
    tok = token or cfg.access_token
    if not tok:
        raise typer.BadParameter(
            "Missing access token. Run 'canvas-dl auth' or set ACCESS_TOKEN/.env."
        )
    return CanvasClient(base_url=base, access_token=tok)


@app.callback()
def main_callback(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose logging"),
):
    ctx.obj = {"verbose": verbose}


@app.command()
def help():
    """Show detailed help information about canvas-dl."""
    help_text = Text()
    help_text.append("canvas-dl - Canvas Files Downloader CLI for UVA\n\n", style="bold blue")
    
    help_text.append("DESCRIPTION\n", style="bold")
    help_text.append("A user-friendly CLI tool to download files from UVA Canvas courses. ")
    help_text.append("Supports token management, interactive course selection, and robust downloading with filtering options.\n\n")
    
    help_text.append("COMMANDS\n", style="bold")
    help_text.append("• ", style="cyan")
    help_text.append("auth", style="bold")
    help_text.append(" - Configure your Canvas access token\n")
    help_text.append("• ", style="cyan")
    help_text.append("courses", style="bold")
    help_text.append(" - List your Canvas courses\n")
    help_text.append("• ", style="cyan")
    help_text.append("download", style="bold")
    help_text.append(" - Download files from a course\n")
    help_text.append("• ", style="cyan")
    help_text.append("version", style="bold")
    help_text.append(" - Show version information\n")
    help_text.append("• ", style="cyan")
    help_text.append("help", style="bold")
    help_text.append(" - Show this help message\n\n")
    
    help_text.append("EXAMPLES\n", style="bold")
    help_text.append("1. First time setup:\n", style="yellow")
    help_text.append("   canvas-dl auth\n")
    help_text.append("   canvas-dl courses --published\n\n")
    
    help_text.append("2. Download all files from a course:\n", style="yellow")
    help_text.append("   canvas-dl download --course-id 45952\n\n")
    
    help_text.append("3. Interactive course selection:\n", style="yellow")
    help_text.append("   canvas-dl download\n\n")
    
    help_text.append("4. Filter by file types and name:\n", style="yellow")
    help_text.append("   canvas-dl download --course-id 45952 --only pdf,ipynb --name \"*lecture*\"\n\n")
    
    help_text.append("5. Custom destination and concurrency:\n", style="yellow")
    help_text.append("   canvas-dl download --course-id 45952 --dest ~/UVA/Causality --concurrency 4\n\n")
    
    help_text.append("FEATURES\n", style="bold")
    help_text.append("• ", style="green")
    help_text.append("Secure token management with local storage\n")
    help_text.append("• ", style="green")
    help_text.append("Interactive course selection\n")
    help_text.append("• ", style="green")
    help_text.append("File type and name filtering\n")
    help_text.append("• ", style="green")
    help_text.append("Concurrent downloads with rate limiting\n")
    help_text.append("• ", style="green")
    help_text.append("Rich terminal output with progress tracking\n")
    help_text.append("• ", style="green")
    help_text.append("Respects Canvas API rate limits\n\n")
    
    help_text.append("CONFIGURATION\n", style="bold")
    help_text.append("• Default API URL: ", style="yellow")
    help_text.append(f"{DEFAULT_API_URL}\n")
    help_text.append("• Token storage: ", style="yellow")
    help_text.append("Local config file (never logged)\n")
    help_text.append("• Environment variables: ", style="yellow")
    help_text.append("ACCESS_TOKEN, CANVAS_API_URL\n\n")
    
    help_text.append("For more detailed help on specific commands, run:\n", style="dim")
    help_text.append("canvas-dl <command> --help\n", style="cyan")
    
    panel = Panel(help_text, title="canvas-dl Help", border_style="blue")
    console.print(panel)


@app.command()
def version():
    """Show version."""
    console.print(f"canvas-dl {__version__}")


@app.command()
def auth(api_url: str = typer.Option(DEFAULT_API_URL, help="Canvas API base URL")):
    """Prompt for token and save to config file."""
    token = questionary.password("Enter Canvas access token:").ask()
    if not token:
        raise typer.Exit(code=1)
    cfg = AppConfig.from_sources()
    cfg.api_url = api_url
    cfg.access_token = token
    cfg.save()
    console.print(f"Saved token to {AppConfig.config_path()}")


@app.command()
def courses(
    api_url: Optional[str] = typer.Option(None, help="Canvas API base URL override"),
    token: Optional[str] = typer.Option(None, help="Access token override"),
    published: bool = typer.Option(False, help="Only show published courses"),
):
    """List your courses."""
    cfg = AppConfig.from_sources()
    client = _build_client(cfg, api_url, token)

    # Cache: 5 minutes
    dirs = get_app_dirs()
    cache_path = Path(dirs.user_cache_dir) / "courses.json"
    from .utils import TTLCache

    cache = TTLCache(cache_path, ttl_seconds=300)
    data = cache.load()
    if data is None:
        try:
            data = client.list_courses(published=published)
        except CanvasAPIError as e:
            console.print(f"[red]Error listing courses:[/red] {e}")
            raise typer.Exit(code=1)
        cache.save(data)

    table = Table(title="Courses", box=box.SIMPLE_HEAVY)
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Term", style="magenta")
    table.add_column("Published", style="green")

    for c in data:
        table.add_row(str(c.get("id")), c.get("name", ""), (c.get("term") or {}).get("name", ""), str(c.get("workflow_state") == "available"))
    console.print(table)


@app.command()
def download(
    course_id: Optional[int] = typer.Option(None, help="Course ID to download"),
    api_url: Optional[str] = typer.Option(None, help="Canvas API base URL override"),
    token: Optional[str] = typer.Option(None, help="Access token override"),
    dest: Optional[Path] = typer.Option(None, help="Destination directory"),
    only: Optional[str] = typer.Option(None, help="Only download file types, comma-separated (e.g., pdf,ipynb)"),
    name: Optional[str] = typer.Option(None, help="Filter by name (glob)"),
    regex: Optional[str] = typer.Option(None, help="Filter by name (regex)"),
    concurrency: Optional[int] = typer.Option(None, help="Concurrent downloads"),
):
    """Download module files for a course."""
    cfg = AppConfig.from_sources()
    client = _build_client(cfg, api_url, token)

    # Interactive course picker if not provided
    if course_id is None:
        courses = client.list_courses(published=True)
        if not courses:
            console.print("No courses found.")
            raise typer.Exit(code=1)
        choice = questionary.select(
            "Pick a course",
            choices=[questionary.Choice(title=f"{c.get('name')} ({c.get('id')})", value=c) for c in courses],
        ).ask()
        if not choice:
            raise typer.Exit(code=1)
        course_id = int(choice["id"])
        course_name = choice.get("name") or f"course-{course_id}"
    else:
        # Need a name for dest default
        try:
            course = next((c for c in client.list_courses() if int(c.get("id")) == int(course_id)))
            course_name = course.get("name") or f"course-{course_id}"
        except Exception:
            course_name = f"course-{course_id}"

    dest_root = dest or Path("downloads")
    course_dest = dest_root.expanduser().resolve() / sanitize_course_dir(course_name)

    opts = DownloadOptions(
        only_exts=[s.strip() for s in only.split(",")] if only else None,
        name_glob=name,
        name_regex=regex,
        concurrency=concurrency or cfg.concurrency,
    )

    console.print(f"Downloading to: {course_dest}")

    try:
        files, _modules = asyncio.run(
            download_course_files(client, int(course_id), course_name, course_dest, opts)
        )
    except CanvasAPIError as e:
        console.print(f"[red]Error during download:[/red] {e}")
        raise typer.Exit(code=1)

    console.print(f"Downloaded {len(files)} files.")


def sanitize_course_dir(name: str) -> str:
    # reuse file sanitizer but avoid trailing dots and spaces (Windows)
    from .utils import sanitize_filename

    cleaned = sanitize_filename(name)
    return cleaned.rstrip(" .")


def main():  # entry point
    app()
