import sys
from pathlib import Path
import fitz  # PyMuPDF

def render_pdf_pages(pdf_path_str: str, page_range=None, dpi=150):
    pdf_path = Path(pdf_path_str).resolve()
    if not pdf_path.exists():
        print(f"Error: File not found: {pdf_path}")
        return

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    print(f"[PDF Loaded] {pdf_path.name} (Total Pages: {total_pages})")

    out_dir = pdf_path.parent / "pdf_preview"
    out_dir.mkdir(exist_ok=True)

    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)

    if page_range is None:
        pages_to_render = range(total_pages)
    else:
        pages_to_render = [p for p in page_range if 0 <= p < total_pages]

    rendered_files = []
    for page_num in pages_to_render:
        page = doc.load_page(page_num)
        pix = page.get_pixmap(matrix=mat)
        img_name = f"page_{page_num+1:02d}.png"
        img_path = out_dir / img_name
        pix.save(img_path)
        rendered_files.append(img_path)
        print(f"  [Page {page_num+1:02d}/{total_pages}] Saved -> {img_path.name}")

    print(f"\n[Finished] Rendered {len(rendered_files)} pages into: {out_dir}")
    return rendered_files

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python inspect_pdf.py <path_to_pdf> [start_page end_page]")
    else:
        pdf_file = sys.argv[1]
        rng = None
        if len(sys.argv) >= 4:
            s, e = int(sys.argv[2]) - 1, int(sys.argv[3])
            rng = range(s, e)
        render_pdf_pages(pdf_file, rng)
