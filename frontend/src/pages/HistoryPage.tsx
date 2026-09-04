import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { historyApi } from "../api/history";
import { resumesApi } from "../api/resumes";
import { downloadAnalysisPdf } from "../api/analysis";
import { ApiError } from "../api/client";
import { AtsCharts, HrCharts } from "../components/AnalysisCharts";
import { MarkdownStream } from "../components/MarkdownStream";
import { EmptyState, SkeletonList } from "../components/ui";
import { parseAnalysisPayload, type AtsChartData, type HrChartData } from "../lib/analysisPayload";
import {
  AlertIcon,
  ArrowLeftIcon,
  ChevronDownIcon,
  DownloadIcon,
  InboxIcon,
  MailIcon,
  SparklesIcon,
  TargetIcon,
  TrashIcon,
} from "../components/icons";
import type { Generation, GenerationKind, GenerationSummary, Resume } from "../types/resume";

type Filter = "all" | GenerationKind;

const KIND_META: Record<GenerationKind, { label: string; icon: typeof SparklesIcon }> = {
  hr: { label: "HR Review", icon: SparklesIcon },
  ats: { label: "ATS Check", icon: TargetIcon },
  cover_letter: { label: "Cover Letter", icon: MailIcon },
};

const FILTERS: { key: Filter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "hr", label: "HR Review" },
  { key: "ats", label: "ATS Check" },
  { key: "cover_letter", label: "Cover Letter" },
];

function formatRelative(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const minutes = Math.floor((Date.now() - date.getTime()) / 60000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (minutes < 1440) return `${Math.floor(minutes / 60)}h ago`;
  if (minutes < 10080) return `${Math.floor(minutes / 1440)}d ago`;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function formatFull(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function HistoryRow({
  record,
  resumeId,
  onDeleted,
}: {
  record: GenerationSummary;
  resumeId: number;
  onDeleted: (id: number) => void;
}) {
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState<Generation | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  const meta = KIND_META[record.kind];
  const Icon = meta.icon;

  const parsed = useMemo(() => {
    if (!detail || record.kind === "cover_letter") {
      return { chart: null, markdown: detail?.result ?? "", pending: false };
    }
    return parseAnalysisPayload<AtsChartData | HrChartData>(detail.result);
  }, [detail, record.kind]);

  const toggle = async () => {
    const next = !open;
    setOpen(next);
    if (next && !detail) {
      setLoading(true);
      setError(null);
      try {
        setDetail(await historyApi.get(record.id));
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load this record.");
      } finally {
        setLoading(false);
      }
    }
  };

  const remove = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Delete this record? This cannot be undone.")) return;
    try {
      await historyApi.remove(record.id);
      onDeleted(record.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete this record.");
    }
  };

  const downloadPdf = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!detail || (record.kind !== "hr" && record.kind !== "ats")) return;
    setDownloadingPdf(true);
    setError(null);
    try {
      await downloadAnalysisPdf(
        resumeId,
        record.kind,
        detail.job_description,
        detail.result,
        `${record.kind}-review.pdf`,
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to generate the PDF.");
    } finally {
      setDownloadingPdf(false);
    }
  };

  return (
    <div className={`card card-hover history-card${open ? " is-open" : ""}`}>
      <div className="history-card-head" onClick={toggle}>
        <span className={`history-kind-badge tone-${record.kind}`}>
          <Icon size={17} />
        </span>
        <div className="history-card-info">
          <div className="history-card-meta">
            <span className="history-kind-label">{meta.label}</span>
            <span className="history-dot" />
            <time
              className="history-time"
              dateTime={record.created_at}
              title={formatFull(record.created_at)}
            >
              {formatRelative(record.created_at)}
            </time>
          </div>
          <p className="history-job">{record.job_description}</p>
        </div>
        <button className="btn btn-sm btn-ghost history-delete" onClick={remove} title="Delete record">
          <TrashIcon size={14} />
        </button>
        <ChevronDownIcon
          size={16}
          className="history-chevron"
          style={{ transform: open ? "rotate(180deg)" : undefined }}
        />
      </div>
      {open && (
        <div className="history-card-body">
          {loading && <div className="skeleton skeleton-card" style={{ height: 120 }} />}
          {error && (
            <div className="error">
              <AlertIcon size={15} />
              {error}
            </div>
          )}
          {detail && (
            <div className="stack">
              {record.kind !== "cover_letter" && (
                <button
                  type="button"
                  className="btn btn-sm btn-ghost"
                  style={{ alignSelf: "flex-end" }}
                  onClick={downloadPdf}
                  disabled={downloadingPdf}
                >
                  {downloadingPdf ? <span className="spinner" /> : <DownloadIcon size={13} />}
                  {downloadingPdf ? "Generating…" : "Download PDF"}
                </button>
              )}
              {record.kind === "ats" && parsed.chart && (
                <AtsCharts data={parsed.chart as AtsChartData} />
              )}
              {record.kind === "hr" && parsed.chart && <HrCharts data={parsed.chart as HrChartData} />}
              <MarkdownStream text={parsed.markdown || detail.result} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function HistoryPage() {
  const { profileId, resumeId } = useParams();
  const pid = profileId ? Number(profileId) : null;
  const rid = Number(resumeId);
  const analysisPath =
    pid !== null ? `/profiles/${pid}/resumes/${rid}/analysis/hr` : `/quick-check/${rid}/analysis/hr`;

  const [resume, setResume] = useState<Resume | null>(null);
  const [records, setRecords] = useState<GenerationSummary[] | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    resumesApi.get(rid).then(setResume).catch(() => setResume(null));
  }, [rid]);

  useEffect(() => {
    setRecords(null);
    historyApi
      .list(rid, filter === "all" ? undefined : filter)
      .then(setRecords)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load history."));
  }, [rid, filter]);

  const onDeleted = (id: number) => {
    setRecords((prev) => prev?.filter((r) => r.id !== id) ?? prev);
  };

  return (
    <div className="stack-lg">
      <div>
        <Link className="breadcrumb" to={analysisPath}>
          <ArrowLeftIcon size={14} />
          Back to analysis
        </Link>
        <div className="page-head" style={{ marginTop: 8 }}>
          <div style={{ minWidth: 0 }}>
            <h2 style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <InboxIcon size={22} style={{ color: "var(--accent)", flexShrink: 0 }} />
              History
            </h2>
            <p className="subtitle">{resume ? resume.name : "Loading resume…"}</p>
          </div>
          <div className="seg-control">
            {FILTERS.map((f) => (
              <button
                key={f.key}
                type="button"
                className={filter === f.key ? "active" : ""}
                onClick={() => setFilter(f.key)}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && (
        <div className="error">
          <AlertIcon size={15} />
          {error}
        </div>
      )}

      {records === null ? (
        <SkeletonList count={3} height={90} />
      ) : records.length === 0 ? (
        <EmptyState
          icon={<InboxIcon size={24} />}
          title="No history yet"
          message="Run an HR review, ATS check, or cover letter to see it saved here."
        />
      ) : (
        <div className="stack">
          {records.map((r) => (
            <HistoryRow key={r.id} record={r} resumeId={rid} onDeleted={onDeleted} />
          ))}
        </div>
      )}
    </div>
  );
}
