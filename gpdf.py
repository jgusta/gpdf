#!/usr/bin/env python3
import argparse
import html
import os
import re
import sys
from datetime import datetime
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

try:
    import fitz  # PyMuPDF
except Exception as exc:
    print("ERROR: PyMuPDF is required. Install with: pip install -r requirements.txt", file=sys.stderr)
    raise


@dataclass
class MatchRecord:
    source_path: str
    title: str
    page_number: int
    page_count: int
    percent: float
    context: str


def _normalize_context(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _normalize_with_ansi(text: str) -> str:
    sentinel_start = "\x00GPDF_START\x00"
    sentinel_end = "\x00GPDF_END\x00"
    text = text.replace("\x1b[31m", sentinel_start).replace("\x1b[0m", sentinel_end)
    text = _normalize_context(text)
    return text.replace(sentinel_start, "\x1b[31m").replace(sentinel_end, "\x1b[0m")

def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)

def _ansi_to_bold_html(text: str) -> str:
    sentinel_start = "__GPDF_BOLD_START__"
    sentinel_end = "__GPDF_BOLD_END__"
    text = text.replace("\x1b[31m", sentinel_start).replace("\x1b[0m", sentinel_end)
    escaped = html.escape(text)
    return escaped.replace(sentinel_start, "<strong>").replace(sentinel_end, "</strong>")


def _extract_context(text: str, start: int, end: int, window: int) -> str:
    left = max(0, start - window)
    right = min(len(text), end + window)
    snippet = text[left:right]
    local_start = start - left
    local_end = end - left
    colored = (
        snippet[:local_start]
        + "\x1b[31m"
        + snippet[local_start:local_end]
        + "\x1b[0m"
        + snippet[local_end:]
    )
    return _normalize_with_ansi(colored)


def _default_pdf_paths(cwd: str) -> List[str]:
    return [
        os.path.join(cwd, name)
        for name in os.listdir(cwd)
        if name.lower().endswith(".pdf") and os.path.isfile(os.path.join(cwd, name))
    ]


def _collect_paths(args_paths: List[str]) -> List[str]:
    if not args_paths:
        return _default_pdf_paths(os.getcwd())

    collected: List[str] = []
    for path in args_paths:
        if os.path.isdir(path):
            for name in os.listdir(path):
                full = os.path.join(path, name)
                if name.lower().endswith(".pdf") and os.path.isfile(full):
                    collected.append(full)
        else:
            collected.append(path)
    return collected


def _pdf_title(doc: "fitz.Document", fallback: str) -> str:
    try:
        title = doc.metadata.get("title") or ""
    except Exception:
        title = ""
    title = title.strip()
    return title if title else fallback


def _scan_pdf(
    path: str,
    pattern: re.Pattern,
    context: int,
) -> Tuple[List[MatchRecord], List[int]]:
    matches: List[MatchRecord] = []
    matched_pages: List[int] = []

    try:
        doc = fitz.open(path)
    except Exception as exc:
        print(f"ERROR: failed to open {path}: {exc}", file=sys.stderr)
        return matches, matched_pages

    title = _pdf_title(doc, os.path.basename(path))
    page_count = doc.page_count

    for page_index in range(page_count):
        page = doc.load_page(page_index)
        text = page.get_text("text") or ""
        if not text:
            continue
        page_has_match = False
        for match in pattern.finditer(text):
            page_has_match = True
            snippet = _extract_context(text, match.start(), match.end(), context)
            percent = ((page_index + 1) / page_count) * 100.0 if page_count else 0.0
            matches.append(
                MatchRecord(
                    source_path=path,
                    title=title,
                    page_number=page_index + 1,
                    page_count=page_count,
                    percent=percent,
                    context=snippet,
                )
            )
        if page_has_match:
            matched_pages.append(page_index)

    doc.close()
    return matches, matched_pages


def _write_html_index(
    output_path: str,
    records: List[MatchRecord],
    pattern_text: str,
    link_prefix: str,
    summary_link_prefix: Optional[str],
    summary_filename: Optional[str],
    summary_pages: Optional[dict],
    report_title: str,
    back_href: Optional[str],
) -> None:
    rows = []
    for rec in records:
        file_name = os.path.basename(rec.source_path)
        clean_context = _ansi_to_bold_html(rec.context)
        summary_page = None
        if summary_pages:
            summary_page = summary_pages.get((rec.source_path, rec.page_number))
        links = [f"<a href=\"{html.escape(link_prefix + file_name)}\">source</a>"]
        if summary_page and summary_filename and summary_link_prefix is not None:
            summary_href = f"{summary_link_prefix}{summary_filename}#page={summary_page}"
            links.append(f"<a href=\"{html.escape(summary_href)}\">summary</a>")
        rows.append(
            "<tr>"
            f"<td>{html.escape(file_name)}</td>"
            f"<td>{rec.page_number}</td>"
            f"<td class=\"context\">{clean_context}</td>"
            f"<td>" + "<br>".join(links) + "</td>"
            "</tr>"
        )

    meta_tag = f'<meta name="gpdf-pattern" content="{html.escape(pattern_text)}" />'
    html_doc = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
""" + meta_tag + """
<title>gpdf results</title>
<style>
body {
  margin: 0;
  background: #f5f1ea;
  color: #2a2a2a;
  font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Palatino, serif;
}
.wrap {
  max-width: 1100px;
  margin: 32px auto 48px;
  padding: 0 24px;
}
.header {
  background: #fffaf2;
  border: 1px solid #e6dccb;
  border-radius: 14px;
  padding: 18px 20px;
  box-shadow: 0 6px 16px rgba(80, 64, 32, 0.08);
}
.header-top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
}
.back-link {
  font-size: 12px;
  color: #2b5c7d;
}
.title {
  font-size: 24px;
  margin: 0 0 6px 0;
}
.subtitle {
  font-size: 12px;
  color: #7a6a52;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.pattern {
  font-size: 14px;
  color: #5a4a35;
}
.pattern code {
  font-family: "Menlo", "Consolas", "Liberation Mono", monospace;
  background: #f0e6d6;
  padding: 2px 6px;
  border-radius: 6px;
}
table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  background: #fff;
  border: 1px solid #e1d7c5;
  border-radius: 14px;
  overflow: hidden;
  margin-top: 18px;
  box-shadow: 0 8px 20px rgba(80, 64, 32, 0.08);
}
th, td {
  padding: 10px 12px;
  vertical-align: top;
  border-bottom: 1px solid #eee3d4;
}
th {
  background: #efe6d7;
  text-align: left;
  letter-spacing: 0.04em;
  font-size: 12px;
  text-transform: uppercase;
  color: #5a4a35;
}
tr:hover td {
  background: #fff6e8;
}
.context {
  font-family: "Menlo", "Consolas", "Liberation Mono", monospace;
  font-size: 13px;
}
a {
  color: #2b5c7d;
  text-decoration: none;
}
a:hover {
  text-decoration: underline;
}
</style>
</head>
<body>
<div class="wrap">
<div class="header">
  <div class="header-top">
    <div class="title">""" + html.escape(report_title) + """</div>
    """ + (f"<a class=\"back-link\" href=\"{html.escape(back_href)}\">&larr; Back</a>" if back_href else "") + """
  </div>
  <div class="subtitle">created by gpdf</div>
  <div class="pattern">Pattern: <code>""" + html.escape(pattern_text) + """</code></div>
</div>
<table>
<thead>
<tr>
<th>File</th>
<th>Page</th>
<th>Context</th>
<th>Links</th>
</tr>
</thead>
<tbody>
""" + "\n".join(rows) + """
</tbody>
</table>
</div>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(html_doc)


def _build_reports_index(output_dir: str, report_title: str) -> None:
    entries = []
    html_dir = os.path.join(output_dir, "html")
    if os.path.isdir(html_dir):
        scan_dir = html_dir
        link_prefix = "html/"
    else:
        scan_dir = output_dir
        link_prefix = ""
    for name in sorted(os.listdir(scan_dir)):
        if not name.lower().endswith(".html"):
            continue
        if name == "index.html":
            continue
        path = os.path.join(scan_dir, name)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                content = handle.read(4096)
        except Exception:
            continue
        match = re.search(r'<meta name="gpdf-pattern" content="([^"]*)"\s*/?>', content, re.IGNORECASE)
        pattern_text = html.unescape(match.group(1)) if match else "unknown pattern"
        entries.append((name, pattern_text))

    rows = []
    for name, pattern_text in entries:
        rows.append(
            f"<tr><td>{html.escape(pattern_text)}</td>"
            f"<td><a href=\"{html.escape(link_prefix + name)}\">{html.escape(name)}</a></td></tr>"
        )

    index_html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>gpdf reports</title>
<style>
body {
  margin: 0;
  background: #f5f1ea;
  color: #2a2a2a;
  font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Palatino, serif;
}
.wrap {
  max-width: 1100px;
  margin: 32px auto 48px;
  padding: 0 24px;
}
.header {
  background: #fffaf2;
  border: 1px solid #e6dccb;
  border-radius: 14px;
  padding: 18px 20px;
  box-shadow: 0 6px 16px rgba(80, 64, 32, 0.08);
}
.title {
  font-size: 24px;
  margin: 0 0 6px 0;
}
.subtitle {
  font-size: 12px;
  color: #7a6a52;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  background: #fff;
  border: 1px solid #e1d7c5;
  border-radius: 14px;
  overflow: hidden;
  margin-top: 18px;
  box-shadow: 0 8px 20px rgba(80, 64, 32, 0.08);
}
th, td {
  padding: 10px 12px;
  vertical-align: top;
  border-bottom: 1px solid #eee3d4;
}
th {
  background: #efe6d7;
  text-align: left;
  letter-spacing: 0.04em;
  font-size: 12px;
  text-transform: uppercase;
  color: #5a4a35;
}
tr:hover td {
  background: #fff6e8;
}
a {
  color: #2b5c7d;
  text-decoration: none;
}
a:hover {
  text-decoration: underline;
}
</style>
</head>
<body>
<div class="wrap">
<div class="header">
  <div class="title">""" + html.escape(report_title) + """</div>
  <div class="subtitle">created by gpdf</div>
</div>
<table>
<thead>
<tr><th>Pattern</th><th>Report</th></tr>
</thead>
<tbody>
""" + "\n".join(rows) + """
</tbody>
</table>
</div>
</body>
</html>
"""

    with open(os.path.join(output_dir, "index.html"), "w", encoding="utf-8") as handle:
        handle.write(index_html)


def _safe_filename(path: str) -> str:
    return os.path.basename(path)


def _copy_pdfs(output_dir: str, sources: Iterable[str]) -> None:
    for src in sources:
        dst = os.path.join(output_dir, _safe_filename(src))
        if os.path.abspath(src) == os.path.abspath(dst):
            continue
        with open(src, "rb") as r, open(dst, "wb") as w:
            w.write(r.read())


def _next_available_output(base_dir: str, ext: str) -> str:
    date_stamp = datetime.now().strftime("%Y-%m-%d")
    for i in range(1, 1000):
        name = f"gpdf-{date_stamp}-{i:03d}.{ext}"
        path = os.path.join(base_dir, name)
        if not os.path.exists(path):
            return path
    raise RuntimeError("could not determine an available output filename")


def _resolve_output_path(requested: Optional[str], output_dir: Optional[str], ext: str) -> Optional[str]:
    if requested is None:
        return None
    base_dir = output_dir or os.getcwd()
    if requested == "":
        return _next_available_output(base_dir, ext)
    if output_dir:
        return os.path.join(output_dir, os.path.basename(requested))
    return requested


def _build_merged_pdf(
    output_path: str,
    records: List[MatchRecord],
    matched_pages_by_file: dict,
) -> dict:
    merged = fitz.open()
    toc = []
    entries = []
    page_map = {}

    for src_path, page_indexes in matched_pages_by_file.items():
        if not page_indexes:
            continue
        try:
            src_doc = fitz.open(src_path)
        except Exception as exc:
            print(f"ERROR: failed to open {src_path}: {exc}", file=sys.stderr)
            continue

        title = _pdf_title(src_doc, os.path.basename(src_path))
        for page_index in page_indexes:
            merged_page_number = merged.page_count + 1
            merged.insert_pdf(src_doc, from_page=page_index, to_page=page_index)

            display = f"{title} - page {page_index + 1}"
            toc.append([1, display, merged_page_number])
            entries.append(
                {
                    "title": title,
                    "source_path": src_path,
                    "source_page": page_index + 1,
                    "merged_page_index": merged_page_number - 1,
                }
            )
            page_map[(src_path, page_index + 1)] = merged_page_number

            page = merged.load_page(merged_page_number - 1)
            link_rect = fitz.Rect(36, 24, 550, 40)
            label = f"Source: {os.path.basename(src_path)} page {page_index + 1}"
            page.insert_text((36, 36), label, fontsize=9)
            uri = f"file://{os.path.abspath(src_path)}#page={page_index + 1}"
            page.insert_link({
                "kind": fitz.LINK_URI,
                "from": link_rect,
                "uri": uri,
            })

        src_doc.close()

    if merged.page_count:
        if entries:
            toc_page = merged.new_page(pno=0)
            toc_page.insert_text((36, 36), "Contents", fontsize=16)
            y = 60
            line_height = 14
            for entry in entries:
                display = f"{entry['title']} - page {entry['source_page']}"
                toc_page.insert_text((36, y), display, fontsize=10)
                toc_page.insert_text((420, y), "page", fontsize=10)
                toc_page.insert_text((470, y), "source", fontsize=10)

                internal_rect = fitz.Rect(420, y - 2, 455, y + 10)
                external_rect = fitz.Rect(470, y - 2, 540, y + 10)
                target_index = entry["merged_page_index"] + 1
                toc_page.insert_link(
                    {
                        "kind": fitz.LINK_GOTO,
                        "from": internal_rect,
                        "page": target_index,
                    }
                )
                source_uri = (
                    f"file://{os.path.abspath(entry['source_path'])}"
                    f"#page={entry['source_page']}"
                )
                toc_page.insert_link(
                    {
                        "kind": fitz.LINK_URI,
                        "from": external_rect,
                        "uri": source_uri,
                    }
                )
                y += line_height

            toc = [
                [level, title, page + 1]
                for level, title, page in toc
            ]

        if toc:
            merged.set_toc(toc)
        merged.save(output_path)
    merged.close()
    return page_map


def main() -> int:
    parser = argparse.ArgumentParser(description="grep-like search for PDFs", add_help=False)
    parser.add_argument("--help", action="help", help="show this help message and exit")
    parser.add_argument("pattern", help="regex pattern (case-insensitive)")
    parser.add_argument("paths", nargs="*", help="pdf files or directories")
    parser.add_argument("-c", "--context", type=int, default=120, help="context window size")
    parser.add_argument(
        "-h",
        "--html",
        action="store_true",
        help="write html index with auto name",
    )
    parser.add_argument(
        "-m",
        "--merge",
        action="store_true",
        help="write merged pdf with auto name",
    )
    parser.add_argument("--html-path", help="write html index to path")
    parser.add_argument("--merge-path", help="write merged pdf to path")
    parser.add_argument("--name", help="title for the HTML report")
    parser.add_argument(
        "--report",
        action="store_true",
        help="create a gpdf_report bundle with html/source/summaries",
    )
    parser.add_argument(
        "--output-dir",
        help="directory for html/merged outputs and optional copies",
    )
    parser.add_argument(
        "--copy-pdfs",
        action="store_true",
        help="copy matched source pdfs into output directory",
    )

    args = parser.parse_args()

    try:
        pattern = re.compile(args.pattern, re.IGNORECASE)
    except re.error as exc:
        print(f"ERROR: invalid regex: {exc}", file=sys.stderr)
        return 2

    paths = _collect_paths(args.paths)
    if not paths:
        print("No PDF files found.", file=sys.stderr)
        return 1

    report_mode = args.report
    html_requested = args.html or args.html_path
    merge_requested = args.merge or args.merge_path

    if report_mode:
        output_dir = "gpdf_report"
        html_dir = os.path.join(output_dir, "html")
        source_dir = os.path.join(output_dir, "source")
        summaries_dir = os.path.join(output_dir, "summaries")

        html_requested = args.html_path if args.html_path else ""
        merge_requested = args.merge_path if args.merge_path else ""
        args.html_path = _resolve_output_path(html_requested, html_dir, "html")
        args.merge_path = _resolve_output_path(merge_requested, summaries_dir, "pdf")
        args.copy_pdfs = True
        link_prefix = "../source/"
        summary_link_prefix = "../summaries/"
        back_href = "../index.html"
        default_title = os.path.basename(os.path.dirname(os.path.abspath(output_dir)))
    else:
        output_dir = args.output_dir or ("_gpdf_results" if (html_requested or merge_requested) else None)
        html_requested = args.html_path if args.html_path else ("" if args.html else None)
        merge_requested = args.merge_path if args.merge_path else ("" if args.merge else None)
        args.html_path = _resolve_output_path(html_requested, output_dir, "html")
        args.merge_path = _resolve_output_path(merge_requested, output_dir, "pdf")
        link_prefix = ""
        summary_link_prefix = ""
        back_href = None
        default_title = "gpdf results"

    output_paths = {
        os.path.abspath(path)
        for path in [args.html_path, args.merge_path]
        if path
    }
    if output_paths:
        paths = [
            path for path in paths if os.path.abspath(path) not in output_paths
        ]

    all_records: List[MatchRecord] = []
    matched_pages_by_file = {}

    for path in paths:
        if not os.path.exists(path):
            print(f"WARN: missing {path}", file=sys.stderr)
            continue
        if os.path.isfile(path) and not path.lower().endswith(".pdf"):
            print(f"WARN: skipping non-pdf {path}", file=sys.stderr)
            continue

        records, matched_pages = _scan_pdf(path, pattern, args.context)
        all_records.extend(records)
        matched_pages_by_file[path] = sorted(set(matched_pages))

        for record in records:
            file_name = os.path.basename(record.source_path)
            if record.page_count:
                location = f"page {record.page_number}"
            else:
                location = f"{record.percent:.1f}%"
            print(f"{file_name}:{location}: {record.context}")

    if all_records:
        if report_mode:
            os.makedirs(html_dir, exist_ok=True)
            os.makedirs(source_dir, exist_ok=True)
            os.makedirs(summaries_dir, exist_ok=True)
        elif output_dir:
            os.makedirs(output_dir, exist_ok=True)

        summary_pages = {}
        if args.merge_path:
            summary_pages = _build_merged_pdf(args.merge_path, all_records, matched_pages_by_file)
            print(f"Merged PDF written to {args.merge_path}")

        if args.html_path:
            summary_name = os.path.basename(args.merge_path) if args.merge_path else None
            _write_html_index(
                args.html_path,
                all_records,
                args.pattern,
                link_prefix,
                summary_link_prefix if args.merge_path else None,
                summary_name,
                summary_pages,
                args.name or default_title,
                back_href,
            )
            print(f"HTML index written to {args.html_path}")
            if output_dir:
                _build_reports_index(output_dir, args.name or default_title)

        if output_dir and args.copy_pdfs:
            sources = [path for path, pages in matched_pages_by_file.items() if pages]
            if report_mode:
                _copy_pdfs(source_dir, sources)
            else:
                _copy_pdfs(output_dir, sources)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
