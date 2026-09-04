import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { resumesApi } from "../api/resumes";
import { downloadAnalysisPdf, streamAnalysis } from "../api/analysis";
import { ApiError } from "../api/client";
import { AtsCharts, HrCharts } from "../components/AnalysisCharts";
import { MarkdownStream } from "../components/MarkdownStream";
import { EmptyState } from "../components/ui";
import { parseAnalysisPayload, type AtsChartData, type HrChartData } from "../lib/analysisPayload";
import {
  AlertIcon,
  ArrowLeftIcon,
  CheckIcon,
  CopyIcon,
  DownloadIcon,
  FileIcon,
  InboxIcon,
  MailIcon,
  SparklesIcon,
  TargetIcon,
} from "../components/icons";
import type { Resume } from "../types/resume";

type AnalysisMode = "hr" | "ats" | "cover-letter";

interface ModeMeta {
  label: string;
  icon: typeof SparklesIcon;
  resultTitle: string;
  runLabel: string;
  runningLabel: string;
  emptyTitle: string;
  emptyMessage: string;
}

const MODES: Record<AnalysisMode, ModeMeta> = {
  hr: {
    label: "HR Review",
    icon: SparklesIcon,
    resultTitle: "HR review",
    runLabel: "Run HR review",
    runningLabel: "Reviewing",
    emptyTitle: "No HR review yet",
    emptyMessage:
      "Paste a job description and run the review — fit feedback and suggestions will stream in here.",
  },
  ats: {
    label: "ATS Check",
    icon: TargetIcon,
    resultTitle: "ATS report",
    runLabel: "Run ATS check",
    runningLabel: "Checking",
    emptyTitle: "No ATS report yet",
    emptyMessage:
      "Paste a job description and run the check — keyword gaps and fixes will stream in here.",
  },
  "cover-letter": {
    label: "Cover Letter",
    icon: MailIcon,
    resultTitle: "Cover letter draft",
    runLabel: "Generate cover letter",
    runningLabel: "Writing",
    emptyTitle: "No cover letter yet",
    emptyMessage:
      "Paste a job description and generate — a tailored letter will stream in here, ready to copy.",
  },
};

export function AnalysisPage() {
  const { profileId, resumeId, mode } = useParams();
  const pid = profileId ? Number(profileId) : null;
  const rid = Number(resumeId);
  const libraryPath = pid !== null ? `/profiles/${pid}/resumes` : "/quick-check";
  const libraryLabel = pid !== null ? "Resume library" : "Quick Check";
  const historyPath =
    pid !== null ? `/profiles/${pid}/resumes/${rid}/history` : `/quick-check/${rid}/history`;
  const modePath = (m: string) =>
    pid !== null ? `/profiles/${pid}/resumes/${rid}/analysis/${m}` : `/quick-check/${rid}/analysis/${m}`;
  const analysisMode: AnalysisMode =
    mode === "ats" ? "ats" : mode === "cover-letter" ? "cover-letter" : "hr";

  const [resume, setResume] = useState<Resume | null>(null);
  const [jobDescription, setJobDescription] = useState("");
  const [result, setResult] = useState("");
  const [running, setRunning] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    resumesApi.get(rid).then(setResume).catch(() => setResume(null));
    setResult("");
    setError(null);
    setCopied(false);
    return () => abortRef.current?.abort();
  }, [rid, analysisMode]);

  const run = async () => {
    if (!jobDescription.trim()) {
      setError("Paste a job description first.");
      return;
    }
    setRunning(true);
    setError(null);
    setResult("");
    setCopied(false);
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      let acc = "";
      await streamAnalysis(
        rid,
        analysisMode,
        jobDescription,
        (chunk) => {
          acc += chunk;
          setResult(acc);
        },
        controller.signal,
      );
      if (!acc.trim()) {
        setError("The model returned an empty response. Try again.");
      } else if (!isLetter) {
        const check = parseAnalysisPayload<AtsChartData | HrChartData>(acc);
        if (!check.chart && !check.markdown.trim()) {
          setError("The response was cut off before it finished. Try again.");
        }
      }
    } catch (err) {
      if (!(err instanceof DOMException && err.name === "AbortError")) {
        setError(err instanceof ApiError ? err.message : "Analysis failed.");
      }
    } finally {
      setRunning(false);
    }
  };

  const meta = MODES[analysisMode];
  const ModeIcon = meta.icon;
  const isLetter = analysisMode === "cover-letter";
  const wordCount = jobDescription.trim() ? jobDescription.trim().split(/\s+/).length : 0;

  const parsed = useMemo(
    () =>
      isLetter
        ? { chart: null, markdown: result, pending: false }
        : parseAnalysisPayload<AtsChartData | HrChartData>(result),
    [result, isLetter],
  );
  const displayText = isLetter ? result : parsed.markdown;
  const hasContent = isLetter ? result.trim().length > 0 : !!parsed.chart || displayText.trim().length > 0;

  const copyResult = async () => {
    try {
      await navigator.clipboard.writeText(displayText || result);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setError("Could not copy to clipboard.");
    }
  };

  const downloadPdf = async () => {
    if (analysisMode === "cover-letter") return;
    setDownloadingPdf(true);
    setError(null);
    try {
      await downloadAnalysisPdf(
        rid,
        analysisMode,
        jobDescription,
        result,
        `${analysisMode}-review.pdf`,
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to generate the PDF.");
    } finally {
      setDownloadingPdf(false);
    }
  };

  return (
    <div className="stack-lg">
      <div className="analysis-topbar">
        <Link className="breadcrumb" to={libraryPath}>
          <ArrowLeftIcon size={14} />
          {libraryLabel}
        </Link>
        <Link className="btn btn-sm btn-ghost" to={historyPath}>
          <InboxIcon size={14} /> History
        </Link>
      </div>

      <div className="analysis-heading">
        <span className="analysis-heading-icon">
          <ModeIcon size={20} />
        </span>
        <div style={{ minWidth: 0 }}>
          <h2 className="analysis-heading-title">{meta.label}</h2>
          <p className="subtitle">{resume ? resume.name : "Loading resume…"}</p>
        </div>
      </div>

      <nav className="seg-control analysis-modes" aria-label="Analysis mode">
        {(Object.keys(MODES) as AnalysisMode[]).map((m) => {
          const Icon = MODES[m].icon;
          return (
            <Link
              key={m}
              className={analysisMode === m ? "active" : ""}
              to={modePath(m)}
            >
              <Icon size={13} />
              {MODES[m].label}
            </Link>
          );
        })}
      </nav>

      <div className="analysis-layout">
        <div className="card analysis-input">
          <div className="analysis-input-head">
            <div className="card-title-text">
              <span className="card-icon">
                <FileIcon size={14} />
              </span>
              <label htmlFor="job">Job description</label>
            </div>
            {wordCount > 0 && (
              <span className="analysis-input-meta">
                {wordCount} word{wordCount === 1 ? "" : "s"}
              </span>
            )}
          </div>
          <textarea
            id="job"
            rows={12}
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            placeholder="Paste the job posting you're targeting…"
          />
          <button className="btn btn-primary btn-block" onClick={run} disabled={running}>
            {running ? (
              <>
                <span className="spinner" /> {meta.runningLabel}…
              </>
            ) : (
              <>
                <ModeIcon size={15} /> {meta.runLabel}
              </>
            )}
          </button>
          <p className="analysis-input-hint">
            {running
              ? "Takes 10–30 seconds — results stream in live."
              : "Compared against this resume only."}
          </p>
        </div>

        <div className="stack analysis-result-col">
          {error && (
            <div className="error">
              <AlertIcon size={15} />
              {error}
            </div>
          )}

          {hasContent ? (
            <div className="stack">
              {analysisMode === "ats" && parsed.chart && (
                <AtsCharts data={parsed.chart as AtsChartData} />
              )}
              {analysisMode === "hr" && parsed.chart && (
                <HrCharts data={parsed.chart as HrChartData} />
              )}
              <div className="card">
                <div className="card-title">
                  <h3 className="card-title-text">
                    <span className="card-icon">
                      <ModeIcon size={14} />
                    </span>
                    {meta.resultTitle}
                  </h3>
                  <div className="row" style={{ gap: 10, flex: "0 0 auto", alignItems: "center" }}>
                    {running && (
                      <span className="stream-indicator">
                        <span className="dot" />
                        <span className="dot" />
                        <span className="dot" />
                      </span>
                    )}
                    {!running && !isLetter && (
                      <button
                        type="button"
                        className="btn btn-sm btn-ghost"
                        onClick={downloadPdf}
                        disabled={downloadingPdf}
                      >
                        {downloadingPdf ? (
                          <span className="spinner" />
                        ) : (
                          <DownloadIcon size={13} />
                        )}
                        {downloadingPdf ? "Generating…" : "PDF"}
                      </button>
                    )}
                    {!running && (
                      <button
                        type="button"
                        className={copied ? "copy-btn copied" : "copy-btn"}
                        onClick={copyResult}
                      >
                        {copied ? <CheckIcon size={13} /> : <CopyIcon size={13} />}
                        {copied ? "Copied" : "Copy"}
                      </button>
                    )}
                  </div>
                </div>
                <MarkdownStream text={displayText} breaks={isLetter} letter={isLetter} />
              </div>
            </div>
          ) : running ? (
            <div className="empty-state analysis-warmup">
              <span className="stream-indicator">
                <span className="dot" />
                <span className="dot" />
                <span className="dot" />
              </span>
              <p>
                {meta.runningLabel} your resume against the job description — the first lines will
                appear in a moment.
              </p>
            </div>
          ) : (
            !error && (
              <EmptyState
                icon={<ModeIcon size={24} />}
                title={meta.emptyTitle}
                message={meta.emptyMessage}
              />
            )
          )}
        </div>
      </div>
    </div>
  );
}
