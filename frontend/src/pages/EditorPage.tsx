import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { resumesApi } from "../api/resumes";
import { metaApi } from "../api/meta";
import { ApiError } from "../api/client";
import {
  blankResumeData,
  resumeTitle,
  type FontMeta,
  type ResumeData,
  type TemplateMeta,
} from "../types/resume";
import { HeaderFields } from "../components/editor/HeaderFields";
import { ExperienceTab } from "../components/editor/ExperienceTab";
import { SkillsTab } from "../components/editor/SkillsTab";
import { ImpactLeadershipTab } from "../components/editor/ImpactLeadershipTab";
import { EducationExtrasTab } from "../components/editor/EducationExtrasTab";
import { SectionsTab } from "../components/editor/SectionsTab";
import { TemplateFontPicker } from "../components/editor/TemplateFontPicker";
import { PdfPreview } from "../components/PdfPreview";
import { SkeletonList, Toast } from "../components/ui";
import {
  AlertIcon,
  ArrowLeftIcon,
  DownloadIcon,
  EyeIcon,
  PencilIcon,
  SparklesIcon,
  TrashIcon,
  UploadIcon,
  WandIcon,
} from "../components/icons";

const TABS = ["Experience", "Skills", "Impact & Leadership", "Education & Extras", "Sections", "Design"] as const;
type Tab = (typeof TABS)[number];

type View = "edit" | "preview";

export function EditorPage() {
  const { profileId, resumeId } = useParams();
  const pid = Number(profileId);
  const rid = Number(resumeId);
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [data, setData] = useState<ResumeData>(blankResumeData());
  const [template, setTemplate] = useState("classic");
  const [font, setFont] = useState("lmodern");
  const [hasPdf, setHasPdf] = useState(false);
  const [tab, setTab] = useState<Tab>("Experience");
  const [view, setView] = useState<View>("edit");

  const [templates, setTemplates] = useState<Record<string, TemplateMeta>>({});
  const [fonts, setFonts] = useState<Record<string, FontMeta>>({});

  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);

  const [pages, setPages] = useState<string[]>([]);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    resumesApi
      .get(rid)
      .then((r) => {
        setData(r.data);
        setTemplate(r.template);
        setFont(r.font);
        setHasPdf(r.has_pdf);
      })
      .catch((err) => setLoadError(err instanceof ApiError ? err.message : "Failed to load resume."))
      .finally(() => setLoading(false));
    metaApi.templates().then(setTemplates).catch(() => setTemplates({}));
    metaApi.fonts().then(setFonts).catch(() => setFonts({}));
  }, [rid]);

  useEffect(() => {
    if (!flash) return;
    const t = setTimeout(() => setFlash(null), 3000);
    return () => clearTimeout(t);
  }, [flash]);

  // Debounced live preview, mirroring the original app's auto-recompiling pane.
  const serialized = useMemo(() => JSON.stringify({ template, font, data }), [template, font, data]);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (loading) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setPreviewLoading(true);
      setPreviewError(null);
      resumesApi
        .preview(template, font, data)
        .then((res) => setPages(res.pages))
        .catch((err) => setPreviewError(err instanceof ApiError ? err.message : "Preview failed."))
        .finally(() => setPreviewLoading(false));
    }, 500);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [serialized, loading]);

  const patch = (p: Partial<ResumeData>) => setData((prev) => ({ ...prev, ...p }));

  const save = async () => {
    setSaving(true);
    setActionError(null);
    try {
      const name = resumeTitle(data);
      const updated = await resumesApi.update(rid, { name, template, font, data });
      setData(updated.data);
      setFlash("Resume saved");
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to save resume.");
    } finally {
      setSaving(false);
    }
  };

  const generatePdf = async () => {
    setGenerating(true);
    setActionError(null);
    try {
      await save();
      const updated = await resumesApi.generatePdf(rid);
      setHasPdf(updated.has_pdf);
      setFlash("PDF generated");
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "PDF generation failed.");
    } finally {
      setGenerating(false);
    }
  };

  const downloadPdf = () => resumesApi.downloadPdf(rid, resumeTitle(data).replace(/ /g, "_"));

  const removeResume = async () => {
    if (!confirm("Delete this resume? This cannot be undone.")) return;
    try {
      await resumesApi.remove(rid);
      navigate(`/profiles/${pid}/resumes`);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to delete resume.");
    }
  };

  const onImportJson = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    file
      .text()
      .then((text) => {
        const parsed = JSON.parse(text);
        if (typeof parsed !== "object" || parsed === null) throw new Error("Invalid JSON");
        setData({ ...blankResumeData(), ...parsed });
        setFlash("Imported JSON");
      })
      .catch(() => setActionError("Could not parse the uploaded JSON file."));
  };

  const switchView = (v: View) => setView(v);

  if (loading) {
    return (
      <div className="stack-lg">
        <SkeletonList count={2} height={90} />
        <SkeletonList count={2} height={220} />
      </div>
    );
  }
  if (loadError) {
    return (
      <div className="error">
        <AlertIcon size={15} />
        {loadError}
      </div>
    );
  }

  return (
    <div className="editor-page">
      <div className="editor-head">
        <div className="editor-head-info">
          <Link className="breadcrumb" to={`/profiles/${pid}/resumes`}>
            <ArrowLeftIcon size={14} />
            Resume library
          </Link>
          <h2 title={resumeTitle(data)}>{resumeTitle(data)}</h2>
          <p className="subtitle">The preview updates automatically as you type.</p>
        </div>
        <div className="editor-actions">
          <button className="btn btn-primary" onClick={save} disabled={saving}>
            {saving ? (
              <>
                <span className="spinner" /> Saving…
              </>
            ) : (
              "Save"
            )}
          </button>
          <button className="btn" onClick={generatePdf} disabled={generating}>
            {generating ? (
              <>
                <span className="spinner" /> Generating…
              </>
            ) : (
              <>
                <WandIcon size={15} /> Generate PDF
              </>
            )}
          </button>
          {hasPdf && (
            <button className="btn" onClick={downloadPdf} title="Download PDF">
              <DownloadIcon size={15} />
            </button>
          )}
          <Link className="btn btn-soft" to={`/profiles/${pid}/resumes/${rid}/analysis/hr`}>
            <SparklesIcon size={15} /> Analyze
          </Link>
          <label className="btn" style={{ cursor: "pointer" }}>
            <UploadIcon size={15} /> Import JSON
            <input
              type="file"
              accept="application/json"
              onChange={onImportJson}
              hidden
            />
          </label>
          <button className="btn btn-danger" onClick={removeResume} title="Delete resume">
            <TrashIcon size={15} />
          </button>
        </div>
      </div>

      {actionError && (
        <div className="error">
          <AlertIcon size={15} />
          {actionError}
        </div>
      )}

      <div className="view-toggle-row">
        <div className="seg-control">
          <button
            type="button"
            className={view === "edit" ? "active" : ""}
            onClick={() => switchView("edit")}
          >
            <PencilIcon size={13} />
            Write
          </button>
          <button
            type="button"
            className={view === "preview" ? "active" : ""}
            onClick={() => switchView("preview")}
          >
            <EyeIcon size={13} />
            Preview
          </button>
        </div>
      </div>

      <div className="editor-workspace">
        <div className={`editor-content${view === "preview" ? " pane-hidden" : ""}`}>
          <div className="stack">
            <div className="card">
              <HeaderFields data={data} onChange={patch} />
            </div>

            <div className="tabs-sticky">
              <div className="tabs" role="tablist">
                {TABS.map((t) => (
                  <button
                    key={t}
                    role="tab"
                    aria-selected={tab === t}
                    className={`tab${tab === t ? " active" : ""}`}
                    onClick={() => setTab(t)}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>

            <div className="card">
              {tab === "Experience" && (
                <ExperienceTab
                  items={data.experience}
                  onChange={(items) => patch({ experience: items })}
                />
              )}
              {tab === "Skills" && (
                <SkillsTab
                  skills={data.skills}
                  capabilities={data.capabilities}
                  onChangeSkills={(items) => patch({ skills: items })}
                  onChangeCapabilities={(items) => patch({ capabilities: items })}
                />
              )}
              {tab === "Impact & Leadership" && (
                <ImpactLeadershipTab
                  impact={data.impact}
                  leadership={data.leadership}
                  onChangeImpact={(items) => patch({ impact: items })}
                  onChangeLeadership={(items) => patch({ leadership: items })}
                />
              )}
              {tab === "Education & Extras" && (
                <EducationExtrasTab
                  data={data}
                  onChangeEducation={(items) => patch({ education: items })}
                  onChangeCertifications={(items) => patch({ certifications: items })}
                  onChange={patch}
                />
              )}
              {tab === "Sections" && <SectionsTab data={data} onChange={patch} />}
              {tab === "Design" && (
                <div className="stack">
                  <div className="card-title" style={{ marginBottom: 0 }}>
                    <h3>Template & font</h3>
                    <span className="badge">Applies instantly</span>
                  </div>
                  <TemplateFontPicker
                    templates={templates}
                    fonts={fonts}
                    template={template}
                    font={font}
                    onTemplateChange={setTemplate}
                    onFontChange={setFont}
                  />
                </div>
              )}
            </div>
          </div>
        </div>

        <aside className={`preview-pane${view === "edit" ? " pane-hidden" : ""}`}>
          <div className="preview-pane-head">
            <h3>Live preview</h3>
            <div className="preview-pane-status">
              {pages.length > 0 && (
                <span className="meta-chip">
                  {pages.length} {pages.length === 1 ? "page" : "pages"}
                </span>
              )}
              {previewLoading ? (
                <span className="stream-indicator">
                  Rendering
                  <span className="dot" />
                  <span className="dot" />
                  <span className="dot" />
                </span>
              ) : (
                <span className="badge badge-success">Up to date</span>
              )}
            </div>
          </div>
          <div className="preview-pane-body">
            <PdfPreview pages={pages} loading={previewLoading} error={previewError} />
          </div>
        </aside>
      </div>

      {flash && <Toast message={flash} />}
    </div>
  );
}
