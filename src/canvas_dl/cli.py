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

from . import __version__
from .api import CanvasAPIError, CanvasClient
from .config import AppConfig, DEFAULT_API_URL
from .download import DownloadOptions, download_course_files
from .merge import merge_course, merge_per_module
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
    no_merge: bool = typer.Option(False, "--no-merge", help="Skip PDF merging"),
    merge_scope: str = typer.Option("both", help="PDF merge scope: per-module|course|both"),
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
        files, modules = asyncio.run(
            download_course_files(client, int(course_id), course_name, course_dest, opts)
        )
    except CanvasAPIError as e:
        console.print(f"[red]Error during download:[/red] {e}")
        raise typer.Exit(code=1)

    pdf_outputs = []
    if not no_merge:
        scope = merge_scope.lower()
        if scope in ("per-module", "both"):
            pdf_outputs.extend(merge_per_module(course_dest, modules))
        if scope in ("course", "both"):
            c = merge_course(course_dest, modules)
            if c:
                pdf_outputs.append(c)

    console.print(f"Downloaded {len(files)} files.")
    if pdf_outputs:
        console.print(f"Merged PDFs: {len(pdf_outputs)}")


def sanitize_course_dir(name: str) -> str:
    # reuse file sanitizer but avoid trailing dots and spaces (Windows)
    from .utils import sanitize_filename

    cleaned = sanitize_filename(name)
    return cleaned.rstrip(" .")


def main():  # entry point
    app()
