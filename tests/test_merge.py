from pathlib import Path

from pypdf import PdfWriter

from canvas_dl.merge import safe_merge_pdfs


def _make_pdf(path: Path, pages: int = 1) -> None:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=72)
    with path.open("wb") as f:
        writer.write(f)


def test_safe_merge_pdfs(tmp_path: Path):
    a = tmp_path / "a.pdf"
    b = tmp_path / "b.pdf"
    out = tmp_path / "out.pdf"
    _make_pdf(a)
    _make_pdf(b)

    count = safe_merge_pdfs([a, b], out)
    assert count == 2
    assert out.exists()
