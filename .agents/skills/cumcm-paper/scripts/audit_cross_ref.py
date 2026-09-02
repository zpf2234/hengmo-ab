import sys
import os
import json
try:
    import fitz
except ImportError:
    print(json.dumps({"error": "PyMuPDF (fitz) is not installed."}))
    sys.exit(1)

def audit_cross_references(pdf_path, max_allowed_drift=1):
    if not os.path.exists(pdf_path):
        return {"error": f"File not found: {pdf_path}"}

    results = {
        "pdf_path": pdf_path,
        "warnings": [],
        "issues": []
    }

    try:
        doc = fitz.open(pdf_path)
        
        # We will scan all internal links
        for page_num in range(len(doc)):
            page = doc[page_num]
            links = page.get_links()
            
            for link in links:
                if link["kind"] == fitz.LINK_GOTO:
                    dest_page = link.get("page")
                    if dest_page is not None:
                        drift = dest_page - page_num
                        # If a reference is pointing to a figure/table many pages away
                        if abs(drift) > max_allowed_drift:
                            # Try to extract the text around the link to give better context
                            rect = link["from"]
                            # Expand rect slightly to capture the word (e.g. "Figure 3")
                            expanded_rect = fitz.Rect(rect.x0 - 50, rect.y0 - 10, rect.x1 + 50, rect.y1 + 10)
                            words = page.get_textbox(expanded_rect).replace('\n', ' ').strip()
                            
                            # Filter out links that are likely Table of Contents (usually on first few pages)
                            if page_num < 3:
                                continue
                                
                            results["warnings"].append({
                                "source_page": page_num + 1,
                                "dest_page": dest_page + 1,
                                "drift": abs(drift),
                                "context": words,
                                "message": f"Reference on page {page_num + 1} points to an object on page {dest_page + 1} (Drift: {abs(drift)} pages)."
                            })

    except Exception as e:
        return {"error": f"Failed to process PDF for cross references: {str(e)}"}
        
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python audit_cross_ref.py <pdf_path>"}))
        sys.exit(1)
        
    pdf_path = sys.argv[1]
    res = audit_cross_references(pdf_path)
    print(json.dumps(res, indent=2, ensure_ascii=False))
