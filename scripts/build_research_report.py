"""Render the canonical Markdown research report to a styled HTML/PDF artifact."""

from __future__ import annotations

import html
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "submission" / "research" / "report-source.md"
OUTPUT_DIR = SOURCE.parent
HTML_OUTPUT = OUTPUT_DIR / "CrossSignal-Competitive-Research-and-Enhancement-Report.html"
PDF_OUTPUT = OUTPUT_DIR / "CrossSignal-Competitive-Research-and-Enhancement-Report.pdf"


def inline(text: str) -> str:
    """Escape source text and render the small inline Markdown subset used here."""
    value = html.escape(text.strip())
    value = re.sub(r"\[([^]]+)]\(([^)]+)\)", r'<a href="\2">\1</a>', value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", value)
    value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
    return value


def render_markdown(source: str) -> str:
    lines = source.splitlines()
    body: list[str] = []
    index = 0
    in_list = False
    first_heading = True
    while index < len(lines):
        line = lines[index]
        if line.startswith("|") and line.endswith("|"):
            if in_list:
                body.append("</ul>")
                in_list = False
            table_lines = []
            while index < len(lines) and lines[index].startswith("|"):
                table_lines.append(lines[index])
                index += 1
            rows = [row for row in table_lines if not re.fullmatch(r"[| :\-]+", row)]
            body.append("<table>")
            for row_number, row in enumerate(rows):
                tag = "th" if row_number == 0 else "td"
                body.append("<tr>" + "".join(
                    f"<{tag}>{inline(cell)}</{tag}>" for cell in row.strip("|").split("|")
                ) + "</tr>")
            body.append("</table>")
            continue
        if line.startswith("- "):
            if not in_list:
                body.append("<ul>")
                in_list = True
            body.append(f"<li>{inline(line[2:])}</li>")
            index += 1
            continue
        if in_list:
            body.append("</ul>")
            in_list = False
        if not line.strip():
            index += 1
            continue
        if line.startswith("# "):
            css_class = ' class="report-title"' if first_heading else ""
            body.append(f"<h1{css_class}>{inline(line[2:])}</h1>")
            first_heading = False
        elif line.startswith("## "):
            body.append(f"<h2>{inline(line[3:])}</h2>")
        elif line.startswith("### "):
            body.append(f"<h3>{inline(line[4:])}</h3>")
        else:
            body.append(f"<p>{inline(line)}</p>")
        index += 1
    if in_list:
        body.append("</ul>")
    return "\n".join(body)


def main() -> None:
    content = render_markdown(SOURCE.read_text(encoding="utf-8"))
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>CrossSignal Competitive Research</title>
<style>
@page {{ size: Letter; margin: 0.65in 0.68in 0.68in; }}
* {{ box-sizing: border-box; }}
body {{ color:#172238; font:10pt/1.43 'Segoe UI',Arial,sans-serif; margin:0; }}
body::before {{ content:''; position:fixed; top:-0.65in; left:-0.68in; right:-0.68in;
height:0.16in; background:#d79a32; }}
h1,h2,h3 {{ color:#102747; font-family:'Segoe UI Semibold','Segoe UI',sans-serif;
page-break-after:avoid; }}
.report-title {{ font-size:27pt; line-height:1.08; margin:0 0 18pt; padding-top:8pt;
border-bottom:3px solid #d79a32; padding-bottom:14pt; }}
h2 {{ font-size:16pt; margin:19pt 0 7pt; border-bottom:1px solid #ccd5e2; padding-bottom:3pt; }}
h3 {{ font-size:11.5pt; margin:13pt 0 4pt; color:#24517b; }}
p {{ margin:0 0 7pt; orphans:3; widows:3; }}
strong {{ color:#102747; }}
code {{ background:#edf2f7; border-radius:3px; padding:1px 3px; font-size:9pt; }}
a {{ color:#145d91; text-decoration:none; }}
ul {{ margin:3pt 0 9pt 18pt; padding:0; }} li {{ margin:0 0 3pt; }}
table {{ width:100%; border-collapse:collapse; margin:8pt 0 12pt; font-size:7.4pt;
page-break-inside:auto; }}
tr {{ page-break-inside:avoid; }}
th {{ color:white; background:#173a62; text-align:left; padding:5px 6px; }}
td {{ border:1px solid #cbd5e1; vertical-align:top; padding:5px 6px; }}
tr:nth-child(even) td {{ background:#f3f6f9; }}
h2:first-of-type + p {{ border-left:4px solid #d79a32; background:#f7f4ec; padding:9pt 11pt; }}
</style></head><body>{content}</body></html>"""
    HTML_OUTPUT.write_text(document, encoding="utf-8")

    edge_candidates = (
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    )
    edge = next((path for path in edge_candidates if path.exists()), None)
    if edge is None:
        raise FileNotFoundError("Microsoft Edge is required for PDF rendering")
    subprocess.run([
        str(edge), "--headless", "--disable-gpu", "--no-pdf-header-footer",
        f"--print-to-pdf={PDF_OUTPUT}", HTML_OUTPUT.as_uri(),
    ], check=True)
    print(HTML_OUTPUT)
    print(PDF_OUTPUT)


if __name__ == "__main__":
    main()
