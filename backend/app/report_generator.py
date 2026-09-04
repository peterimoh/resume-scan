"""Render a saved HR review / ATS check into a formatted PDF.

Reuses the exact Jinja2 -> LaTeX -> pdflatex pipeline already used for
resumes (see resume_generator.py for the `<< >>` / `<% %>` delimiter
convention and the `tex` escape filter). Two things get converted to LaTeX:

- The leading JSON metrics block (see llm.py) is redrawn natively with tikz
  progress bars — not screenshotted — so it stays crisp vector output.
- The markdown report body is converted with a small mistune renderer that
  emits LaTeX instead of HTML (mirrors frontend/src/lib/analysisPayload.ts
  and MarkdownStream.tsx, which is the browser-side equivalent of this).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

import mistune

from .resume_generator import _env, compile_pdf, latex_escape

FENCE_RE = re.compile(r"^\s*```(?:json)?[ \t]*\r?\n([\s\S]*?)\r?\n```[ \t]*\r?\n?")

# Maps the tone names used by AnalysisCharts.tsx to the LaTeX colors defined
# in report.tex.j2.
TONE_COLORS = {
    "success": "rptsuccess",
    "warning": "rptwarning",
    "danger": "rptdanger",
    "accent": "rptaccent",
}

# Cell text is joined with this sentinel (rather than string-searching for a
# trailing " & ") so a literal escaped ampersand at the end of a cell can
# never be mistaken for the column separator. Never reaches the .tex file —
# _join_cells consumes it before the surrounding row/head text is returned.
_CELL_SEP = "\x00"


def _join_cells(text: str) -> str:
    cells = text.split(_CELL_SEP)
    if cells and cells[-1] == "":
        cells.pop()
    return " & ".join(cells) + " \\\\\n"


def parse_analysis_payload(raw: str) -> tuple[dict | None, str]:
    """Split the leading ```json fence (chart metrics) from the markdown
    report that follows it. Mirrors parseAnalysisPayload in
    frontend/src/lib/analysisPayload.ts exactly."""
    if not raw.lstrip().startswith("```"):
        return None, raw
    match = FENCE_RE.match(raw)
    if not match:
        return None, ""
    rest = raw[match.end() :]
    try:
        return json.loads(match.group(1)), rest
    except json.JSONDecodeError:
        return None, rest


def _tone_for_pct(pct: float) -> str:
    if pct >= 70:
        return "success"
    if pct >= 40:
        return "warning"
    return "danger"


def _bar_tex(pct: float, tone: str, track_cm: float = 9.0) -> str:
    pct = max(0.0, min(100.0, pct))
    filled = track_cm * pct / 100
    color = TONE_COLORS[tone]
    return (
        r"\begin{tikzpicture}[baseline=-0.5ex]"
        + rf"\fill[black!12] (0,0) rectangle ({track_cm:.2f},0.28);"
        + rf"\fill[{color}] (0,0) rectangle ({filled:.2f},0.28);"
        + r"\end{tikzpicture}"
    )


def _gauge_tex(pct: float, label: str, sublabel: str | None = None) -> str:
    tone = _tone_for_pct(pct)
    color = TONE_COLORS[tone]
    out = (
        "{\\Huge\\bfseries\\color{" + color + "}" + f"{round(pct)}\\%" + "}\\\\[2pt]\n"
        + "{\\bfseries " + latex_escape(label) + "}"
    )
    if sublabel:
        out += "\\\\{\\small\\color{black!55} " + latex_escape(sublabel) + "}"
    return out + "\n\n"


def _metric_tex(label: str, value_label: str, pct: float, tone: str) -> str:
    return (
        "\\par\\noindent{\\small\\bfseries " + latex_escape(label) + "}\\hfill"
        + "{\\small " + latex_escape(value_label) + "}\\\\[2pt]\n"
        + _bar_tex(pct, tone) + "\\\\[8pt]\n"
    )


def _chips_tex(label: str, items: list[str], tone: str) -> str:
    if not items:
        return ""
    color = TONE_COLORS[tone]
    joined = ", ".join(latex_escape(i) for i in items)
    return (
        "\\par\\noindent{\\small\\bfseries " + latex_escape(label) + ": }"
        + "{\\small{\\color{" + color + "}" + joined + "}}\\par\\vspace{4pt}\n"
    )


def ats_chart_tex(data: dict[str, Any]) -> str:
    must = data.get("must_have") or {}
    nice = data.get("nice_to_have") or {}
    must_matched, must_total = must.get("matched", 0), max(must.get("total", 0), 0)
    nice_matched, nice_total = nice.get("matched", 0), max(nice.get("total", 0), 0)
    must_pct = (must_matched / must_total * 100) if must_total else 0
    nice_pct = (nice_matched / nice_total * 100) if nice_total else 0

    missing = data.get("missing_keywords") or []
    must_missing = [k.get("term", "") for k in missing if k.get("priority") == "must_have"]
    nice_missing = [k.get("term", "") for k in missing if k.get("priority") == "nice_to_have"]

    parts = [
        _gauge_tex(data.get("match_score", 0), "Match score"),
        _metric_tex("Must-have requirements", f"{must_matched} / {must_total}", must_pct, _tone_for_pct(must_pct)),
        _metric_tex("Nice-to-have requirements", f"{nice_matched} / {nice_total}", nice_pct, "accent"),
        _chips_tex("Missing must-have", must_missing, "danger"),
        _chips_tex("Missing nice-to-have", nice_missing, "warning"),
        _chips_tex("Sections present", data.get("sections_present") or [], "success"),
        _chips_tex("Sections missing", data.get("sections_missing") or [], "danger"),
    ]
    return "\n".join(p for p in parts if p)


def hr_chart_tex(data: dict[str, Any]) -> str:
    ach = data.get("achievements") or {}
    quantified, unquantified = ach.get("quantified", 0), ach.get("unquantified", 0)
    total_ach = quantified + unquantified
    ach_pct = (quantified / total_ach * 100) if total_ach else 0
    gap_count = max(
        data.get("standout_count", 0), data.get("weakness_count", 0),
        data.get("missing_requirements_count", 0), 1,
    )
    standout_pct = data.get("standout_count", 0) / gap_count * 100
    weakness_pct = data.get("weakness_count", 0) / gap_count * 100
    missing_pct = data.get("missing_requirements_count", 0) / gap_count * 100

    parts = [
        _gauge_tex(data.get("fit_score", 0), "Fit score", data.get("verdict")),
        _metric_tex("What stands out", str(data.get("standout_count", 0)), standout_pct, "success"),
        _metric_tex("Flaws & weaknesses", str(data.get("weakness_count", 0)), weakness_pct, "warning"),
        _metric_tex("Missing requirements", str(data.get("missing_requirements_count", 0)), missing_pct, "danger"),
    ]
    if total_ach:
        parts.append(_metric_tex("Achievements quantified", f"{quantified} / {total_ach}", ach_pct, "success"))
    flags = data.get("scrutiny_flags", 0)
    if flags:
        parts.append(_chips_tex("HR scrutiny", [f"{flags} flag{'s' if flags != 1 else ''} raised"], "warning"))
    return "\n".join(p for p in parts if p)


class LatexRenderer(mistune.HTMLRenderer):
    """Renders a mistune AST as LaTeX instead of HTML.

    Subclasses HTMLRenderer purely to inherit its render_token, which
    extracts each token's rendered children (or raw text) into a plain
    string before calling the matching method below — see
    mistune/renderers/html.py. Only the output-producing methods are
    overridden; the dispatch machinery itself is untouched.
    """

    NAME = "latex"

    def render_token(self, token: dict, state) -> str:
        if token["type"] == "table":
            # Column count is only available on the raw (pre-render) token
            # tree, so grab it here before the recursive render below turns
            # every cell into a plain string.
            head = token["children"][0]
            self._table_cols = len(head.get("children", []))
        return super().render_token(token, state)

    # --- inline ---

    def text(self, text: str) -> str:
        return latex_escape(text)

    def emphasis(self, text: str) -> str:
        return "\\textit{" + text + "}"

    def strong(self, text: str) -> str:
        return "\\textbf{" + text + "}"

    def codespan(self, text: str) -> str:
        return "\\texttt{" + latex_escape(text) + "}"

    def linebreak(self) -> str:
        return "\\\\\n"

    def softbreak(self) -> str:
        return " "

    def link(self, text: str, url: str, title: str | None = None) -> str:
        return "\\href{" + latex_escape(url) + "}{" + text + "}"

    def image(self, text: str, url: str, title: str | None = None) -> str:
        # No image support in review markdown — degrade to the alt text.
        return text

    def inline_html(self, html: str) -> str:
        return latex_escape(html)

    # --- block ---

    def paragraph(self, text: str) -> str:
        return text + "\n\n"

    def heading(self, text: str, level: int, **attrs: Any) -> str:
        size = "\\Large" if level <= 2 else "\\large"
        return (
            "\\par\\vspace{8pt}{" + size + "\\bfseries\\color{rptaccent} " + text
            + "}\\par\\vspace{4pt}\n"
        )

    def blank_line(self) -> str:
        return ""

    def thematic_break(self) -> str:
        return "\\par\\noindent\\rule{\\linewidth}{0.4pt}\\par\\vspace{6pt}\n"

    def block_text(self, text: str) -> str:
        return text

    def block_code(self, code: str, info: str | None = None) -> str:
        return "\\begin{verbatim}\n" + code + "\\end{verbatim}\n\n"

    def block_quote(self, text: str) -> str:
        return "\\begin{quote}\n" + text + "\\end{quote}\n\n"

    def block_html(self, html: str) -> str:
        return latex_escape(html) + "\n\n"

    def block_error(self, text: str) -> str:
        return latex_escape(text) + "\n\n"

    def list(self, text: str, ordered: bool, **attrs: Any) -> str:
        env = "reportenumerate" if ordered else "reportitemize"
        return "\\begin{" + env + "}\n" + text + "\\end{" + env + "}\n\n"

    def list_item(self, text: str) -> str:
        return "\\item " + text.strip() + "\n"

    # --- tables (GFM pipe tables, via the "table" plugin) ---

    def table(self, text: str) -> str:
        cols = max(getattr(self, "_table_cols", 2), 1)
        col_frac = 0.85 / cols
        colspec = ("p{" + f"{col_frac:.3f}" + "\\linewidth}") * cols
        return "\\begin{longtable}{" + colspec + "}\n" + text + "\\bottomrule\n\\end{longtable}\n\n"

    def table_head(self, text: str) -> str:
        # Unlike table_body's rows, mistune puts head cells directly under
        # table_head with no intermediate table_row wrapper — so this is the
        # only place the header row's cell separators get joined.
        return "\\toprule\n" + _join_cells(text) + "\\midrule\n\\endhead\n"

    def table_body(self, text: str) -> str:
        return text

    def table_row(self, text: str) -> str:
        return _join_cells(text)

    def table_cell(self, text: str, align: str | None = None, head: bool = False) -> str:
        cell = "\\textbf{" + text + "}" if head else text
        return cell + _CELL_SEP


_markdown = mistune.create_markdown(renderer=LatexRenderer(), plugins=["table"])


def markdown_to_latex(text: str) -> str:
    result = _markdown(text)
    return result if isinstance(result, str) else ""


def render_analysis_pdf(
    kind: str, resume_name: str, job_description: str, raw_result: str
) -> bytes:
    """Render a saved HR review or ATS check into PDF bytes."""
    if kind not in ("hr", "ats"):
        raise ValueError(f"PDF export is only supported for 'hr' and 'ats', got {kind!r}.")

    chart, markdown_body = parse_analysis_payload(raw_result)
    body_tex = markdown_to_latex(markdown_body)
    chart_tex = ""
    if chart:
        chart_tex = ats_chart_tex(chart) if kind == "ats" else hr_chart_tex(chart)

    title = "ATS Check" if kind == "ats" else "HR Review"
    generated = datetime.now(timezone.utc).strftime("%B %d, %Y")
    jd_snippet = " ".join(job_description.split())
    if len(jd_snippet) > 220:
        jd_snippet = jd_snippet[:220].rstrip() + "\u2026"
    meta_line = (
        f"Generated {generated} \\textbullet\\ Target role: "
        + latex_escape(jd_snippet or "(no job description provided)")
    )

    tex = _env().get_template("report.tex.j2").render(
        title=title,
        subtitle=resume_name,
        meta_line=meta_line,
        chart_tex=chart_tex,
        body_tex=body_tex,
    )
    return compile_pdf(tex, jobname="report")
