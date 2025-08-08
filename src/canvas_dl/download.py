from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import httpx
from rich.progress import Progress, BarColumn, TimeRemainingColumn, DownloadColumn, TransferSpeedColumn, TextColumn

from .api import CanvasClient
from .utils import ensure_dir, sanitize_filename


@dataclass
class DownloadOptions:
    only_exts: Optional[List[str]] = None
    name_glob: Optional[str] = None
    name_regex: Optional[str] = None
    concurrency: int = 3


def should_include(filename: str, opts: DownloadOptions) -> bool:
    lower = filename.lower()
    if opts.only_exts:
        matched_ext = any(lower.endswith(f".{ext.lower()}") for ext in opts.only_exts)
        if not matched_ext:
            return False
    if opts.name_glob and not fnmatch(filename, opts.name_glob):
        return False
    if opts.name_regex and not re.search(opts.name_regex, filename):
        return False
    return True


def load_state(path: Path) -> Dict[str, Dict[str, str]]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(path: Path, state: Dict[str, Dict[str, str]]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


async def _download_one(client: httpx.AsyncClient, url: str, dest: Path, expected_size: Optional[int] = None, progress: Optional[Progress] = None) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    async with client.stream("GET", url) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("Content-Length", 0)) or expected_size or None
        task_id = None
        if progress is not None:
            task_id = progress.add_task("download", filename=dest.name, total=total)
        with tmp.open("wb") as f:
            async for chunk in resp.aiter_bytes(chunk_size=1024 * 128):
                f.write(chunk)
                if progress is not None and task_id is not None:
                    progress.update(task_id, advance=len(chunk))
    tmp.replace(dest)


async def download_course_files(
    api: CanvasClient,
    course_id: int,
    course_name: str,
    dest_dir: Path,
    opts: DownloadOptions,
) -> Tuple[List[Path], List[dict]]:
    modules = api.list_modules(course_id)
    ensure_dir(dest_dir)

    state_path = dest_dir / ".state.json"
    state = load_state(state_path)

    files_to_get: List[Tuple[str, Path, Optional[int], dict]] = []
    for module in modules:
        module_name = sanitize_filename(module.get("name") or f"module-{module.get('id')}")
        items = module.get("items") or []
        for item in items:
            if item.get("type") != "File":
                continue
            file_info = api.get_file_info(int(item["content_id"]))
            display_name = sanitize_filename(file_info.get("display_name") or str(file_info.get("id")))
            if not should_include(display_name, opts):
                continue
            url = file_info.get("url")
            size = file_info.get("size")
            updated_at = file_info.get("updated_at")
            module_dir = dest_dir / module_name
            ensure_dir(module_dir)
            dest = module_dir / display_name

            # Skip if unchanged
            st = state.get(str(file_info.get("id")))
            if st and st.get("updated_at") == updated_at and dest.exists():
                continue

            files_to_get.append((url, dest, size, {"id": file_info.get("id"), "updated_at": updated_at, "module": module}))

    downloaded_paths: List[Path] = []

    limits = httpx.Limits(max_keepalive_connections=opts.concurrency, max_connections=opts.concurrency)
    async with httpx.AsyncClient(timeout=60.0, limits=limits, follow_redirects=True) as client:
        progress = Progress(
            TextColumn("{task.fields[filename]}", justify="left"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            transient=True,
            refresh_per_second=5,
        )
        with progress:
            sem = asyncio.Semaphore(opts.concurrency)

            async def worker(u: str, d: Path, sz: Optional[int], meta: dict) -> None:
                async with sem:
                    await _download_one(client, u, d, expected_size=sz, progress=progress)
                    downloaded_paths.append(d)
                    state[str(meta["id"])] = {"updated_at": meta.get("updated_at", ""), "path": str(d)}

            tasks = [worker(u, d, sz, meta) for (u, d, sz, meta) in files_to_get]
            if tasks:
                await asyncio.gather(*tasks)

    save_state(state_path, state)
    return downloaded_paths, modules
