#!/usr/bin/env python3
"""
# md2html: Markdown to Standalone Print-Ready HTML Converter

A zero-dependency, single-file Python script to transform any Markdown document (such as resumes, CVs, profiles, and READMEs) into an executive, print-ready HTML document. The styling and layout match the visual identity of Pedro Amaral's standalone CVs ([CV_Pedro_Amaral_EN_UK.html](file:///Users/pedroamaral/Documents/Profile/CV/CV_Pedro_Amaral_EN_UK.html)).

## Features

- **Zero External Dependencies**: Pure Python 3 standard library (`re`, `html`, `argparse`, `pathlib`). No virtual environment or `pip install` required.
- **Identical Visual Identity**:
  - Color palette: Deep slate text (`#0f172a`), muted subtext (`#334155`), and classic executive accent (`#0f4c81`).
  - Native Apple Typography: System UI font stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto...`) with optimized font weights and line heights.
  - Centered Card Layout: Max-width 820px, subtle shadow and border, responsive on mobile and desktop.
- **Print-Ready Engine**:
  - Embedded `@page { size: A4 portrait; margin: 10mm 14mm; }`.
  - Comprehensive `@media print` rules: pure black ink, zero background waste, page-break avoidance on entries, automatic link cleanup.
- **Intelligent CV/Resume Heuristics**:
  - Automatically parses name and contact bar from `H1` (splits email, phone, GitHub, LinkedIn separated by `•`, `|`, or `⁃`).
  - Formats section banners (`H2`) with uppercase styling and bottom borders.
  - Detects roles, organizations, locations, and dates into `.entry-header`, `.role-title`, and `.date-badge`.
  - Converts bullet points into accented dot lists (`<ul class="bullet-list">`).
  - Auto-detects 2-column `.skills-grid` when bullet items start with `**Category:**`.
- **Markdown Completeness**:
  - Fenced code blocks with language support and clean styling.
  - Inline formatting (bold, italic, strikethrough, inline code, links, images).
  - Pipe tables (`| col1 | col2 |`) with alternating row backgrounds and styled headers.
  - Blockquotes and horizontal rules.
- **CLI & Watch Mode**:
  - Batch convert entire directories.
  - `--watch` flag for real-time live re-compilation upon saving markdown files.

---

## Installation & Requirements

- Python 3.8+ (no additional packages required).
- Place [md2html.py](file:///Users/pedroamaral/Documents/Profile/CV/main/md2html.py) anywhere in your PATH or call it directly with `python3`.

---

## CLI Usage

### Convert a Single File
```bash
python3 /Users/pedroamaral/Documents/Profile/CV/main/md2html.py input.md
# Generates input.html in the same directory
```

### Specify Output Path
```bash
python3 /Users/pedroamaral/Documents/Profile/CV/main/md2html.py input.md -o output.html
```

### Batch Convert a Directory
```bash
python3 /Users/pedroamaral/Documents/Profile/CV/main/md2html.py /path/to/markdown_dir/
# Converts all *.md files to corresponding *.html files
```

### Customize Title and Accent Color
```bash
python3 /Users/pedroamaral/Documents/Profile/CV/main/md2html.py input.md --title "My Custom Title" --accent "#059669"
```

### Raw Markdown Mode (Disable CV Heuristics)
For general documentation or standard README files where you want the exact same visual styling and page layout without resume-specific section parsing:
```bash
python3 /Users/pedroamaral/Documents/Profile/CV/main/md2html.py README.md --raw-markdown -o README.html
```

### Live Watch Mode
Continuously monitors a file and recompiles on save:
```bash
python3 /Users/pedroamaral/Documents/Profile/CV/main/md2html.py CV.md --watch
```

---

## Programmatic Python API

You can also import and use `md2html` directly inside Python scripts:

```python
from pathlib import Path
from md2html import convert_file, parse_markdown_document

# Convert file directly
output_html_path = convert_file(Path("my_cv.md"), Path("my_cv.html"), accent_color="#0f4c81")

# Or convert raw markdown string
markdown_text = "# Pedro Amaral • [GitHub](https://github.com/...)\n\n..."
html_string = parse_markdown_document(markdown_text, page_title="Pedro Amaral")
```

---

## Printing / Exporting to PDF

To generate an A4 PDF from the resulting HTML:
1. Open the `.html` file in Google Chrome, Safari, or Microsoft Edge.
2. Press `Cmd + P` (or `Ctrl + P`).
3. Set **Destination** to `Save as PDF`.
4. Under **More settings**:
   - **Paper size**: `A4`
   - **Margins**: `Default` (the `@page` CSS rule handles margins)
   - **Options**: Uncheck `Headers and footers`, check `Background graphics`.
5. Click **Save**.
"""

from __future__ import annotations

import os
import sys
import re
import html
import argparse
import time
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

DEFAULT_ACCENT = "#0f4c81"

CSS_TEMPLATE = """
    *, *::before, *::after {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    :root {
      --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      --color-bg: #f8fafc;
      --color-page: #ffffff;
      --color-text-main: #0f172a;
      --color-text-muted: #334155;
      --color-text-subtle: #64748b;
      --color-accent: __ACCENT_COLOR__;
      --color-border: #e2e8f0;
      --color-code-bg: #f1f5f9;
      --color-pre-bg: #0f172a;
    }

    body {
      font-family: var(--font-sans);
      background-color: var(--color-bg);
      color: var(--color-text-main);
      line-height: 1.45;
      font-size: 13.5px;
      -webkit-font-smoothing: antialiased;
      padding: 30px 15px;
    }

    .page {
      max-width: 820px;
      margin: 0 auto;
      background: var(--color-page);
      padding: 40px 48px;
      border-radius: 8px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
      border: 1px solid var(--color-border);
    }

    header {
      border-bottom: 2px solid var(--color-text-main);
      padding-bottom: 14px;
      margin-bottom: 18px;
    }

    .header-top {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 4px;
    }

    h1 {
      font-size: 26px;
      font-weight: 800;
      letter-spacing: -0.5px;
      color: var(--color-text-main);
    }

    .contact-bar {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      font-size: 12px;
      color: var(--color-text-muted);
      margin-top: 4px;
      align-items: center;
    }

    .contact-bar a {
      color: var(--color-accent);
      text-decoration: none;
      font-weight: 500;
    }

    .contact-bar a:hover {
      text-decoration: underline;
    }

    section {
      margin-bottom: 16px;
    }

    h2 {
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: var(--color-accent);
      border-bottom: 1px solid var(--color-border);
      padding-bottom: 3px;
      margin-bottom: 8px;
      margin-top: 14px;
    }

    h3 {
      font-size: 13.5px;
      font-weight: 700;
      color: var(--color-text-main);
      margin-top: 10px;
      margin-bottom: 3px;
    }

    h4, h5, h6 {
      font-size: 12.5px;
      font-weight: 600;
      color: var(--color-text-muted);
      margin-top: 8px;
      margin-bottom: 2px;
    }

    p {
      color: var(--color-text-main);
      font-size: 13px;
      line-height: 1.5;
      margin-bottom: 8px;
    }

    .summary-text {
      color: var(--color-text-main);
      font-size: 13px;
      line-height: 1.5;
      text-align: justify;
      margin-bottom: 8px;
    }

    .entry {
      margin-bottom: 10px;
      page-break-inside: avoid;
    }

    .entry:last-child {
      margin-bottom: 0;
    }

    .entry-header {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin-bottom: 1px;
    }

    .role-title {
      font-size: 13.5px;
      font-weight: 700;
      color: var(--color-text-main);
    }

    .organization {
      font-size: 12.5px;
      font-weight: 600;
      color: var(--color-accent);
      margin-bottom: 2px;
    }

    .date-badge {
      font-size: 11.5px;
      font-weight: 600;
      color: var(--color-text-subtle);
      white-space: nowrap;
    }

    ul.bullet-list {
      list-style-type: none;
      padding-left: 0;
      margin-top: 3px;
      margin-bottom: 8px;
    }

    ul.bullet-list li {
      position: relative;
      padding-left: 14px;
      margin-bottom: 2px;
      font-size: 12.5px;
      color: var(--color-text-main);
      line-height: 1.4;
    }

    ul.bullet-list li::before {
      content: "•";
      position: absolute;
      left: 0;
      color: var(--color-accent);
      font-weight: bold;
    }

    ol {
      padding-left: 20px;
      margin-top: 3px;
      margin-bottom: 8px;
      font-size: 12.5px;
      color: var(--color-text-main);
      line-height: 1.4;
    }

    ol li {
      margin-bottom: 3px;
    }

    .skills-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 6px 14px;
      margin-top: 4px;
      margin-bottom: 8px;
    }

    @media (max-width: 600px) {
      .skills-grid {
        grid-template-columns: 1fr;
      }
    }

    .skill-category {
      font-size: 12px;
      line-height: 1.4;
    }

    .skill-category strong {
      color: var(--color-text-main);
      font-weight: 700;
      display: inline-block;
      margin-right: 4px;
    }

    .skill-category span {
      color: var(--color-text-muted);
    }

    .essays-list {
      display: grid;
      grid-template-columns: 1fr;
      gap: 3px;
      font-size: 12px;
      margin-top: 4px;
      margin-bottom: 8px;
    }

    .essay-item {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      color: var(--color-text-main);
    }

    .essay-item a {
      color: var(--color-accent);
      text-decoration: none;
      font-weight: 600;
    }

    .essay-item a:hover {
      text-decoration: underline;
    }

    .essay-meta {
      font-size: 11px;
      color: var(--color-text-subtle);
    }

    a {
      color: var(--color-accent);
      text-decoration: none;
      font-weight: 500;
    }

    a:hover {
      text-decoration: underline;
    }

    hr {
      border: 0;
      border-top: 1px solid var(--color-border);
      margin: 16px 0;
    }

    blockquote {
      border-left: 3px solid var(--color-accent);
      padding: 6px 14px;
      margin: 10px 0;
      color: var(--color-text-muted);
      background: var(--color-code-bg);
      border-radius: 0 4px 4px 0;
      font-style: italic;
    }

    code {
      font-family: var(--font-mono);
      background-color: var(--color-code-bg);
      color: var(--color-text-main);
      padding: 2px 5px;
      border-radius: 4px;
      font-size: 12px;
      border: 1px solid var(--color-border);
    }

    pre {
      background-color: var(--color-pre-bg);
      color: #f8fafc;
      padding: 12px 16px;
      border-radius: 6px;
      overflow-x: auto;
      margin: 12px 0;
      font-size: 12px;
      line-height: 1.5;
    }

    pre code {
      background-color: transparent;
      padding: 0;
      border: none;
      color: inherit;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      margin: 14px 0;
      font-size: 12.5px;
    }

    th, td {
      padding: 8px 12px;
      border: 1px solid var(--color-border);
      text-align: left;
    }

    th {
      background-color: var(--color-code-bg);
      font-weight: 700;
      color: var(--color-text-main);
    }

    tr:nth-child(even) {
      background-color: var(--color-bg);
    }

    img {
      max-width: 100%;
      height: auto;
      border-radius: 6px;
      margin: 8px 0;
    }

    @page {
      size: A4 portrait;
      margin: 10mm 14mm 10mm 14mm;
    }

    @media print {
      body {
        background: transparent !important;
        padding: 0 !important;
        color: #000000 !important;
        font-size: 11pt !important;
      }

      .page {
        max-width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        border: none !important;
        box-shadow: none !important;
      }

      header {
        border-bottom-color: #000000 !important;
        padding-bottom: 8px !important;
        margin-bottom: 10px !important;
      }

      h1 {
        font-size: 19pt !important;
        color: #000000 !important;
      }

      h2, .organization {
        color: #0f365d !important;
      }

      .contact-bar a, .essay-item a, a {
        color: #000000 !important;
        text-decoration: none !important;
      }

      .entry {
        page-break-inside: avoid !important;
        margin-bottom: 8px !important;
      }

      ul.bullet-list li {
        font-size: 9.5pt !important;
        margin-bottom: 2px !important;
      }

      blockquote {
        background: transparent !important;
        border-left-color: #000000 !important;
      }

      pre {
        background-color: #f8fafc !important;
        color: #000000 !important;
        border: 1px solid #cbd5e1 !important;
      }
    }
"""

def render_inline(text: str) -> str:
    """Parse inline markdown elements to HTML."""
    if not text:
        return ""
    
    # Protect code spans first
    code_spans: List[str] = []
    def code_repl(m):
        code_spans.append(m.group(1))
        return f"__CODE_SPAN_{len(code_spans)-1}__"
    
    text = re.sub(r'`([^`]+)`', code_repl, text)
    
    # Images: ![alt](url)
    text = re.sub(r'!\[(.*?)\]\((.*?)\)', r'<img src="\2" alt="\1">', text)
    
    # Links: [text](url)
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    
    # Bold + Italic: ***text*** or ___text___
    text = re.sub(r'\*\*\*(.*?)\*\*\*', r'<strong><em>\1</em></strong>', text)
    text = re.sub(r'___(.*?)___', r'<strong><em>\1</em></strong>', text)
    
    # Bold: **text** or __text__
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__(.*?)__', r'<strong>\1</strong>', text)
    
    # Italic: *text* or _text_
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
    text = re.sub(r'(?<!\w)_([^_]+)_(?!\w)', r'<em>\1</em>', text)
    
    # Strikethrough: ~~text~~
    text = re.sub(r'~~(.*?)~~', r'<del>\1</del>', text)
    
    # Auto-link raw URLs if not already inside an anchor
    def autolink(m):
        url = m.group(0)
        return f'<a href="{url}" target="_blank" rel="noopener">{url}</a>'
    text = re.sub(r'(?<!href=")(https?://[^\s<"]+)', autolink, text)
    
    # Restore code spans
    for i, cs in enumerate(code_spans):
        escaped_cs = html.escape(cs)
        text = text.replace(f"__CODE_SPAN_{i}__", f"<code>{escaped_cs}</code>")
        
    return text


def parse_markdown_document(
    md_text: str,
    raw_mode: bool = False,
    accent_color: str = DEFAULT_ACCENT,
    page_title: Optional[str] = None
) -> str:
    """Convert markdown text into a styled standalone HTML document."""
    lines = md_text.replace("\r\n", "\n").splitlines()
    
    # Strip optional YAML front-matter
    if lines and lines[0].strip() == "---":
        idx = 1
        while idx < len(lines) and lines[idx].strip() != "---":
            idx += 1
        if idx < len(lines) and lines[idx].strip() == "---":
            lines = lines[idx+1:]
            
    doc_title = page_title or "Document"
    header_html = ""
    start_idx = 0
    
    # Locate primary H1 for title and contact bar
    h1_idx = None
    for i, l in enumerate(lines):
        if l.startswith("# "):
            h1_idx = i
            break
            
    if h1_idx is not None and not raw_mode:
        h1_line = lines[h1_idx][2:].strip()
        start_idx = h1_idx + 1
        
        parts = re.split(r'\s+[•⁃|]\s+', h1_line)
        main_name = parts[0].strip()
        contact_items = parts[1:]
        
        # Check next non-empty line for contact information
        next_non_empty = start_idx
        while next_non_empty < len(lines) and not lines[next_non_empty].strip():
            next_non_empty += 1
            
        if next_non_empty < len(lines):
            cand = lines[next_non_empty].strip()
            if (not cand.startswith("#") and not cand.startswith("-") and not cand.startswith("---")
                    and ('@' in cand or 'http' in cand or '|' in cand or '•' in cand)):
                cand_parts = re.split(r'\s+[•⁃|]\s+', cand)
                if len(cand_parts) > 1 or '@' in cand:
                    contact_items.extend(cand_parts)
                    start_idx = next_non_empty + 1
                    
        # Skip trailing whitespace or divider immediately following header
        while start_idx < len(lines) and (not lines[start_idx].strip() or lines[start_idx].strip() == "---"):
            start_idx += 1
            
        doc_title = page_title or main_name
        
        contacts_rendered = []
        for ci in contact_items:
            rendered_ci = render_inline(ci.strip())
            if rendered_ci:
                contacts_rendered.append(f'<span>{rendered_ci}</span>')
                
        contact_bar_html = f'<div class="contact-bar">{"".join(contacts_rendered)}</div>' if contacts_rendered else ""
        header_html = f"""<header>
    <div class="header-top">
      <h1>{render_inline(main_name)}</h1>
    </div>
    {contact_bar_html}
  </header>"""

    body_html_parts: List[str] = []
    current_section: Optional[str] = None
    current_entry: Optional[str] = None
    in_list = False
    is_ordered_list = False
    list_items: List[str] = []
    in_code_block = False
    code_block_lang = ""
    code_block_lines: List[str] = []
    in_table = False
    table_rows: List[List[str]] = []
    
    def flush_list() -> str:
        nonlocal in_list, is_ordered_list, list_items
        if not in_list or not list_items:
            in_list = False
            list_items = []
            return ""
        
        # Check if list matches skills grid: **Category:** description
        skills_pattern = True
        skills_data = []
        for item in list_items:
            m = re.match(r'^\s*<strong>(.*?)</strong>[:\s]*(.*)$', item, re.DOTALL)
            if m:
                skills_data.append((m.group(1).rstrip(':'), m.group(2)))
            else:
                skills_pattern = False
                break
                
        if skills_pattern and len(skills_data) >= 2 and not raw_mode:
            grid_html = ['<div class="skills-grid">']
            for cat, desc in skills_data:
                grid_html.append(f'  <div class="skill-category"><strong>{cat}:</strong><span>{desc.strip()}</span></div>')
            grid_html.append('</div>')
            res = "\n".join(grid_html)
        elif is_ordered_list:
            lis = [f'  <li>{it}</li>' for it in list_items]
            res = '<ol>\n' + "\n".join(lis) + '\n</ol>'
        else:
            lis = [f'  <li>{it}</li>' for it in list_items]
            res = '<ul class="bullet-list">\n' + "\n".join(lis) + '\n</ul>'
            
        in_list = False
        is_ordered_list = False
        list_items = []
        return res

    def flush_table() -> str:
        nonlocal in_table, table_rows
        if not in_table or not table_rows:
            in_table = False
            table_rows = []
            return ""
        
        header_row = table_rows[0]
        data_rows = table_rows[1:]
        
        # Filter out markdown divider row (e.g. |---|---|)
        filtered_data = []
        for r in data_rows:
            if all(re.match(r'^[:\- ]+$', c.strip()) for c in r if c.strip()):
                continue
            filtered_data.append(r)
            
        out = ['<table>', '  <thead>', '    <tr>']
        for c in header_row:
            out.append(f'      <th>{render_inline(c.strip())}</th>')
        out.extend(['    </tr>', '  </thead>', '  <tbody>'])
        for r in filtered_data:
            out.append('    <tr>')
            for c in r:
                out.append(f'      <td>{render_inline(c.strip())}</td>')
            out.append('    </tr>')
        out.extend(['  </tbody>', '</table>'])
        
        in_table = False
        table_rows = []
        return "\n".join(out)

    def close_entry() -> str:
        nonlocal current_entry
        if current_entry:
            current_entry = None
            return '</div><!-- /entry -->'
        return ""

    def close_section() -> str:
        nonlocal current_section
        out = []
        if current_entry:
            out.append(close_entry())
        if current_section:
            out.append('</section>')
            current_section = None
        return "\n".join(out)

    i = start_idx
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Fenced code blocks
        if stripped.startswith("```"):
            if in_table:
                body_html_parts.append(flush_table())
            if in_code_block:
                code_content = html.escape("\n".join(code_block_lines))
                body_html_parts.append(f'<pre><code class="language-{code_block_lang}">{code_content}</code></pre>')
                in_code_block = False
                code_block_lines = []
            else:
                if in_list:
                    body_html_parts.append(flush_list())
                in_code_block = True
                code_block_lang = stripped[3:].strip()
                code_block_lines = []
            i += 1
            continue
            
        if in_code_block:
            code_block_lines.append(line)
            i += 1
            continue
            
        # Markdown table detection
        if stripped.startswith("|") and stripped.endswith("|"):
            if in_list:
                body_html_parts.append(flush_list())
            in_table = True
            cols = [c.strip() for c in stripped.strip("|").split("|")]
            table_rows.append(cols)
            i += 1
            continue
        elif in_table:
            body_html_parts.append(flush_table())
            
        # Empty lines
        if not stripped:
            if in_list:
                body_html_parts.append(flush_list())
            i += 1
            continue
            
        # Horizontal rules
        if re.match(r'^(---|___|\*\*\*)$', stripped):
            if in_list:
                body_html_parts.append(flush_list())
            body_html_parts.append("<hr>")
            i += 1
            continue
            
        # Section Header (H2)
        if stripped.startswith("## ") and not raw_mode:
            # Check if this H2 is an entry header (e.g. "## School (2019-2022)")
            date_in_h2 = re.search(r'\((\d{4}[–\-]\d{4}|\d{4}[–\-]\w+|\d{4})\)', stripped[3:])
            if date_in_h2 and current_section:
                if in_list:
                    body_html_parts.append(flush_list())
                if current_entry:
                    body_html_parts.append(close_entry())
                    
                full_title = stripped[3:].strip()
                date_str = date_in_h2.group(1)
                clean_title = re.sub(r'\s*\(' + re.escape(date_str) + r'\)\s*', '', full_title).strip()
                
                # Check next line for location or subtitle
                org_subtitle = ""
                if (i + 1 < len(lines) and lines[i+1].strip()
                        and not lines[i+1].strip().startswith(("#", "-", "*", ">"))):
                    org_subtitle = lines[i+1].strip().rstrip(".")
                    i += 1
                    
                entry_html = f"""<div class="entry">
  <div class="entry-header">
    <span class="role-title">{render_inline(clean_title)}</span>
    <span class="date-badge">{date_str}</span>
  </div>"""
                if org_subtitle:
                    entry_html += f'\n  <div class="organization">{render_inline(org_subtitle)}</div>'
                body_html_parts.append(entry_html)
                current_entry = clean_title
                i += 1
                continue
            else:
                # Top-level Section Banner
                if in_list:
                    body_html_parts.append(flush_list())
                body_html_parts.append(close_section())
                
                section_title = stripped[3:].strip()
                body_html_parts.append(f'<section>\n  <h2>{render_inline(section_title)}</h2>')
                current_section = section_title
                i += 1
                continue
                
        # H3 Entries in CV mode
        if stripped.startswith("### ") and not raw_mode:
            if in_list:
                body_html_parts.append(flush_list())
            if current_entry:
                body_html_parts.append(close_entry())
                
            h3_text = stripped[4:].strip()
            
            # Match "Org — Role" or "**Org** — Location"
            date_badge = ""
            org_line = ""
            role_line = h3_text
            
            m_org_loc = re.match(r'^(.*?)\s*[—–-]\s*(.+)$', h3_text)
            if m_org_loc:
                left_part = m_org_loc.group(1).strip()
                right_part = m_org_loc.group(2).strip()
            else:
                left_part = h3_text
                right_part = ""
                
            # Peek at subsequent line for date badges and roles
            if i + 1 < len(lines):
                next_l = lines[i+1].strip()
                m_role_date = re.match(r'^\*\*(.*?)\*\*\s*\|\s*\*?(.*?)\*?$', next_l)
                m_date_loc = re.match(r'^\*\*(.*?)\s*[•|]\s*(.*?)\*\*$', next_l)
                m_date_only = re.match(r'^\*\*(\d{4}[–\-].*?)\*\*$', next_l)
                
                if m_role_date:
                    role_line = m_role_date.group(1).strip()
                    date_badge = m_role_date.group(2).strip()
                    org_line = left_part
                    if right_part:
                        org_line += f" — {right_part}"
                    i += 1
                elif m_date_loc:
                    date_badge = m_date_loc.group(1).strip()
                    org_loc = m_date_loc.group(2).strip()
                    org_line = f"{left_part} — {org_loc}" if left_part else org_loc
                    role_line = right_part if right_part else left_part
                    i += 1
                elif m_date_only:
                    date_badge = m_date_only.group(1).strip()
                    org_line = left_part
                    role_line = right_part if right_part else left_part
                    i += 1
                elif right_part:
                    role_line = right_part
                    org_line = left_part
            elif right_part:
                role_line = right_part
                org_line = left_part
                
            if date_badge or org_line:
                entry_html = f"""<div class="entry">
  <div class="entry-header">
    <span class="role-title">{render_inline(role_line)}</span>
    <span class="date-badge">{date_badge}</span>
  </div>"""
                if org_line:
                    entry_html += f'\n  <div class="organization">{render_inline(org_line)}</div>'
                body_html_parts.append(entry_html)
                current_entry = role_line
            else:
                body_html_parts.append(f'<h3>{render_inline(h3_text)}</h3>')
                
            i += 1
            continue
            
        # Generic Headings (h1 to h6)
        m_head = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if m_head:
            if in_list:
                body_html_parts.append(flush_list())
            lvl = len(m_head.group(1))
            htext = render_inline(m_head.group(2).strip())
            body_html_parts.append(f'<h{lvl}>{htext}</h{lvl}>')
            i += 1
            continue
            
        # Unordered Lists
        m_list = re.match(r'^(\*|-|\+)\s+(.+)$', stripped)
        if m_list:
            if in_list and is_ordered_list:
                body_html_parts.append(flush_list())
            in_list = True
            is_ordered_list = False
            list_items.append(render_inline(m_list.group(2).strip()))
            i += 1
            continue
            
        # Ordered Lists
        m_olist = re.match(r'^\d+\.\s+(.+)$', stripped)
        if m_olist:
            if in_list and not is_ordered_list:
                body_html_parts.append(flush_list())
            in_list = True
            is_ordered_list = True
            list_items.append(render_inline(m_olist.group(1).strip()))
            i += 1
            continue
            
        # Blockquotes
        if stripped.startswith("> "):
            if in_list:
                body_html_parts.append(flush_list())
            bq_text = render_inline(stripped[2:].strip())
            body_html_parts.append(f'<blockquote><p>{bq_text}</p></blockquote>')
            i += 1
            continue
            
        # Paragraphs & text lines
        if in_list:
            body_html_parts.append(flush_list())
            
        rendered_p = render_inline(stripped)
        body_html_parts.append(f'<p class="summary-text">{rendered_p}</p>')
        i += 1
        
    if in_list:
        body_html_parts.append(flush_list())
    if in_table:
        body_html_parts.append(flush_table())
    body_html_parts.append(close_section())
    
    css_content = CSS_TEMPLATE.replace("__ACCENT_COLOR__", accent_color)
    content_html = "\n".join([p for p in body_html_parts if p.strip()])
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(doc_title)}</title>
  <style>
{css_content}
  </style>
</head>
<body>

<div class="page">
{header_html}
{content_html}
</div>

</body>
</html>
"""


def convert_file(
    input_path: Path,
    output_path: Optional[Path] = None,
    raw_mode: bool = False,
    accent_color: str = DEFAULT_ACCENT,
    page_title: Optional[str] = None
) -> Path:
    """Convert a single markdown file to an HTML document."""
    input_path = Path(input_path).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
        
    if output_path is None:
        output_path = input_path.with_suffix(".html")
    else:
        output_path = Path(output_path).resolve()
        if output_path.is_dir():
            output_path = output_path / f"{input_path.stem}.html"
            
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    text = input_path.read_text(encoding="utf-8", errors="ignore")
    out_html = parse_markdown_document(
        text,
        raw_mode=raw_mode,
        accent_color=accent_color,
        page_title=page_title or input_path.stem
    )
    
    output_path.write_text(out_html, encoding="utf-8")
    return output_path


def watch_file(input_path: Path, output_path: Optional[Path], **kwargs) -> None:
    """Continuously watch a markdown file and recompile on modification."""
    print(f"Watching {input_path} for changes... (Press Ctrl+C to stop)")
    last_mtime = 0.0
    while True:
        try:
            mtime = os.path.getmtime(input_path)
            if mtime != last_mtime:
                last_mtime = mtime
                out = convert_file(input_path, output_path, **kwargs)
                timestamp = time.strftime("%H:%M:%S")
                print(f"[{timestamp}] Recompiled -> {out}")
            time.sleep(1.0)
        except KeyboardInterrupt:
            print("\nStopped watcher.")
            break
        except Exception as e:
            print(f"Error during compile: {e}")
            time.sleep(1.0)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert Markdown files to standalone, print-ready HTML styled with Pedro Amaral's CV layout."
    )
    parser.add_argument("input", help="Path to markdown file or directory containing markdown files")
    parser.add_argument("-o", "--output", help="Output HTML file path or destination directory")
    parser.add_argument("--title", help="Custom HTML <title> for the document")
    parser.add_argument("--accent", default=DEFAULT_ACCENT, help=f"Primary accent color hex (default: {DEFAULT_ACCENT})")
    parser.add_argument("--raw-markdown", action="store_true", help="Disable CV heuristics and render standard markdown")
    parser.add_argument("--watch", action="store_true", help="Watch input file for changes and recompile automatically")
    
    args = parser.parse_args()
    in_path = Path(args.input).resolve()
    
    if not in_path.exists():
        sys.stderr.write(f"Error: path does not exist: {in_path}\n")
        sys.exit(1)
        
    if args.watch:
        if in_path.is_dir():
            sys.stderr.write("Error: --watch is only supported for single files.\n")
            sys.exit(1)
        watch_file(
            in_path,
            Path(args.output) if args.output else None,
            raw_mode=args.raw_markdown,
            accent_color=args.accent,
            page_title=args.title
        )
        return

    if in_path.is_dir():
        md_files = list(in_path.glob("*.md"))
        if not md_files:
            print(f"No markdown (.md) files found in {in_path}")
            return
        out_dir = Path(args.output).resolve() if args.output else in_path
        print(f"Found {len(md_files)} markdown files in {in_path}. Converting to {out_dir}...")
        for f in sorted(md_files):
            out_file = convert_file(
                f,
                out_dir / f"{f.stem}.html",
                raw_mode=args.raw_markdown,
                accent_color=args.accent,
                page_title=args.title
            )
            print(f"  ✓ {f.name} -> {out_file.name}")
    else:
        out_file = convert_file(
            in_path,
            Path(args.output) if args.output else None,
            raw_mode=args.raw_markdown,
            accent_color=args.accent,
            page_title=args.title
        )
        print(f"✓ Successfully generated: {out_file} ({os.path.getsize(out_file)} bytes)")


if __name__ == "__main__":
    main()
