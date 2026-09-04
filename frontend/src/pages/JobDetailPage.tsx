import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { jobsApi } from "../api/jobs";
import { ApiError } from "../api/client";
import type { Job } from "../types/resume";
import { EmptyState } from "../components/ui";
import { MarkdownStream } from "../components/MarkdownStream";
import { fullDate, postedLabel } from "../lib/dates";
import {
  AlertIcon,
  ArrowLeftIcon,
  DollarIcon,
  ExternalLinkIcon,
  InboxIcon,
  MapPinIcon,
} from "../components/icons";

function humanizeJobType(value: string): string {
  return value.replace(/[_-]+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

interface JobDetailLocationState {
  from?: string;
}

export function JobDetailPage() {
  const { jobId } = useParams();
  const location = useLocation();
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);

  const id = Number(jobId);

  useEffect(() => {
    setJob(null);
    setError(null);
    if (!Number.isInteger(id) || id <= 0) {
      setError("That job link doesn't look right.");
      return;
    }
    jobsApi
      .get(id)
      .then(setJob)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load this job."));
  }, [id]);

  const state = location.state as JobDetailLocationState | null;
  const backTo = state?.from?.startsWith("/jobs") ? state.from : "/jobs?tab=browse";

  return (
    <div className="stack-lg job-detail">
      <Link className="breadcrumb" to={backTo}>
        <ArrowLeftIcon size={14} /> Back to jobs
      </Link>

      {error ? (
        <EmptyState
          icon={<AlertIcon size={24} />}
          title="Couldn't load this job"
          message={error}
          action={
            <Link className="btn" to={backTo}>
              Back to jobs
            </Link>
          }
        />
      ) : job === null ? (
        <>
          <div className="skeleton skeleton-card job-head-skeleton" />
          <div className="skeleton skeleton-card" style={{ height: 320 }} />
        </>
      ) : (
        <>
          <header className="card job-detail-head">
            <div className="job-detail-title-row">
              <span className="job-logo job-logo-lg" aria-hidden="true">
                {(job.company?.trim() || job.source).slice(0, 2).toUpperCase()}
              </span>
              <div className="job-detail-title">
                <h2>
                  <a href={job.url} target="_blank" rel="noreferrer noopener" title="Open the original posting">
                    {job.title}
                  </a>
                </h2>
                <p className="job-detail-company">
                  {job.company || "Unknown company"} ·{" "}
                  <span title={`Source: ${job.source}`}>{job.source}</span>
                </p>
              </div>
            </div>
            <div className="meta-chips">
              {job.location && (
                <span className="meta-chip" title={job.location}>
                  <MapPinIcon size={11} /> <span className="meta-chip-text">{job.location}</span>
                </span>
              )}
              {job.job_type && <span className="meta-chip">{humanizeJobType(job.job_type)}</span>}
              {job.salary && (
                <span className="meta-chip" title={job.salary}>
                  <DollarIcon size={11} /> <span className="meta-chip-text">{job.salary}</span>
                </span>
              )}
              {job.posted_at && (
                <span className="meta-chip" title={fullDate(job.posted_at)}>
                  Posted {postedLabel(job.posted_at)}
                </span>
              )}
              {job.fetched_at && (
                <span className="meta-chip" title={fullDate(job.fetched_at)}>
                  Found {postedLabel(job.fetched_at)}
                </span>
              )}
            </div>
            <div className="job-detail-actions">
              <a
                className="btn btn-primary"
                href={job.url}
                target="_blank"
                rel="noreferrer noopener"
              >
                Open job posting <ExternalLinkIcon size={14} />
              </a>
            </div>
          </header>

          <section className="card job-detail-body">
            <h3 className="job-detail-section-title">
              <InboxIcon size={15} /> About this role
            </h3>
            {job.description ? (
              <MarkdownStream text={job.description} breaks />
            ) : (
              <p className="hint">
                No description was provided for this posting — use the button above to read it at
                the source.
              </p>
            )}
          </section>
        </>
      )}
    </div>
  );
}
