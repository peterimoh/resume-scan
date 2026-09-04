import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { resumesApi } from "../api/resumes";
import { ApiError } from "../api/client";
import type { ResumeSummary } from "../types/resume";
import { EmptyState, SkeletonList } from "../components/ui";
import { ResumeThumbnail } from "../components/ResumeThumbnail";
import { ActionMenu } from "../components/ActionMenu";
import {
  AlertIcon,
  DownloadIcon,
  EyeIcon,
  InboxIcon,
  TargetIcon,
  TrashIcon,
  UploadIcon,
} from "../components/icons";

export function QuickCheckPage() {
  const [resumes, setResumes] = useState<ResumeSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const load = () => {
    resumesApi
      .listQuick()
      .then(setResumes)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load your scans."));
  };

  useEffect(load, []);

  const upload = async (file: File) => {
    setError(null);
    setUploading(true);
    try {
      await resumesApi.uploadQuick(file);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const onFileChosen = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (file) upload(file);
  };

  const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) upload(file);
  };

  const removeResume = async (id: number) => {
    if (!confirm("Delete this scan? This cannot be undone.")) return;
    try {
      await resumesApi.remove(id);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete this scan.");
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
      <div className="page-head">
        <div>
          <h2>Quick Check</h2>
          <p className="subtitle">
            Upload a resume PDF and run an ATS check or HR review straight away — no profile
            needed.
          </p>
        </div>
      </div>

      {error && (
        <div className="error">
          <AlertIcon size={15} />
          {error}
        </div>
      )}

      <div
        className={`quick-dropzone${dragOver ? " is-drag" : ""}${uploading ? " is-busy" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
      >
        <UploadIcon size={22} />
        <p className="quick-dropzone-title">
          {uploading ? "Uploading…" : "Drag & drop a resume PDF here"}
        </p>
        <p className="quick-dropzone-hint">or</p>
        <label className="btn btn-primary" style={{ cursor: "pointer" }}>
          Browse files
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf"
            onChange={onFileChosen}
            disabled={uploading}
            hidden
          />
        </label>
      </div>

      {resumes === null ? (
        <SkeletonList count={2} height={110} />
      ) : resumes.length === 0 ? (
        <EmptyState
          icon={<TargetIcon size={24} />}
          title="No scans yet"
          message="Upload a resume PDF above to run your first ATS check or HR review."
        />
      ) : (
        <div className="stack">
          {resumes.map((r) => (
            <div className="card card-hover" key={r.id}>
              <div className="row" style={{ alignItems: "center", marginBottom: 14 }}>
                {r.has_pdf && (
                  <span style={{ display: "block", flex: "0 0 auto" }}>
                    <ResumeThumbnail resumeId={r.id} />
                  </span>
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
                    <span className="meta-chip">Uploaded {r.created_at.slice(0, 10)}</span>
                  </div>
                </div>
              </div>
              <div
                className="btn-row"
                style={{ borderTop: "1px solid var(--border)", paddingTop: 14 }}
              >
                <Link className="btn btn-primary btn-sm" to={`/quick-check/${r.id}/analysis/ats`}>
                  <TargetIcon size={14} /> Analyze
                </Link>
                <Link className="btn btn-sm" to={`/quick-check/${r.id}/history`}>
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
                      {
                        label: "Download PDF",
                        icon: <DownloadIcon size={14} />,
                        onClick: () => resumesApi.downloadPdf(r.id, r.name),
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
