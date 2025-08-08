from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from platformdirs import PlatformDirs

TOKEN_MASK = "***TOKEN***"


def mask_token(text: str | None) -> str:
    if not text:
        return ""
    if len(text) <= 8:
        return TOKEN_MASK
    return text[:4] + "…" + text[-4:]


def sanitize_filename(name: str, max_length: int = 150) -> str:
    # Remove control characters and forbidden path separators
    name = re.sub(r"[\x00-\x1f\x7f]", "", name)
    name = name.replace("/", "-").replace("\\", "-")
    # Collapse whitespace
    name = re.sub(r"\s+", " ", name).strip()
    # Limit length but keep extension
    if len(name) > max_length:
        if "." in name:
            base, ext = name.rsplit(".", 1)
            keep = max_length - len(ext) - 1
            name = base[:keep] + "." + ext
        else:
            name = name[:max_length]
    return name


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def get_app_dirs() -> PlatformDirs:
    return PlatformDirs(appname="canvas-dl", appauthor=False)


@dataclass
class TTLCache:
    path: Path
    ttl_seconds: int

    def load(self) -> Optional[dict]:
        if not self.path.exists():
            return None
        try:
            data = self.path.read_text(encoding="utf-8")
            import json

            obj = json.loads(data)
            ts = obj.get("_ts", 0)
            if time.time() - ts > self.ttl_seconds:
                return None
            return obj.get("data")
        except Exception:
            return None

    def save(self, data: dict) -> None:
        ensure_dir(self.path.parent)
        import json

        payload = {"_ts": time.time(), "data": data}
        self.path.write_text(json.dumps(payload), encoding="utf-8")


LinkMap = Dict[str, str]


def parse_link_header(link_header: str | None) -> LinkMap:
    # RFC 5988 style: <url>; rel="next", <url>; rel="last"
    links: LinkMap = {}
    if not link_header:
        return links
    for part in link_header.split(","):
        part = part.strip()
        if not part:
            continue
        if part.startswith("<") and ">" in part:
            url = part[1 : part.index(">")]
            m = re.search(r"rel=\"([^\"]+)\"", part)
            if m:
                rel = m.group(1)
                links[rel] = url
    return links


def is_ci() -> bool:
    return any(
        key in ("CI", "GITHUB_ACTIONS", "BUILD_NUMBER") for key in sys.environ.keys()
    )
