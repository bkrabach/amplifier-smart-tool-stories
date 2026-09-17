"""Static HTML preview with stable, revision-local element and text anchors."""

import hashlib

from bs4 import BeautifulSoup

from .errors import require

MAX_HTML = 2_000_000


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def parse_html(html):
    require(isinstance(html, str) and 0 < len(html.encode()) <= MAX_HTML, "Supply nonempty HTML under 2 MB.")
    soup = BeautifulSoup(html, "html.parser")
    require(soup.html is not None and soup.body is not None, "HTML must contain html and body elements.")
    require(bool(soup.body.get_text(strip=True)), "HTML has no visible text content.")
    return soup


def preview(html):
    soup = parse_html(html)
    # Source scripts never run in the review origin. Original bytes remain available for export.
    for node in soup.select("script,iframe,object,embed,base,link,meta,form,input,textarea,button,svg,math"):
        node.decompose()
    for node in soup.find_all(True):
        for key in list(node.attrs):
            if key.startswith("on") or key in {"srcdoc", "formaction", "action", "href", "src", "srcset"}:
                del node.attrs[key]
        # Prevent a supplied stylesheet from masquerading as overlay controls outside its iframe.
        node.attrs.pop("contenteditable", None)
    anchors = []
    blocks = soup.body.select("h1,h2,h3,h4,p,li,td,th,blockquote,figcaption,article,section,div,span")
    for i, node in enumerate(blocks):
        if not node.get_text(strip=True):
            continue
        key = f"e{i}"
        node["data-stories-id"] = key
        anchors.append({"element": key, "text": node.get_text(), "tag": node.name})
    return str(soup), anchors


def validate_anchor(html, anchor):
    require(isinstance(anchor, dict), "Anchor must be an object.")
    require(set(anchor) <= {"kind", "element", "start", "end", "quote"}, "Unknown anchor fields.")
    kind = anchor.get("kind")
    require(kind in {"story", "element", "text"}, "Anchor kind must be story, element, or text.")
    if kind == "story":
        require(set(anchor) == {"kind"}, "Whole-story anchors contain only kind.")
        return {"kind": "story"}
    _, elements = preview(html)
    targets = {e["element"]: e for e in elements}
    require(anchor.get("element") in targets, "Anchor element does not exist in this revision.")
    text = targets[anchor["element"]]["text"]
    if kind == "text":
        start, end = anchor.get("start"), anchor.get("end")
        require(
            type(start) is int and type(end) is int and 0 <= start < end <= len(text), "Invalid text range."
        )
        require(anchor.get("quote") == text[start:end], "Selected quote does not match this revision.")
        return {
            "kind": kind,
            "element": anchor["element"],
            "start": start,
            "end": end,
            "quote": text[start:end],
        }
    return {"kind": kind, "element": anchor["element"], "quote": text[:500]}


def evidence_checked(evidence, sources):
    require(isinstance(evidence, list), "Evidence must be a list.")
    index = {s["id"]: s["content"] for s in sources}
    seen = set()
    for fact in evidence:
        require(isinstance(fact, dict), "Evidence entries must be objects.")
        require(isinstance(fact.get("id"), str) and fact["id"] not in seen, "Evidence IDs must be unique.")
        seen.add(fact["id"])
        require(fact.get("source_id") in index, "Evidence refers to an unavailable source.")
        require(
            isinstance(fact.get("quote"), str)
            and fact["quote"]
            and fact["quote"] in index[fact["source_id"]],
            "Evidence quote must occur verbatim in its source.",
        )
        require(isinstance(fact.get("claim"), str) and fact["claim"], "Evidence needs a claim.")
    return evidence
