import sys
import os
import json
try:
    import fitz
except ImportError:
    print(json.dumps({"error": "PyMuPDF (fitz) is not installed. Run: pip install PyMuPDF"}))
    sys.exit(1)

def audit_layout(pdf_path):
    if not os.path.exists(pdf_path):
        return {"error": f"File not found: {pdf_path}"}

    results = {
        "pdf_path": pdf_path,
        "page_count": 0,
        "issues": [],
        "warnings": []
    }

    try:
        doc = fitz.open(pdf_path)
        results["page_count"] = len(doc)
        
        # A4 standard points: 595.27 x 841.89
        for page_num in range(len(doc)):
            page = doc[page_num]
            rect = page.rect
            width, height = rect.width, rect.height
            
            # Margins (approx 2.5cm)
            margin_x = 70.0
            margin_y = 70.0
            
            # Content area
            content_rect = fitz.Rect(margin_x, margin_y, width - margin_x, height - margin_y)
            
            blocks = page.get_text("dict")["blocks"]
            
            # Calculate coverage (rough estimate based on block bounding boxes)
            covered_area = 0.0
            content_blocks = []
            
            for b in blocks:
                b_rect = fitz.Rect(b["bbox"])
                if b.get("type") == 0:  # text
                    content_blocks.append(b_rect)
                    covered_area += b_rect.get_area()
                elif b.get("type") == 1:  # image
                    content_blocks.append(b_rect)
                    covered_area += b_rect.get_area()
                    
                    # Check for margin bleed
                    if b_rect.x0 < margin_x - 10 or b_rect.x1 > width - margin_x + 10:
                        results["warnings"].append({
                            "page": page_num + 1,
                            "type": "image_margin_bleed",
                            "message": f"Image/Table bleeds into margins (x0: {b_rect.x0:.1f}, x1: {b_rect.x1:.1f})"
                        })
            
            printable_area = content_rect.get_area()
            coverage_ratio = covered_area / printable_area if printable_area > 0 else 0
            
            # Warn if extremely low coverage on a non-last page
            # Usually the last page can have low coverage, and first page is title
            if page_num > 1 and page_num < len(doc) - 1:
                # Calculate Y-span to see if it's just half-empty page
                if content_blocks:
                    min_y = min(b.y0 for b in content_blocks)
                    max_y = max(b.y1 for b in content_blocks)
                    y_span = max_y - min_y
                    y_span_ratio = y_span / content_rect.height
                    
                    if y_span_ratio < 0.5:
                        results["warnings"].append({
                            "page": page_num + 1,
                            "type": "large_empty_space",
                            "message": f"Page appears to have large empty space (Vertical span only {y_span_ratio*100:.1f}% of printable area)."
                        })

    except Exception as e:
        return {"error": f"Failed to process PDF: {str(e)}"}
        
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python audit_pdf_layout.py <pdf_path>"}))
        sys.exit(1)
        
    pdf_path = sys.argv[1]
    res = audit_layout(pdf_path)
    print(json.dumps(res, indent=2, ensure_ascii=False))
