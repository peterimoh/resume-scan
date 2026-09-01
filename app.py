#!/usr/bin/env python3
"""Streamlit UI for editing resumes and generating ATS-friendly PDFs.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import shutil
import time
from pathlib import Path

import streamlit as st

import db
import llm
from resume_generator import (
    DEFAULT_FONT,
    DEFAULT_SECTION_LABELS,
    FONTS,
    TEMPLATES,
    compile_pdf,
    installed_fonts,
    pdf_to_png,
    pdf_to_pngs,
    pdf_to_text,
    render_tex,
)

BASE_DIR = Path(__file__).resolve().parent
JSON_PATH = BASE_DIR / "resume.json"

st.set_page_config(page_title="Resume Builder", page_icon="\U0001f4c4", layout="wide")

# Lock the app to the viewport height and make the two top-level columns
# (form builder / live preview) scroll independently instead of scrolling
# the whole page. Applied only in the Editor view; the Library view scrolls
# normally.
_LOCK_CSS = """
<style>
html, body { height: 100%; overflow: hidden; }

section[data-testid="stMain"] { overflow: hidden !important; }

section[data-testid="stSidebar"] { width: 360px !important; }

.block-container {
    max-width: 1400px;
    height: 100vh;
    height: 100dvh;
    padding: 4.75rem 1.5rem 1rem 1.5rem !important;
    display: flex;
    flex-direction: column;
    overflow: hidden !important;
}

/* Root vertical block fills the container without scrolling. */
.block-container > [data-testid="stVerticalBlock"] {
    flex: 1 1 auto;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

/* The columns row is wrapped in a layout wrapper — constrain it too. */
.block-container > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] {
    flex: 1 1 auto;
    min-height: 0;
    overflow: hidden;
}

/* The top-level row (editor | preview) fills the remaining height. */
.block-container > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] {
    flex: 1 1 auto;
    min-height: 0;
    height: 100%;
    overflow: hidden;
}

/* Each top-level column scrolls independently. */
.block-container > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    height: 100%;
    min-height: 0;
    overflow-y: auto;
}

/* Floating preview toggle button pinned to the bottom-right. */
section[data-testid="stMain"] div[data-testid="stButton"]:has(button[kind="primary"]) {
    position: fixed !important;
    bottom: 1.5rem;
    right: 1.5rem;
    z-index: 999;
    width: 48px !important;
    height: 48px !important;
}
section[data-testid="stMain"] button[kind="primary"] {
    width: 48px !important;
    height: 48px !important;
    min-height: 0 !important;
    padding: 0 !important;
    border-radius: 50% !important;
    font-size: 1.3rem !important;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35);
}
</style>
"""

_SIDEBAR_CSS = """
<style>
section[data-testid="stSidebar"] { width: 360px !important; }
</style>
"""

_LOGIN_CSS = """
<style>
.block-container {
    max-width: 600px;
    width: 100%;
    margin: 0 auto;
    padding-top: 4rem !important;
}
</style>
"""


def load_data() -> dict:
    if JSON_PATH.exists():
        return json.loads(JSON_PATH.read_text(encoding="utf-8"))
    return {}


def _blank_data() -> dict:
    """A complete, empty resume schema with no values."""
    return {
        "title": "",
        "name": "",
        "headline": "",
        "contact": {
            "location": "",
            "email": "",
            "phone": "",
            "github": "",
            "linkedin": "",
        },
        "profile": "",
        "skills": [],
        "experience": [],
        "impact": [],
        "leadership": [],
        "education": [],
        "certifications": [],
        "capabilities": [],
        "career_progression": "",
        "professional_profile": "",
        "technology_index": [],
        "references": "",
        "section_labels": {},
        "sections": {},
    }


def _resume_title(data: dict) -> str:
    """Label for a resume: the explicit title, else the person's name."""
    title = (data.get("title") or "").strip()
    if title:
        return title
    return (data.get("name") or "").strip() or "Untitled Resume"


@st.cache_data(show_spinner=False)
def live_pages(template: str, font: str, serialized_data: str) -> list:
    """Compile the resume and return PNG bytes for every page (for live preview)."""
    data = json.loads(serialized_data)
    tex = render_tex(data, template, font)
    pdf = compile_pdf(tex, jobname=f"preview_{template}")
    return pdf_to_pngs(pdf)


@st.cache_data(show_spinner=False)
def thumbnail(pdf_bytes: bytes) -> bytes:
    """Return a small first-page PNG for library previews."""
    return pdf_to_png(pdf_bytes, dpi=60)


def list_editor(title: str, items: list, layout: list, key: str) -> list:
    """Edit a list of dicts with add/remove controls.

    `layout` is a list of rows; each row is a list of field names that share
    a horizontal grid. A single-element row is full width.
    """
    st.subheader(title)

    edited = []
    for idx, item in enumerate(items):
        with st.container(border=True):
            head = st.columns([0.9, 0.1])
            head[0].markdown(f"**Entry {idx + 1}**")
            remove = head[1].checkbox(
                "✕", key=f"{key}_rm_{idx}", label_visibility="collapsed",
                help="Remove this entry",
            )

            row = {}
            for fields in layout:
                cols = st.columns(len(fields))
                for f, col in zip(fields, cols):
                    default = item.get(f, "")
                    if f == "highlights":
                        text = col.text_area(
                            f"{f} (one per line)",
                            value="\n".join(item.get(f, [])),
                            key=f"{key}_{idx}_{f}",
                        )
                        row[f] = [ln.strip() for ln in text.splitlines() if ln.strip()]
                    elif f in ("items", "description", "text", "profile"):
                        row[f] = col.text_area(
                            f.capitalize(), value=default, key=f"{key}_{idx}_{f}"
                        )
                    else:
                        row[f] = col.text_input(
                            f.capitalize(), value=default, key=f"{key}_{idx}_{f}"
                        )

            if not remove:
                edited.append(row)

    st.caption(f"{len(edited)} entry(ies)")

    def blank() -> dict:
        d = {}
        for fields in layout:
            for f in fields:
                d[f] = [] if f == "highlights" else ""
        return d

    if st.button(f"Add {title}", key=f"{key}_add_btn"):
        edited.append(blank())

    return edited


def str_list_editor(title: str, items: list, key: str) -> list:
    """Edit a flat list of strings (e.g. certifications)."""
    st.subheader(title)
    text = st.text_area(
        "One per line",
        value="\n".join(items),
        key=f"{key}_strings",
    )
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------

def _init_state() -> None:
    if "view" in st.session_state:
        return
    st.session_state.view = "Editor"
    st.session_state.preview_open = True
    st.session_state.pdf = None

    saved = db.list_resumes()
    if saved:
        r = db.get_resume(saved[0]["id"])
        st.session_state.resume_id = r["id"]
        st.session_state.data = r["data"]
        st.session_state.template = r["template"]
        st.session_state.font = r.get("font", DEFAULT_FONT)
        st.session_state.resume_selector = r["id"]
        st.session_state.pdf = r.get("pdf")
    elif JSON_PATH.exists():
        st.session_state.resume_id = None
        st.session_state.data = load_data() or _blank_data()
        st.session_state.template = "classic"
        st.session_state.font = DEFAULT_FONT
        st.session_state.resume_selector = -1
    else:
        st.session_state.resume_id = None
        st.session_state.data = _blank_data()
        st.session_state.template = "classic"
        st.session_state.font = DEFAULT_FONT
        st.session_state.resume_selector = -1


def _apply_pending() -> None:
    """Apply a pending state switch queued by a button handler.

    Widget-backed keys (``template``, ``resume_selector``, ``view``) can only
    be mutated before their widget is instantiated, so state changes are queued
    here at the top of the script and applied before any widgets render.
    """
    p = st.session_state.pop("_pending", None)
    if p:
        for k, v in p.items():
            st.session_state[k] = v


def _flash(message: str) -> None:
    """Queue a toast to show on the next rerun.

    ``st.toast`` is dropped when immediately followed by ``st.rerun()``, so
    actions that rerun stash the message here and it is toasted at the top of
    ``main()`` after the rerun.
    """
    st.session_state._flash = message


def _switch_resume(resume_id, data, template, font, pdf) -> None:
    st.session_state._pending = {
        "resume_id": resume_id,
        "data": data,
        "template": template,
        "font": font,
        "pdf": pdf,
        "resume_selector": resume_id if resume_id is not None else -1,
    }
    st.rerun()


def _open_in_editor(r: dict) -> None:
    st.session_state._pending = {
        "view": "Editor",
        "resume_id": r["id"],
        "data": r["data"],
        "template": r["template"],
        "font": r.get("font", DEFAULT_FONT),
        "pdf": r.get("pdf"),
        "resume_selector": r["id"],
    }
    st.rerun()


def _on_resume_change() -> None:
    sel = st.session_state.resume_selector
    if sel == -1:
        return
    r = db.get_resume(sel)
    if r is None:
        return
    st.session_state.resume_id = r["id"]
    st.session_state.data = r["data"]
    st.session_state.pdf = r.get("pdf")
    st.session_state.template = r["template"]
    st.session_state.font = r.get("font", DEFAULT_FONT)


def _on_import_json() -> None:
    uploaded = st.session_state.get("import_json")
    if uploaded is None:
        return
    try:
        raw = json.loads(uploaded.getvalue().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        st.session_state.import_error = f"Could not parse JSON: {exc}"
        return
    if not isinstance(raw, dict):
        st.session_state.import_error = "Invalid resume.json: expected a JSON object."
        return
    st.session_state.import_error = None
    data = _blank_data()
    data.update(raw)
    _flash("Imported resume.json.")
    _switch_resume(None, data, "classic", DEFAULT_FONT, None)


def _open_analysis(mode: str, resume_id: int) -> None:
    st.session_state._pending = {
        "view": mode,
        "analysis_resume_id": resume_id,
    }
    st.rerun()


def _resume_text(full: dict) -> str:
    """Return the resume as plain text (compiling it if no PDF is stored)."""
    pdf = full.get("pdf")
    if not pdf:
        tex = render_tex(
            full["data"], full["template"], full.get("font", DEFAULT_FONT)
        )
        pdf = compile_pdf(tex)
    return pdf_to_text(pdf)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def _render_editor_sidebar() -> None:
    st.header("Resumes")

    saved = db.list_resumes()
    has_unsaved = st.session_state.resume_id is None

    options = []
    labels = {}
    if has_unsaved:
        options.append(-1)
        labels[-1] = "— New / unsaved —"
    for r in saved:
        options.append(r["id"])
        labels[r["id"]] = f"{r['name']}  ·  {TEMPLATES[r['template']][0]}"

    if options:
        st.selectbox(
            "Open resume",
            options,
            key="resume_selector",
            format_func=lambda x: labels.get(x, str(x)),
            on_change=_on_resume_change,
        )
    else:
        st.caption("No saved resumes yet.")

    c1, c2 = st.columns(2)
    if c1.button("New", use_container_width=True):
        _switch_resume(None, _blank_data(), "classic", DEFAULT_FONT, None)
    if c2.button(
        "Delete",
        use_container_width=True,
        disabled=st.session_state.resume_id is None,
    ):
        db.delete_resume(st.session_state.resume_id)
        _flash("Resume deleted.")
        _switch_resume(None, _blank_data(), "classic", DEFAULT_FONT, None)

    st.divider()
    st.header("Template")

    template_names = list(TEMPLATES)
    template = st.radio(
        "Select an ATS template",
        template_names,
        key="template",
        format_func=lambda t: TEMPLATES[t][0],
    )
    st.caption(TEMPLATES[template][1])

    st.divider()
    st.header("Font")

    fonts = installed_fonts()
    if st.session_state.get("font") not in fonts:
        st.session_state.font = DEFAULT_FONT if DEFAULT_FONT in fonts else fonts[0]

    st.radio(
        "Select a font",
        fonts,
        key="font",
        format_func=lambda f: FONTS[f][0],
    )

    missing = [FONTS[f][0] for f in FONTS if f not in fonts]
    if missing:
        st.caption(
            "More ATS fonts available via `tlmgr install "
            "collection-fontsrecommended`: " + ", ".join(missing)
        )

    st.divider()
    st.header("Actions")

    if st.button("Save Resume", use_container_width=True):
        _save_current()

    if st.button("Generate PDF", type="primary", use_container_width=True):
        _generate_pdf()

    if st.session_state.get("pdf"):
        name = _resume_title(st.session_state.data).replace(" ", "_")
        fname = f"{name}_{st.session_state.template}.pdf"
        st.download_button(
            "Download PDF",
            data=st.session_state.pdf,
            file_name=fname,
            mime="application/pdf",
            use_container_width=True,
        )

    st.divider()
    st.header("Import")

    st.file_uploader(
        "Import resume.json",
        type=["json"],
        key="import_json",
        on_change=_on_import_json,
        help="Upload a resume JSON (e.g. one downloaded from the Library) "
        "to load it into the editor.",
    )
    if st.session_state.get("import_error"):
        st.error(st.session_state.import_error)
        st.session_state.pop("import_error", None)


def _save_current() -> None:
    data = st.session_state.data
    name = _resume_title(data)
    template = st.session_state.template
    font = st.session_state.font
    rid = st.session_state.resume_id

    if rid is None:
        rid = db.create_resume(name, template, font, data)
        _flash("Saved as a new resume.")
        _switch_resume(rid, data, template, font, st.session_state.pdf)
    else:
        db.update_resume(rid, name, template, font, data)
        _flash("Saved.")
        st.rerun()


def _generate_pdf() -> None:
    data = st.session_state.data
    template = st.session_state.template
    font = st.session_state.font
    try:
        with st.spinner("Compiling PDF..."):
            tex = render_tex(data, template, font)
            pdf_bytes = compile_pdf(tex)
        st.session_state.pdf = pdf_bytes
        if st.session_state.resume_id is not None:
            db.save_pdf(st.session_state.resume_id, pdf_bytes)
        st.toast("PDF generated.")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Compilation failed:\n\n{exc}")


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

def _render_editor() -> None:
    if not shutil.which("pdflatex"):
        st.error(
            "`pdflatex` was not found. Install a TeX distribution (e.g. "
            "`brew install --cask basictex`) and restart this app."
        )

    data = st.session_state.data
    template = st.session_state.template
    font = st.session_state.font

    cols = (
        st.columns([1.15, 1], gap="large")
        if st.session_state.preview_open
        else st.columns([1], gap="large")
    )
    left = cols[0]
    right = cols[1] if len(cols) > 1 else None

    with left:
        st.subheader("Header")
        data["title"] = st.text_input(
            "Resume title",
            data.get("title", ""),
            help="Label shown in the library (e.g. \"Frontend Role\"). "
            "Defaults to the full name if left blank.",
        )
        data["name"] = st.text_input("Full name", data.get("name", ""))
        data["headline"] = st.text_input("Headline", data.get("headline", ""))

        contact = data.setdefault("contact", {})
        c1, c2, c3 = st.columns(3)
        contact["location"] = c1.text_input("Location", contact.get("location", ""))
        contact["email"] = c2.text_input("Email", contact.get("email", ""))
        contact["phone"] = c3.text_input("Phone", contact.get("phone", ""))
        c4, c5, _ = st.columns(3)
        contact["github"] = c4.text_input("GitHub", contact.get("github", ""))
        contact["linkedin"] = c5.text_input("LinkedIn", contact.get("linkedin", ""))

        data["profile"] = st.text_area("Profile", data.get("profile", ""), height=120)

        tab_exp, tab_skills, tab_impact, tab_edu, tab_labels = st.tabs(
            ["Experience", "Skills", "Impact & Leadership", "Education & Extras", "Sections"]
        )

        with tab_exp:
            data["experience"] = list_editor(
                "Professional Experience",
                data.get("experience", []),
                [["role", "company"], ["type", "dates"], ["highlights"]],
                "exp",
            )

        with tab_skills:
            data["skills"] = list_editor(
                "Core Technical Skills",
                data.get("skills", []),
                [["group"], ["items"]],
                "skills",
            )
            data["capabilities"] = list_editor(
                "Technical Capabilities",
                data.get("capabilities", []),
                [["group"], ["items"]],
                "caps",
            )

        with tab_impact:
            data["impact"] = list_editor(
                "Selected Engineering Impact",
                data.get("impact", []),
                [["lead"], ["text"]],
                "impact",
            )
            data["leadership"] = list_editor(
                "Leadership & Community",
                data.get("leadership", []),
                [["role", "org"], ["dates"], ["description"]],
                "lead",
            )

        with tab_edu:
            data["education"] = list_editor(
                "Education",
                data.get("education", []),
                [["degree"], ["school", "year"]],
                "edu",
            )
            data["certifications"] = str_list_editor(
                "Certifications", data.get("certifications", []), "cert"
            )

            data["career_progression"] = st.text_area(
                "Career Progression", data.get("career_progression", ""), height=80
            )
            data["professional_profile"] = st.text_area(
                "Professional Profile", data.get("professional_profile", ""), height=100
            )

            tech = st.text_area(
                "Technology Index (comma separated)",
                value=", ".join(data.get("technology_index", [])),
                height=80,
            )
            data["technology_index"] = [t.strip() for t in tech.split(",") if t.strip()]

            data["references"] = st.text_area(
                "References", data.get("references", ""), height=60
            )

        with tab_labels:
            st.subheader("Sections")
            st.caption(
                "Toggle a section off to remove it from the generated resume, "
                "or rename its heading."
            )
            labels = data.setdefault("section_labels", {})
            sections = data.setdefault("sections", {})

            for key in DEFAULT_SECTION_LABELS:
                show_col, label_col = st.columns([0.55, 1], vertical_alignment="center")
                sections[key] = show_col.toggle(
                    DEFAULT_SECTION_LABELS[key],
                    value=sections.get(key, True),
                    key=f"section_show_{key}",
                )
                labels[key] = label_col.text_input(
                    "Heading",
                    value=labels.get(key, DEFAULT_SECTION_LABELS[key]),
                    key=f"section_label_{key}",
                )

            if st.button("Reset sections"):
                data["section_labels"] = {}
                data["sections"] = {}
                st.rerun()

    if right is not None:
        with right:
            st.subheader("Live Preview")
            try:
                serialized = json.dumps(data, ensure_ascii=False, sort_keys=True)
                with st.spinner("Rendering..."):
                    pages = live_pages(template, font, serialized)
                for i, png in enumerate(pages, start=1):
                    st.image(png, caption=f"Page {i}", use_container_width=True)
            except Exception as exc:  # noqa: BLE001
                st.warning(f"Preview unavailable:\n\n{exc}")

            with st.expander("View LaTeX source"):
                try:
                    tex = render_tex(data, template, font)
                    st.code(tex, language="latex")
                except Exception as exc:  # noqa: BLE001
                    st.warning(f"Could not render preview: {exc}")

    if st.session_state.preview_open:
        if st.button("◀", key="toggle_preview", type="primary", help="Collapse preview"):
            st.session_state.preview_open = False
            st.rerun()
    else:
        if st.button("▶", key="toggle_preview", type="primary", help="Show preview"):
            st.session_state.preview_open = True
            st.rerun()


def _render_library() -> None:
    st.title("Resume Library")

    resumes = db.list_resumes()
    if not resumes:
        st.info("No saved resumes yet. Switch to the Editor view to create one.")
        return

    st.caption(f"{len(resumes)} saved resume(s)")

    for r in resumes:
        full = db.get_resume(r["id"])
        fname = _resume_title(full["data"]).replace(" ", "_")

        with st.container(border=True):
            head = st.columns([3, 2, 2, 2])
            head[0].markdown(f"**{full['name']}**")
            head[1].markdown(f"Template: `{TEMPLATES[full['template']][0]}`")
            head[2].markdown(f"Font: `{FONTS[full['font']][0]}`")
            head[3].markdown(f"Updated: {full['updated_at'][:10]}")

            actions = st.columns([1.2, 1, 1, 1])
            if actions[0].button(
                "Open in Editor", key=f"open_{r['id']}", use_container_width=True
            ):
                _open_in_editor(full)

            if actions[1].button(
                "HR Analysis", key=f"hr_{r['id']}", use_container_width=True
            ):
                _open_analysis("HR Analysis", r["id"])

            if actions[2].button(
                "ATS Analysis", key=f"ats_{r['id']}", use_container_width=True
            ):
                _open_analysis("ATS Analysis", r["id"])

            if full.get("pdf"):
                actions[3].download_button(
                    "PDF",
                    data=full["pdf"],
                    file_name=f"{fname}_{full['template']}.pdf",
                    mime="application/pdf",
                    key=f"dl_{r['id']}",
                    use_container_width=True,
                )

            row2 = st.columns([1, 1, 1])
            row2[0].download_button(
                "JSON",
                data=json.dumps(full["data"], indent=2, ensure_ascii=False),
                file_name=f"{fname}.json",
                mime="application/json",
                key=f"json_{r['id']}",
                use_container_width=True,
            )

            if row2[1].button(
                "Delete", key=f"del_{r['id']}", use_container_width=True
            ):
                db.delete_resume(r["id"])
                if st.session_state.resume_id == r["id"]:
                    _switch_resume(None, _blank_data(), "classic", DEFAULT_FONT, None)
                else:
                    _flash("Resume deleted.")
                    st.rerun()

            if full.get("pdf"):
                with st.expander("Preview"):
                    try:
                        st.image(thumbnail(full["pdf"]), use_container_width=True)
                    except Exception as exc:  # noqa: BLE001
                        st.warning(f"Preview unavailable: {exc}")


def _render_analysis(mode: str) -> None:
    st.title(mode)

    saved = db.list_resumes()
    if not saved:
        st.info("No saved resumes yet. Create one in the Editor view first.")
        return

    labels = {r["id"]: f"{r['name']}  ·  {TEMPLATES[r['template']][0]}" for r in saved}
    ids = [r["id"] for r in saved]

    if st.session_state.get("analysis_resume_id") not in ids:
        st.session_state.analysis_resume_id = ids[0]

    st.selectbox(
        "Resume",
        ids,
        key="analysis_resume_id",
        format_func=lambda x: labels.get(x, str(x)),
    )

    job = st.text_area(
        "Target role / job description",
        height=220,
        key="analysis_job",
        placeholder="Paste the full job posting here. The analysis scores the resume against this role.",
    )

    if st.button(f"Run {mode}", type="primary"):
        _run_analysis(mode, st.session_state.analysis_resume_id, job)

    fresh = st.session_state.pop("_analysis_fresh", False)
    result = st.session_state.get("analysis_result")
    if (
        result
        and not fresh
        and st.session_state.get("analysis_result_ctx")
        == (mode, st.session_state.analysis_resume_id)
    ):
        st.divider()
        st.markdown(result)


def _run_analysis(mode: str, resume_id: int, job: str) -> None:
    if not job.strip():
        st.warning("Paste a job description first.")
        return

    full = db.get_resume(resume_id)
    if full is None:
        st.error("Resume not found.")
        return

    try:
        text = _resume_text(full)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not extract resume text:\n\n{exc}")
        return

    try:
        if mode == "HR Analysis":
            stream = llm.analyze_hr(text, job)
        else:
            stream = llm.analyze_ats(text, job)
        result = st.write_stream(stream)

        if not result or not str(result).strip():
            st.error("The model returned an empty response. Please try again.")
            return

        st.session_state.analysis_result = result
        st.session_state.analysis_result_ctx = (mode, resume_id)
        st.session_state._analysis_fresh = True
    except Exception as exc:  # noqa: BLE001
        st.error(f"Analysis failed:\n\n{exc}")


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def _auth_credentials() -> dict[str, str]:
    """Return username -> password pairs from Streamlit secrets or env vars."""
    creds: dict[str, str] = {}
    try:
        auth = st.secrets.get("auth", {})
        if hasattr(auth, "items"):
            creds = {str(k): v for k, v in auth.items() if isinstance(v, str)}
    except Exception:
        pass
    if not creds:
        user = os.environ.get("AUTH_USERNAME")
        password = os.environ.get("AUTH_PASSWORD")
        if user and password:
            creds = {user: password}
    return creds


def _check_password(candidate: str, stored: str) -> bool:
    """Compare a candidate password against plaintext or a ``sha256$`` hash."""
    if stored.startswith("sha256$"):
        digest = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
        return hmac.compare_digest(digest, stored[len("sha256$"):])
    return hmac.compare_digest(candidate, stored)


# ---------------------------------------------------------------------------
# Login persistence
#
# A signed token is stashed in a URL query param (not a cookie) so a page
# refresh doesn't sign you out. Cookies would need to be set via a script
# injected in a components.html iframe, which ad/tracker blockers such as
# Brave Shields treat as a tracking pattern and silently drop — query params
# are native to Streamlit and don't hit that.
# ---------------------------------------------------------------------------

_AUTH_QUERY_PARAM = "auth"
_AUTH_TOKEN_MAX_AGE_DAYS = 30


def _auth_secret(creds: dict[str, str]) -> bytes:
    """Derive a signing key from the configured credentials.

    Tied to the credentials themselves so that changing a password
    invalidates any tokens issued under the old one.
    """
    material = "|".join(f"{u}:{p}" for u, p in sorted(creds.items()))
    return hashlib.sha256(material.encode("utf-8")).digest()


def _make_auth_token(username: str, creds: dict[str, str]) -> str:
    expires = int(time.time()) + _AUTH_TOKEN_MAX_AGE_DAYS * 86400
    payload = f"{username}:{expires}"
    sig = hmac.new(_auth_secret(creds), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def _verify_auth_token(token: str, creds: dict[str, str]) -> str | None:
    try:
        username, expires_s, sig = token.split(":", 2)
        expires = int(expires_s)
    except (ValueError, AttributeError):
        return None
    if username not in creds or time.time() > expires:
        return None
    expected = hmac.new(
        _auth_secret(creds), f"{username}:{expires}".encode("utf-8"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    return username


def _render_auth_setup() -> None:
    st.title("Resume Builder")
    st.error("Authentication is not configured.")
    st.markdown(
        "This app requires a login. Configure credentials before sharing it.\n\n"
        "Create `.streamlit/secrets.toml` locally (or use the Secrets manager "
        "in Streamlit Cloud) with:\n\n"
        "```toml\n"
        "[auth]\n"
        'username = "your-password"\n'
        'DEEPSEEK_API_KEY = "sk-..."\n'
        "```\n\n"
        "Passwords may also be stored as a SHA-256 hash using the `sha256$` prefix."
    )


def _login_screen() -> None:
    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)
    st.title("Resume Builder")
    st.markdown("Sign in to continue.")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", use_container_width=True)

    if submitted:
        creds = _auth_credentials()
        if username in creds and _check_password(password, creds[username]):
            st.session_state.authenticated = True
            st.session_state.auth_user = username
            st.query_params[_AUTH_QUERY_PARAM] = _make_auth_token(username, creds)
            st.rerun()
        else:
            st.error("Invalid username or password.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    if not st.session_state.get("authenticated"):
        creds = _auth_credentials()
        if not creds:
            _render_auth_setup()
            return
        token = st.query_params.get(_AUTH_QUERY_PARAM)
        username = _verify_auth_token(token, creds) if token else None
        if username:
            st.session_state.authenticated = True
            st.session_state.auth_user = username
        else:
            _login_screen()
            return

    db.init_db()

    # Seed the database with the existing resume.json on first launch so the
    # current data is immediately available in the library.
    if not db.list_resumes() and JSON_PATH.exists():
        data = load_data()
        if data:
            db.create_resume(
                data.get("name") or "Imported Resume", "classic", DEFAULT_FONT, data
            )

    _init_state()
    _apply_pending()

    flash = st.session_state.pop("_flash", None)
    if flash:
        st.toast(flash)

    view = st.session_state.view

    if view == "Editor":
        st.markdown(_LOCK_CSS, unsafe_allow_html=True)
    else:
        st.markdown(_SIDEBAR_CSS, unsafe_allow_html=True)

    with st.sidebar:
        st.selectbox(
            "View",
            ["Editor", "Resume Library", "HR Analysis", "ATS Analysis"],
            key="view",
        )
        st.divider()
        st.caption(f"Signed in as {st.session_state.get('auth_user', '?')}")
        if st.button("Sign out", use_container_width=True):
            st.query_params.pop(_AUTH_QUERY_PARAM, None)
            st.session_state.clear()
            st.rerun()

    if view == "Editor":
        with st.sidebar:
            _render_editor_sidebar()
        _render_editor()
    elif view == "Resume Library":
        _render_library()
    else:
        _render_analysis(view)


if __name__ == "__main__":
    main()
