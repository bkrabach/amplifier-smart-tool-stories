"""Editable semantic slide layout; does not attempt to translate arbitrary CSS."""

import textwrap

from bs4 import NavigableString, Tag
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_AUTO_SIZE
from pptx.util import Inches, Pt

from ..errors import require

WIDTH, HEIGHT = 13.333333, 7.5


def blocks(node):
    """Preserve document order and block boundaries, including anonymous text."""
    inline = []

    def flush():
        value = " ".join(" ".join(inline).split())
        inline.clear()
        return [("text", value)] if value else []

    for child in node.children:
        if isinstance(child, NavigableString):
            inline.append(str(child))
        elif isinstance(child, Tag):
            if child.name in {"style", "script", "nav"}:
                continue
            if child.name == "table":
                yield from flush()
                yield "table", child
            elif child.name in {"h1", "h2", "h3", "h4", "p", "li", "blockquote", "pre"}:
                yield from flush()
                value = child.get_text(" ", strip=True)
                if value:
                    yield child.name, value
            elif child.name in {"div", "section", "article", "header", "footer", "ul", "ol", "main"}:
                yield from flush()
                yield from blocks(child)
            else:
                inline.append(child.get_text(" ", strip=True))
    yield from flush()


def wrapped(text, width, size):
    # Conservative width reservation; explicit breaks avoid PowerPoint autoshrink.
    chars = max(8, int(width * 72 / (size * 0.58)))
    return "\n".join(textwrap.wrap(text, chars, break_long_words=True, break_on_hyphens=False))


def write_frame(frame, text, size, color, bold=False):
    frame.clear()
    frame.word_wrap = False
    frame.auto_size = MSO_AUTO_SIZE.NONE
    frame.margin_left = frame.margin_right = 0
    frame.margin_top = frame.margin_bottom = 0
    for i, line in enumerate(text.split("\n")):
        p = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
        p.text = line
        p.font.name = "Arial"
        p.font.size = Pt(size)
        p.font.bold = bold
        p.font.color.rgb = RGBColor.from_string(color)
        p.space_before = p.space_after = Pt(0)
        p.line_spacing = Pt(size * 1.2)


def convert_slides(source_slides):
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(WIDTH), Inches(HEIGHT)
    for index, source in enumerate(source_slides, 1):
        items = list(blocks(source))
        require(bool(items), f"Slide {index} is empty.", "conversion_failed")
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = RGBColor.from_string("101820")
        # Select a single readable type scale for the whole slide. Never silently
        # omit text or rely on application-specific fit-to-shape behavior.
        chosen = None
        for body_size in (22, 20, 18, 16):
            layout, top = [], 0.45
            for pos, (kind, value) in enumerate(items):
                if kind == "table":
                    rows = [
                        [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"], recursive=False)]
                        for row in value.find_all("tr")
                    ]
                    require(rows and all(rows), f"Slide {index}: empty table.", "unsupported_content")
                    columns = len(rows[0])
                    require(
                        columns <= 6
                        and all(len(r) == columns for r in rows)
                        and not value.select("[rowspan],[colspan]"),
                        "PowerPoint tables require a rectangular grid without merged cells, at most 6 columns.",
                        "unsupported_content",
                    )
                    cell_width = (WIDTH - 1.2) / columns
                    rows = [[wrapped(c, cell_width - 0.2, body_size) for c in row] for row in rows]
                    heights = [
                        max(c.count("\n") + 1 for c in row) * body_size * 1.2 / 72 + 0.16 for row in rows
                    ]
                    height = sum(heights)
                    layout.append((kind, (rows, heights), top, height, body_size, False))
                else:
                    title = pos == 0 and kind in {"h1", "h2"}
                    size = 30 if title else body_size + 2 if kind in {"h1", "h2", "h3", "h4"} else body_size
                    text = ("• " if kind == "li" else "") + value
                    text = wrapped(text, WIDTH - 1.2, size)
                    height = (text.count("\n") + 1) * size * 1.2 / 72 + 0.04
                    layout.append((kind, text, top, height, size, title or kind.startswith("h")))
                top += height + 0.09
            if top <= HEIGHT - 0.35:
                chosen = layout
                break
        require(
            chosen is not None,
            f"Slide {index}: too much content for readable PowerPoint; split the slide.",
            "conversion_failed",
        )
        for kind, content, top, height, size, bold in chosen:
            if kind == "table":
                rows, heights = content
                table = slide.shapes.add_table(
                    len(rows), len(rows[0]), Inches(0.6), Inches(top), Inches(WIDTH - 1.2), Inches(height)
                ).table
                for i, row in enumerate(rows):
                    table.rows[i].height = Inches(heights[i])
                    for j, text in enumerate(row):
                        cell = table.cell(i, j)
                        cell.margin_left = cell.margin_right = Inches(0.1)
                        cell.margin_top = cell.margin_bottom = Inches(0.08)
                        cell.fill.solid()
                        cell.fill.fore_color.rgb = RGBColor.from_string("233342" if i == 0 else "152330")
                        write_frame(cell.text_frame, text, size, "FFFFFF", i == 0)
            else:
                shape = slide.shapes.add_textbox(
                    Inches(0.6), Inches(top), Inches(WIDTH - 1.2), Inches(height)
                )
                write_frame(shape.text_frame, content, size, "FFFFFF" if bold else "E2E8F0", bold)
    return prs
