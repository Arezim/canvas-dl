from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Tuple

from pypdf import PdfMerger

from .utils import ensure_dir


def safe_merge_pdfs(inputs: List[Path], output: Path) -> int:
    if not inputs:
        return 0
    ensure_dir(output.parent)
    merger = PdfMerger()
    appended = 0
    for pdf in inputs:
        try:
            merger.append(str(pdf))
            appended += 1
        except Exception:
            # skip invalid/encrypted
            continue
    if appended == 0:
        return 0
    merger.write(str(output))
    merger.close()
    return appended


def merge_per_module(course_dest: Path, modules: List[dict]) -> List[Path]:
    outputs: List[Path] = []
    for module in sorted(modules, key=lambda m: (m.get("position", 0), m.get("name", ""))):
        module_name = module.get("name") or f"module-{module.get('id')}"
        module_dir = course_dest / module_name
        if not module_dir.exists():
            continue
        pdfs = sorted([p for p in module_dir.glob("*.pdf") if p.is_file()])
        if not pdfs:
            continue
        out = course_dest / f"{module_name}.merged.pdf"
        count = safe_merge_pdfs(pdfs, out)
        if count:
            outputs.append(out)
    return outputs


def merge_course(course_dest: Path, modules: List[dict]) -> Path | None:
    ordered_files: List[Path] = []
    for module in sorted(modules, key=lambda m: (m.get("position", 0), m.get("name", ""))):
        module_name = module.get("name") or f"module-{module.get('id')}"
        module_dir = course_dest / module_name
        if not module_dir.exists():
            continue
        items = module.get("items") or []
        # Gather PDFs in item order
        item_to_files: List[Path] = []
        for item in sorted(items, key=lambda it: (it.get("position", 0), it.get("title", ""))):
            # find a file starting with item title to preserve order
            title = item.get("title") or ""
            candidates = sorted(module_dir.glob("*.pdf"))
            # heuristic: match by start of filename or include
            for f in candidates:
                name = f.name
                if title and (name.startswith(title) or title.lower() in name.lower()):
                    item_to_files.append(f)
        # fallback include all PDFs
        if not item_to_files:
            item_to_files = sorted([p for p in module_dir.glob("*.pdf") if p.is_file()])
        ordered_files.extend(item_to_files)
    if not ordered_files:
        return None
    out = course_dest / "course.merged.pdf"
    count = safe_merge_pdfs(ordered_files, out)
    return out if count else None
