"""Pydantic request/response models.

The resume data models mirror the exact JSON shape ``resume_generator.py``
depends on — see the field-level comments for shape quirks (e.g.
``SkillGroup.items`` is a comma-joined string, not a list) that must be
preserved rather than "fixed".
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


def strip_uids(value):
    """Recursively remove client-side-only ``_uid`` bookkeeping keys
    (used by the frontend's list editors for stable React keys) before the
    data is persisted or exported. Mirrors the original Streamlit app's
    ``_strip_uids``."""
    if isinstance(value, dict):
        return {k: strip_uids(v) for k, v in value.items() if k != "_uid"}
    if isinstance(value, list):
        return [strip_uids(v) for v in value]
    return value


class Contact(BaseModel):
    model_config = ConfigDict(extra="allow")
    location: str = ""
    email: str = ""
    phone: str = ""
    github: str = ""  # schemeless, e.g. "github.com/x" — render_tex prepends https://
    linkedin: str = ""  # schemeless, same as github


class ExperienceEntry(BaseModel):
    model_config = ConfigDict(extra="allow")
    role: str = ""
    company: str = ""
    type: str = ""
    dates: str = ""
    highlights: list[str] = Field(default_factory=list)


class SkillGroup(BaseModel):
    model_config = ConfigDict(extra="allow")
    group: str = ""
    items: str = ""  # comma-joined STRING, not a list — preserve as-is


class ImpactEntry(BaseModel):
    model_config = ConfigDict(extra="allow")
    lead: str = ""
    text: str = ""


class LeadershipEntry(BaseModel):
    model_config = ConfigDict(extra="allow")
    role: str = ""
    org: str = ""
    dates: str = ""
    description: str = ""


class EducationEntry(BaseModel):
    model_config = ConfigDict(extra="allow")
    degree: str = ""
    school: str = ""
    year: str = ""


class ResumeData(BaseModel):
    model_config = ConfigDict(extra="allow")
    title: str = ""
    name: str = ""
    headline: str = ""
    contact: Contact = Field(default_factory=Contact)
    profile: str = ""
    skills: list[SkillGroup] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    impact: list[ImpactEntry] = Field(default_factory=list)
    leadership: list[LeadershipEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)  # flat array of strings
    capabilities: list[SkillGroup] = Field(default_factory=list)  # same shape as skills
    career_progression: str = ""
    professional_profile: str = ""
    technology_index: list[str] = Field(default_factory=list)  # TRUE array (unlike skills.items)
    references: str = ""
    section_labels: dict[str, str] = Field(default_factory=dict)
    sections: dict[str, bool] = Field(default_factory=dict)

    def cleaned(self) -> dict:
        return strip_uids(self.model_dump())


def resume_title(data: dict) -> str:
    title = (data.get("title") or "").strip()
    if title:
        return title
    name = (data.get("name") or "").strip()
    return name or "Untitled Resume"


# --- Auth -----------------------------------------------------------------


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    signup_code: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    created_at: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=1)
    password: str = Field(min_length=8)


class PasswordResetResponse(BaseModel):
    ok: bool = True
    # Only set while email delivery is not configured (dev fallback).
    reset_token: str | None = None
    note: str | None = None


# --- Profiles ---------------------------------------------------------------


class ProfileCreate(BaseModel):
    name: str = Field(min_length=1)
    headline: str | None = None


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=1)
    headline: str | None = None


class ProfileOut(BaseModel):
    id: int
    user_id: int
    name: str
    headline: str | None = None
    resume_count: int = 0
    created_at: str
    updated_at: str


# --- Resumes ----------------------------------------------------------------


class ResumeSummary(BaseModel):
    id: int
    profile_id: int
    name: str
    template: str
    font: str
    source: str = "built"  # "built" (structured editor) or "uploaded" (Quick Check PDF)
    has_pdf: bool
    created_at: str
    updated_at: str


class ResumeOut(BaseModel):
    id: int
    profile_id: int
    name: str
    template: str
    font: str
    data: ResumeData
    source: str = "built"
    has_pdf: bool
    created_at: str
    updated_at: str


class ResumeCreate(BaseModel):
    name: str | None = None
    template: str = "classic"
    font: str = "lmodern"
    data: ResumeData = Field(default_factory=ResumeData)


class ResumeUpdate(BaseModel):
    name: str | None = None
    template: str = "classic"
    font: str = "lmodern"
    data: ResumeData = Field(default_factory=ResumeData)


class ResumePreviewRequest(BaseModel):
    template: str = "classic"
    font: str = "lmodern"
    data: ResumeData = Field(default_factory=ResumeData)


class ResumePreviewResponse(BaseModel):
    pages: list[str]  # data: URI PNGs, base64-encoded


class AnalysisRequest(BaseModel):
    job_description: str = Field(min_length=1)


class AnalysisPdfRequest(BaseModel):
    kind: str  # "hr" or "ats" — cover letters aren't exported as PDF
    job_description: str = ""
    result: str = Field(min_length=1)


# --- Generation history (HR review / ATS check / cover letter) ------------


class GenerationSummary(BaseModel):
    id: int
    resume_id: int
    kind: str
    job_description: str
    created_at: str


class GenerationOut(GenerationSummary):
    result: str


class HistoryEntry(GenerationSummary):
    """A generation record enriched for the unified History page — includes
    which resume/profile it belongs to so profile-less (Quick Check) scans
    can be told apart from ones tied to a named profile."""

    resume_name: str
    profile_id: int
    profile_name: str
    is_quick: bool


# --- Job board ----------------------------------------------------------

JobChannel = Literal["email", "whatsapp", "telegram"]


class JobSubscriptionCreate(BaseModel):
    keyword: str = Field(min_length=1, max_length=200)
    channel: JobChannel
    channel_target: str = Field(min_length=1, max_length=200)


class JobSubscriptionOut(BaseModel):
    id: int
    user_id: int
    keyword: str
    channel: JobChannel
    channel_target: str
    active: bool
    created_at: str


class JobOut(BaseModel):
    id: int
    source: str
    title: str
    company: str | None = None
    location: str | None = None
    job_type: str | None = None  # e.g. "Full-time · Remote" — best-effort, source-dependent
    salary: str | None = None  # best-effort, source-dependent — many postings omit it
    description: str | None = None  # plain-text snippet, source-dependent
    url: str
    posted_at: str | None = None
    fetched_at: str


class JobListResponse(BaseModel):
    items: list[JobOut]
    total: int
    page: int
    page_size: int


class JobFilterOptions(BaseModel):
    job_types: list[str]
    sources: list[str]
    locations: list[str]


class JobNotificationOut(JobOut):
    notification_id: int
    channel: JobChannel
    status: str
    sent_at: str


# --- Job board: internal (n8n) ---------------------------------------------


class JobPostingIn(BaseModel):
    """One normalized posting from an n8n source branch. dedup_hash is
    computed server-side from source+title+company+(dedup_key or url) —
    n8n doesn't need to hash it, just send the raw fields.

    dedup_key is only needed for sources whose url isn't a stable identity
    for the same posting (e.g. a per-request tracking redirect) — send a
    stable substitute there instead so the same posting doesn't look new
    on every run. url is still stored and used as the actual apply link
    either way."""

    source: str = Field(min_length=1)
    title: str = Field(min_length=1)
    company: str | None = None
    location: str | None = None
    job_type: str | None = None
    salary: str | None = None
    description: str | None = None
    url: str = Field(min_length=1)
    posted_at: str | None = None
    dedup_key: str | None = None


class JobUpsertBatchRequest(BaseModel):
    postings: list[JobPostingIn]


class JobUpsertBatchResponse(BaseModel):
    inserted: list[JobOut]  # only the postings that were genuinely new


class JobMatchRequest(BaseModel):
    job_ids: list[int]


class JobMatch(BaseModel):
    subscription_id: int
    user_id: int
    job_id: int
    channel: JobChannel
    channel_target: str
    # Job fields inlined so n8n can compose the notification message
    # directly off the match, with no extra lookup call per match.
    job_title: str
    job_company: str | None = None
    job_location: str | None = None
    job_type: str | None = None
    job_salary: str | None = None
    job_url: str


class JobMatchResponse(BaseModel):
    matches: list[JobMatch]


class JobNotificationRecordRequest(BaseModel):
    user_id: int
    job_id: int
    subscription_id: int | None = None
    channel: JobChannel
    status: str = "sent"


class JobNotificationRecordResponse(BaseModel):
    recorded: bool  # False means this user was already notified about this job


# --- Telegram connect flow ------------------------------------------------


class TelegramConnectResponse(BaseModel):
    deep_link: str
    expires_at: str


class TelegramStatusResponse(BaseModel):
    linked: bool
    chat_id: str | None = None
    username: str | None = None
