"""Isolated, bounded static renderer. No scripts or external/local resource fetching."""

import base64
import hashlib
import io
import json
import re
import sys
from collections import Counter
from contextlib import redirect_stdout

from .artifacts import parse_html, preview


def render(html, include_pdf=False):
    import pypdfium2 as pdfium
    from weasyprint import CSS, HTML
    from weasyprint.urls import URLFetcher

    clean, _ = preview(html)
    soup = parse_html(clean)
    slides = soup.select(".slide")
    document = bool(soup.select_one("article.stories-document"))
    if len(slides) > 12:
        raise ValueError("Rendered review supports at most 12 slides.")
    # Remove source styles from the expected text, not from the rendered document.
    expected_soup = parse_html(clean)
    for node in expected_soup.select("style,nav,.navigation,.slide-counter,.nav-dots"):
        node.decompose()
    expected = " ".join(expected_soup.body.stripped_strings)
    denied = []

    class NoFetch(URLFetcher):
        def fetch(self, url, headers=None):
            denied.append(str(url).split(":", 1)[0])
            raise ValueError("Resource fetching disabled")

    css = CSS(
        string="""
        @page { size: 1280px 720px; margin: 0; }
        html, body { margin:0!important; padding:0!important; width:1280px!important; }
        .slide { box-sizing:border-box!important;
          width:1280px!important; height:720px!important; min-height:720px!important;
          position:relative!important; opacity:1!important; visibility:visible!important;
          transform:none!important; break-before:page; break-inside:avoid; }
        .slide:first-child { break-before:auto; }
        nav,.navigation,.slide-counter,.nav-dots { display:none!important; }
    """
    )
    doc = HTML(
        string=clean, url_fetcher=NoFetch(allowed_protocols=()), media_type="print" if document else "screen"
    ).render(stylesheets=[] if document else [css])
    if len(doc.pages) > 12:
        raise ValueError("Rendered review exceeds 12 pages; shorten the story.")
    findings, rendered = [], []
    for i, page in enumerate(doc.pages):
        for box in page._page_box.descendants(placeholders=True):
            text = getattr(box, "text", "")
            if not text.strip():
                continue
            rendered.append(text)
            if (
                box.position_x < -1
                or box.position_y < -1
                or box.position_x + box.width > page.width + 1
                or box.position_y + box.height > page.height + 1
            ):
                findings.append(f"Page {i + 1}: text outside the canvas: {text[:80]}")
            if box.style["font_size"] < (12 if document else 16):
                findings.append(f"Page {i + 1}: text below minimum readable size: {text[:80]}")
    if slides and len(doc.pages) != len(slides):
        findings.append(
            f"{len(slides)} slides rendered as {len(doc.pages)} pages; layout spilled or collapsed."
        )
    if denied:
        findings.append("Styles requested blocked external resources; rendering is incomplete.")

    def words(value):
        return Counter(re.findall(r"\w+", value.replace("\u00ad", "").casefold()))

    missing = words(expected) - words(" ".join(rendered))
    if missing:
        findings.append("Text missing from rendered layout: " + ", ".join(list(missing)[:15]))
    pdf_bytes = doc.write_pdf()
    pdf = pdfium.PdfDocument(pdf_bytes)
    images = []
    for page in pdf:
        bitmap = page.render(scale=1)
        output = io.BytesIO()
        bitmap.to_pil().convert("RGB").save(
            output, format="JPEG", quality=40 if document else 45, optimize=True
        )
        png = output.getvalue()
        images.append(
            {
                "sha256": hashlib.sha256(png).hexdigest(),
                "data": base64.b64encode(png).decode(),
                "media_type": "image/jpeg",
            }
        )
        bitmap.close()
        page.close()
    pdf.close()
    return {
        "images": images,
        **({"pdf": base64.b64encode(pdf_bytes).decode()} if include_pdf else {}),
        "renderer": "WeasyPrint Letter document / PDFium"
        if document
        else "WeasyPrint static 1280x720 / PDFium",
        "findings": list(dict.fromkeys(findings))[:30],
        "page_count": len(doc.pages),
        "rendered_text": " ".join(rendered),
        "expected_text": expected,
    }


if __name__ == "__main__":
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_CPU, (35, 35))
        # JSON escaping can expand a valid 2 MB artifact by up to six times.
        value = json.loads(sys.stdin.read(12_100_000))
        with redirect_stdout(io.StringIO()):
            result = render(value["html"], value.get("include_pdf", False))
        print(json.dumps(result))
    except Exception as exc:
        print(json.dumps({"error": f"Static rendering failed ({type(exc).__name__}): {str(exc)[:300]}"}))
        sys.exit(1)
