"""Conservative geometry-to-LaTeX conversion for vector PDF equations.

Uses actual glyph positions and horizontal rules, never a formula dictionary.
Scans without a text layer remain the responsibility of the OCR path.
"""
from dataclasses import dataclass
import re


@dataclass
class Token:
    text: str
    x0: float
    x1: float
    y: float
    size: float
    top: float
    bottom: float
    extensible: bool = False


def _render(tokens, baseline=None):
    if not tokens:
        return ""
    tokens = sorted(tokens, key=lambda t: t.x0)
    if baseline is None:
        largest = max(t.size for t in tokens)
        baseline = max(t.y for t in tokens if t.size >= largest * .9)
    result = ""
    index = 0
    while index < len(tokens):
        token = tokens[index]
        offset = token.y - baseline
        script = "^" if offset < -2 else "_" if offset > 2 else None
        if script:
            end = index + 1
            while end < len(tokens):
                other = tokens[end]
                same = other.y < baseline - 2 if script == "^" else other.y > baseline + 2
                nested = other.size < token.size * .8 and abs(other.y-token.y) < token.size
                if (not same and not nested) or other.x0 - tokens[end-1].x1 > token.size:
                    break
                end += 1
            result += script + "{" + _render(tokens[index:end]) + "}"
            index = end
        else:
            if index and token.x0 - tokens[index-1].x1 > token.size * .12:
                result += " "
            result += token.text
            index += 1
    return result.strip()


def math_page_text(page):
    """Return structured page text only when vector equations are present."""
    tokens = []
    for block in page.get_text("rawdict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                for char in span["chars"]:
                    text = char["c"]
                    if text.isspace():
                        continue
                    # Legacy TeX extensible-parenthesis glyph encoding.
                    text = {"\x12": "(", "\x13": ")"}.get(text, text)
                    box = char["bbox"]
                    tokens.append(Token(text, box[0], box[2], char["origin"][1], span["size"], box[1], box[3], char["c"] in {"\x12", "\x13"}))
    equals = [t for t in tokens if t.text == "="]
    # Avoid changing ordinary prose/pages and tables with occasional '='.
    if len(equals) < 3 or len(equals) > 200 or len(tokens) > 10000:
        return None
    rules = []
    for drawing in page.get_drawings():
        for item in drawing["items"]:
            if item[0] == "l":
                a, b = item[1:3]
                if abs(a.y-b.y) < .3 and abs(a.x-b.x) > 2:
                    rules.append((min(a.x,b.x), max(a.x,b.x), a.y))
    # Prose-heavy pages retain the established text extractor.
    if sum(bool(re.match(r"[А-Яа-яЁё]", t.text)) for t in tokens) > len(tokens) * .35:
        return None
    scripts = any(t.size < e.size * .8 and abs(t.y-e.y) < 10 for e in equals for t in tokens if abs(t.x0-e.x0)<100)
    if not rules and not scripts:
        return None
    # Extensible TeX parentheses have an artificial origin at their top;
    # align these encoded glyphs with the adjacent fraction's baseline.
    for token in tokens:
        if token.extensible or (token.text in {"(", ")"} and token.bottom-token.top > token.size*1.5):
            adjacent = [r for r in rules if abs(r[2]-token.y)<token.size*1.5 and min(abs(token.x0-r[1]),abs(token.x1-r[0]))<token.size]
            if adjacent:
                rule = min(adjacent,key=lambda r:abs(r[2]-token.y))
                token.y = rule[2]+token.size*.26
    # Small/inner fractions first, so nested fractions remain explicit.
    for left, right, y in sorted(rules, key=lambda r:r[1]-r[0]):
        radical = next((t for t in tokens if t.text == "√" and abs(t.x1-left)<2 and abs(t.top-y)<14), None)
        inside = [t for t in tokens if left-1 <= (t.x0+t.x1)/2 <= right+1 and y-23 <= t.y <= y+19]
        if radical:
            body = [t for t in inside if t.y > y]
            indices = [t for t in tokens if radical.x0 <= t.x0 < left and t.size < radical.size*.7 and abs(t.y-y)<12]
            if not body:
                continue
            value = r"\sqrt" + ("["+_render(indices)+"]" if indices else "") + "{"+_render(body)+"}"
            chosen = body + indices + [radical]
            baseline = max(t.y for t in body if t.size >= max(t.size for t in body)*.9)
            node = Token(value, radical.x0, right, baseline, radical.size, min(t.top for t in chosen),max(t.bottom for t in chosen))
        else:
            numerator = [t for t in inside if t.y <= y+1]
            denominator = [t for t in inside if t.y > y+1]
            if not numerator or not denominator:
                continue
            chosen = numerator + denominator
            value = r"\frac{"+_render(numerator)+"}{"+_render(denominator)+"}"
            size = max(t.size for t in chosen)
            node = Token(value,left,right,y+size*.26,size,min(t.top for t in chosen),max(t.bottom for t in chosen))
        tokens = [t for t in tokens if t not in chosen] + [node]
    # Locate equation rows using main '=' baselines. Same-baseline chains stay
    # together; spatially separated columns stay separate.
    anchors = []
    for eq in sorted(equals,key=lambda t:(t.y,t.x0)):
        if not any(abs(eq.y-a.y)<2 and abs(eq.x0-a.x0)<150 for a in anchors):
            anchors.append(eq)
    groups = [[] for _ in anchors]
    leftovers = []
    for token in tokens:
        best = min(range(len(anchors)),key=lambda i: abs(token.y-anchors[i].y)*9 + abs(token.x0-anchors[i].x0))
        anchor = anchors[best]
        if abs(token.y-anchor.y) <= 16 and abs(token.x0-anchor.x0)<230:
            groups[best].append(token)
        else:
            leftovers.append(token)
    lines = []
    for anchor, group in zip(anchors,groups):
        if group:
            lines.append((anchor.y,min(t.x0 for t in group),"$"+_render(group,anchor.y)+"$"))
    # Retain headings and other non-equation text in reading order.
    prose = []
    for token in sorted(leftovers,key=lambda t:(round(t.y/3),t.x0)):
        if not prose or abs(token.y-prose[-1][0].y)>3:
            prose.append([token])
        else:
            prose[-1].append(token)
    for group in prose:
        lines.append((group[0].y,min(t.x0 for t in group),_render(group,group[0].y)))
    return "\n".join(text for _,_,text in sorted(lines))
