"""Static HTML preview with stable, revision-local element and text anchors."""

import hashlib

from bs4 import BeautifulSoup

from .documents import safe_link
from .errors import StoriesError, require

MAX_HTML = 32 * 1024 * 1024


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def parse_html(html):
    require(
        isinstance(html, str) and bool(html),
        "Supply nonempty HTML markup.",
    )
    size = len(html.encode())
    if size > MAX_HTML:
        raise StoriesError(
            "markup_resource_limit",
            f"Markup is {size} UTF-8 bytes, exceeding the {MAX_HTML}-byte (32 MiB) parsing budget.",
            "Retain the complete structured source and use a workflow with sufficient byte capacity. "
            "Import embedded media separately where applicable. Do not truncate, merge or rewrite "
            "storyboard panels to fit a count quota; this is a byte limit, not a panel-count limit.",
        )
    soup = BeautifulSoup(html, "html.parser")
    require(soup.html is not None and soup.body is not None, "HTML must contain html and body elements.")
    require(bool(soup.body.get_text(strip=True)), "HTML has no visible text content.")
    return soup


def preview(html, assets=None):
    soup = parse_html(html)
    # Source scripts never run in the review origin. Original bytes remain available for export.
    for node in soup.select("script,iframe,object,embed,base,link,meta,form,input,textarea,button,svg,math"):
        node.decompose()
    allowed = {"asset:" + a["id"] for a in (assets or [])}
    for node in list(soup.find_all(True)):
        source = {key: node.get(key) for key in ("src", "poster")}
        href = node.get("href")
        node.attrs.pop("data-stories-link", None)
        for key in list(node.attrs):
            if key.startswith("on") or key in {
                "srcdoc",
                "formaction",
                "action",
                "href",
                "src",
                "srcset",
                "poster",
                "background",
            }:
                del node.attrs[key]
        node.attrs.pop("contenteditable", None)
        if node.name == "a" and safe_link(href):
            node["data-stories-link"] = href
            node["role"] = "link"
            node["tabindex"] = "0"
        if node.name in {"img", "video", "source", "track"}:
            for key, value in source.items():
                if value in allowed:
                    node[key] = value
            if source["src"] and not node.get("src"):
                warning = soup.new_tag("span")
                warning.string = "[Media unavailable: import and attach this asset.]"
                node.insert_after(warning)
        if node.name == "video":
            node["controls"] = ""
            node["preload"] = "metadata"
            node.attrs.pop("autoplay", None)
    anchors = []
    blocks = soup.body.select("h1,h2,h3,h4,p,li,td,th,blockquote,figcaption,article,section,div,span,table")
    structured = soup.select_one("article.stories-document")
    used = set()
    for i, node in enumerate(blocks):
        if not node.get_text(strip=True):
            continue
        key = "d-" + node["id"] if structured and node.get("id") else f"e{i}"
        if key in used:
            key = f"e{i}"
        used.add(key)
        node["data-stories-id"] = key
        anchors.append({"element": key, "text": node.get_text(), "tag": node.name})
    return str(soup), anchors


def validate_anchor(html, anchor, assets=None):
    require(isinstance(anchor, dict), "Anchor must be an object.")
    require(set(anchor) <= {"kind", "element", "start", "end", "quote"}, "Unknown anchor fields.")
    kind = anchor.get("kind")
    require(kind in {"story", "element", "text"}, "Anchor kind must be story, element, or text.")
    if kind == "story":
        require(set(anchor) == {"kind"}, "Whole-story anchors contain only kind.")
        return {"kind": "story"}
    _, elements = preview(html, assets)
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
    for fact in evidence:
        source = next(s for s in sources if s["id"] == fact["source_id"])
        fact["source_kind"] = source.get("kind", "source")
        fact["attribution"] = source.get("attribution", "")
    return evidence


def source_excerpts(sources):
    """Identify exact supplied paragraphs so models select references rather than retype quotes."""
    import re

    catalog, index = [], {}
    for number, source in enumerate(sources):
        excerpts = []
        for match in re.finditer(r"\S[\s\S]*?(?=\n\s*\n|$)", source["content"]):
            text = match.group()
            for start in range(0, len(text), 2000):
                key = f"s{number}-p{len(excerpts)}"
                quote = text[start : start + 2000]
                excerpts.append({"excerpt_id": key, "text": quote})
                index[key] = {"source_id": source["id"], "quote": quote}
        catalog.append(
            {
                "id": source["id"],
                "name": source["name"],
                "kind": source.get("kind", "source"),
                "attribution": source.get("attribution", ""),
                "excerpts": excerpts,
            }
        )
    return catalog, index


def selected_evidence(selections, index, sources):
    require(
        isinstance(selections, list) and len(selections) <= 12,
        "Select at most 12 evidence references.",
        "invalid_model_result",
    )
    evidence = []
    for item in selections:
        require(
            isinstance(item, dict) and item.get("excerpt_id") in index,
            "Evidence selected an unavailable excerpt.",
            "invalid_model_result",
        )
        evidence.append({"id": item.get("id"), "claim": item.get("claim"), **index[item["excerpt_id"]]})
    return evidence_checked(evidence, sources)


def revision_evidence(base, extracted):
    """Retain existing citation identities when a revision selects excerpts in a new order."""
    import copy

    result = copy.deepcopy(base or [])
    used = {fact["id"] for fact in result}
    keys = {(fact["source_id"], fact["quote"]) for fact in result}
    for fact in extracted:
        key = (fact["source_id"], fact["quote"])
        if key in keys:
            continue
        fact = copy.deepcopy(fact)
        number = 1
        while f"fact{number}" in used:
            number += 1
        fact["id"] = f"fact{number}"
        result.append(fact)
        used.add(fact["id"])
        keys.add(key)
    return result
