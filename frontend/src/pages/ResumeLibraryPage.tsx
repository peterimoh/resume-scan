import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { resumesApi } from "../api/resumes";
import { profilesApi } from "../api/profiles";
import { ApiError } from "../api/client";
import { blankResumeData, type Profile, type ResumeSummary } from "../types/resume";
import { EmptyState, SkeletonList } from "../components/ui";
import { ResumeThumbnail } from "../components/ResumeThumbnail";
import { ActionMenu } from "../components/ActionMenu";
import {
  AlertIcon,
  ArrowLeftIcon,
  CopyIcon,
  DownloadIcon,
  EyeIcon,
  FileIcon,
  InboxIcon,
  PencilIcon,
  PlusIcon,
  SparklesIcon,
  TrashIcon,
} from "../components/icons";

export function ResumeLibraryPage() {
  const { profileId } = useParams();
  const pid = Number(profileId);
  const navigate = useNavigate();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [resumes, setResumes] = useState<ResumeSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const load = () => {
    profilesApi.get(pid).then(setProfile).catch(() => setProfile(null));
    resumesApi
      .list(pid)
      .then(setResumes)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load resumes."));
  };

  useEffect(load, [pid]);

  const createResume = async () => {
    try {
      const r = await resumesApi.create(pid, {
        template: "classic",
        font: "lmodern",
        data: blankResumeData(),
      });
      navigate(`/profiles/${pid}/resumes/${r.id}/edit`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create resume.");
    }
  };

  const removeResume = async (id: number) => {
    if (!confirm("Delete this resume? This cannot be undone.")) return;
    try {
      await resumesApi.remove(id);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete resume.");
    }
  };

  const duplicateResume = async (id: number) => {
    try {
      await resumesApi.duplicate(id);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to duplicate resume.");
    }
  };

  const toggleExpanded = (id: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div className="stack-lg">
      <div>
        <Link className="breadcrumb" to="/profiles">
          <ArrowLeftIcon size={14} />
          All profiles
        </Link>
        <div className="page-head" style={{ marginTop: 8 }}>
          <div>
            <h2>{profile ? profile.name : "…"}</h2>
            <p className="subtitle">
              {resumes === null
                ? "Loading resumes…"
                : `${resumes.length} resume${resumes.length === 1 ? "" : "s"} in this library`}
            </p>
          </div>
          <button className="btn btn-primary" onClick={createResume}>
            <PlusIcon size={15} /> New resume
          </button>
        </div>
      </div>

      {error && (
        <div className="error">
          <AlertIcon size={15} />
          {error}
        </div>
      )}

      {resumes === null ? (
        <SkeletonList count={3} height={140} />
      ) : resumes.length === 0 ? (
        <EmptyState
          icon={<FileIcon size={24} />}
          title="No resumes yet"
          message="Create your first resume — you'll get a guided editor with a live PDF preview."
          action={
            <button className="btn btn-primary" onClick={createResume}>
              <PlusIcon size={15} /> New resume
            </button>
          }
        />
      ) : (
        <div className="stack">
          {resumes.map((r) => (
            <div className="card card-hover" key={r.id}>
              <div className="row" style={{ alignItems: "center", marginBottom: 14 }}>
                {r.has_pdf && (
                  <Link
                    to={`/profiles/${pid}/resumes/${r.id}/edit`}
                    title="Open in editor"
                    style={{ display: "block", flex: "0 0 auto" }}
                  >
                    <ResumeThumbnail resumeId={r.id} />
                  </Link>
                )}
                <div style={{ minWidth: 0, flex: 1 }}>
                  <h3
                    style={{
                      margin: 0,
                      fontSize: 16,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {r.name}
                  </h3>
                  <div className="meta-chips" style={{ marginTop: 8 }}>
                    <span className="meta-chip">{r.template}</span>
                    <span className="meta-chip">{r.font}</span>
                    <span className="meta-chip">
                      Updated {r.updated_at.slice(0, 10)}
                    </span>
                  </div>
                </div>
              </div>
              <div
                className="btn-row"
                style={{
                  borderTop: "1px solid var(--border)",
                  paddingTop: 14,
                }}
              >
                <Link
                  className="btn btn-primary btn-sm"
                  to={`/profiles/${pid}/resumes/${r.id}/edit`}
                >
                  <PencilIcon size={14} /> Edit
                </Link>
                <Link
                  className="btn btn-sm"
                  to={`/profiles/${pid}/resumes/${r.id}/analysis/hr`}
                >
                  <SparklesIcon size={14} /> Analyze
                </Link>
                <Link className="btn btn-sm" to={`/profiles/${pid}/resumes/${r.id}/history`}>
                  <InboxIcon size={14} /> History
                </Link>
                <div style={{ marginLeft: "auto" }}>
                  <ActionMenu
                    items={[
                      ...(r.has_pdf
                        ? [
                            {
                              label: expanded.has(r.id) ? "Hide preview" : "Preview",
                              icon: <EyeIcon size={14} />,
                              onClick: () => toggleExpanded(r.id),
                            },
                          ]
                        : []),
                      { label: "Duplicate", icon: <CopyIcon size={14} />, onClick: () => duplicateResume(r.id) },
                      ...(r.has_pdf
                        ? [
                            {
                              label: "Download PDF",
                              icon: <DownloadIcon size={14} />,
                              onClick: () => resumesApi.downloadPdf(r.id, r.name),
                            },
                          ]
                        : []),
                      {
                        label: "Download JSON",
                        icon: <DownloadIcon size={14} />,
                        onClick: () => resumesApi.downloadJson(r.id, r.name),
                      },
                      { label: "Delete", icon: <TrashIcon size={14} />, onClick: () => removeResume(r.id), danger: true },
                    ]}
                  />
                </div>
              </div>
              {expanded.has(r.id) && r.has_pdf && (
                <div className="preview-frame" style={{ marginTop: 14 }}>
                  <ResumeThumbnail resumeId={r.id} width={300} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
