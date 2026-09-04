import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { jobsApi } from "../api/jobs";
import { telegramApi, type TelegramStatus } from "../api/telegram";
import { ApiError } from "../api/client";
import type { Job, JobChannel, JobFilterOptions, JobNotification, JobSubscription } from "../types/resume";
import { EmptyState, SkeletonList } from "../components/ui";
import { postedLabel, relativeDate } from "../lib/dates";
import {
  AlertIcon,
  ArrowLeftIcon,
  ArrowRightIcon,
  BellIcon,
  CheckIcon,
  DollarIcon,
  ExternalLinkIcon,
  MailIcon,
  MapPinIcon,
  PauseIcon,
  PlayIcon,
  PlusIcon,
  SearchIcon,
  TelegramIcon,
  TrashIcon,
  WhatsappIcon,
  XIcon,
} from "../components/icons";

const CHANNEL_META: Record<
  JobChannel,
  { label: string; icon: typeof MailIcon; placeholder: string; hint: string }
> = {
  email: {
    label: "Email",
    icon: MailIcon,
    placeholder: "you@example.com",
    hint: "Job matches are sent to this address.",
  },
  telegram: {
    label: "Telegram",
    icon: TelegramIcon,
    placeholder: "Your Telegram chat ID",
    hint: "Message our bot first — it replies with the chat ID to paste here.",
  },
  whatsapp: {
    label: "WhatsApp",
    icon: WhatsappIcon,
    placeholder: "+1 555 123 4567",
    hint: "Include the country code.",
  },
};

type Tab = "feed" | "browse" | "subscriptions";

const TABS: Tab[] = ["feed", "browse", "subscriptions"];

export function JobBoardPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();

  const tabParam = searchParams.get("tab");
  const tab: Tab = TABS.includes(tabParam as Tab) ? (tabParam as Tab) : "feed";

  const selectTab = (next: Tab) => {
    if (next === tab) return;
    const params = new URLSearchParams(searchParams);
    if (next === "feed") params.delete("tab");
    else params.set("tab", next);
    setSearchParams(params);
  };

  const [feed, setFeed] = useState<JobNotification[] | null>(null);
  const [subscriptions, setSubscriptions] = useState<JobSubscription[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  // Opening a job navigates to its own page; the current tab + filters ride
  // along in location.state so "Back to jobs" restores the exact view.
  const openJob = (job: Job) => {
    navigate(`/jobs/${job.id}`, { state: { from: `/jobs${location.search}` } });
  };

  const loadFeed = () => {
    jobsApi
      .feed()
      .then(setFeed)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load your job feed."));
  };

  const loadSubscriptions = () => {
    jobsApi
      .listSubscriptions()
      .then(setSubscriptions)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load subscriptions."));
  };

  useEffect(() => {
    loadFeed();
    loadSubscriptions();
  }, []);

  const togglePause = async (sub: JobSubscription) => {
    setError(null);
    try {
      const updated = sub.active
        ? await jobsApi.pauseSubscription(sub.id)
        : await jobsApi.resumeSubscription(sub.id);
      setSubscriptions((prev) => prev?.map((s) => (s.id === sub.id ? updated : s)) ?? prev);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update the subscription.");
    }
  };

  const removeSubscription = async (sub: JobSubscription) => {
    if (!confirm(`Stop tracking "${sub.keyword}"?`)) return;
    setError(null);
    try {
      await jobsApi.removeSubscription(sub.id);
      setSubscriptions((prev) => prev?.filter((s) => s.id !== sub.id) ?? prev);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete the subscription.");
    }
  };

  const activeCount = subscriptions?.filter((s) => s.active).length ?? 0;

  return (
    <div className="stack-lg">
      <div className="page-head">
        <div>
          <h2 style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <BellIcon size={22} style={{ color: "var(--accent)", flexShrink: 0 }} />
            Job Board
          </h2>
          <p className="subtitle">
            Track job titles you care about and get notified the moment a new match comes in, or
            browse everything we've pulled in — checked every 4 hours across Remotive, Arbeitnow,
            RemoteOK, and Jooble (local markets, including Nigeria).
          </p>
        </div>
        <div className="seg-control">
          <button type="button" className={tab === "feed" ? "active" : ""} onClick={() => selectTab("feed")}>
            Feed
          </button>
          <button type="button" className={tab === "browse" ? "active" : ""} onClick={() => selectTab("browse")}>
            Browse all
          </button>
          <button
            type="button"
            className={tab === "subscriptions" ? "active" : ""}
            onClick={() => selectTab("subscriptions")}
          >
            Subscriptions{subscriptions ? ` (${activeCount})` : ""}
          </button>
        </div>
      </div>

      {error && (
        <div className="error">
          <AlertIcon size={15} />
          {error}
        </div>
      )}

      {tab === "feed" && (
        <JobFeed feed={feed} onManage={() => selectTab("subscriptions")} onSelect={openJob} />
      )}
      {tab === "browse" && <JobBrowse onSelect={openJob} />}
      {tab === "subscriptions" && (
        <div className="stack">
          <div className="page-head" style={{ marginBottom: 0 }}>
            <p className="hint" style={{ margin: 0 }}>
              Add a job title or keyword, then pick where you want to hear about matches.
            </p>
            <button className="btn btn-primary" onClick={() => setModalOpen(true)}>
              <PlusIcon size={15} /> New subscription
            </button>
          </div>
          <SubscriptionList
            subscriptions={subscriptions}
            onTogglePause={togglePause}
            onRemove={removeSubscription}
            onCreate={() => setModalOpen(true)}
          />
        </div>
      )}

      {modalOpen && (
        <SubscriptionModal
          onClose={() => setModalOpen(false)}
          onCreated={() => {
            setModalOpen(false);
            loadSubscriptions();
          }}
        />
      )}
    </div>
  );
}

function JobFeed({
  feed,
  onManage,
  onSelect,
}: {
  feed: JobNotification[] | null;
  onManage: () => void;
  onSelect: (job: Job) => void;
}) {
  if (feed === null) return <SkeletonList count={3} height={110} />;
  if (feed.length === 0) {
    return (
      <EmptyState
        icon={<BellIcon size={24} />}
        title="No matches yet"
        message="Once you add a subscription, matching jobs will start showing up here after the next scan."
        action={
          <button className="btn btn-primary" onClick={onManage}>
            <PlusIcon size={15} /> Add a subscription
          </button>
        }
      />
    );
  }
  return (
    <div className="stack">
      {feed.map((job) => {
        const ChannelIcon = CHANNEL_META[job.channel].icon;
        return (
          <JobCard
            key={job.notification_id}
            job={job}
            onSelect={onSelect}
            footer={
              <span className="meta-chip" title={`Sent via ${CHANNEL_META[job.channel].label}`}>
                <ChannelIcon size={11} /> {relativeDate(job.sent_at)}
              </span>
            }
          />
        );
      })}
    </div>
  );
}

function companyInitials(job: Job): string {
  const name = job.company?.trim() || job.source;
  return name.slice(0, 2).toUpperCase();
}

function humanizeJobType(value: string): string {
  return value.replace(/[_-]+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function JobCard({
  job,
  onSelect,
  footer,
}: {
  job: Job;
  onSelect: (job: Job) => void;
  footer?: ReactNode;
}) {
  return (
    <article
      className="job-card"
      role="button"
      tabIndex={0}
      onClick={() => onSelect(job)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") onSelect(job);
      }}
    >
      <div className="job-card-top">
        <span className="job-logo" aria-hidden="true">
          {companyInitials(job)}
        </span>
        <div className="job-card-head">
          <h3 className="job-card-title" title={job.title}>
            {job.title}
          </h3>
          <p className="job-card-company">
            {job.company || "Unknown company"} · <span title={`Source: ${job.source}`}>{job.source}</span>
          </p>
        </div>
        <a
          className="btn btn-sm btn-ghost job-card-open"
          href={job.url}
          target="_blank"
          rel="noreferrer noopener"
          aria-label={`Open ${job.title} on ${job.source}`}
          onClick={(e) => e.stopPropagation()}
        >
          Open <ExternalLinkIcon size={13} />
        </a>
      </div>
      <div className="job-card-chips">
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
        {job.posted_at && <span className="meta-chip">{postedLabel(job.posted_at)}</span>}
        {footer}
      </div>
    </article>
  );
}

const PAGE_SIZE = 20;

const SEARCH_DEBOUNCE_MS = 350;

function pageFromParams(params: URLSearchParams): number {
  const raw = Number.parseInt(params.get("page") ?? "1", 10);
  return Number.isFinite(raw) && raw > 0 ? raw : 1;
}

function pageWindow(current: number, total: number): (number | "gap")[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const items: (number | "gap")[] = [1];
  const left = Math.max(2, current - 1);
  const right = Math.min(total - 1, current + 1);
  if (left > 2) items.push("gap");
  for (let p = left; p <= right; p++) items.push(p);
  if (right < total - 1) items.push("gap");
  items.push(total);
  return items;
}

function JobBrowse({ onSelect }: { onSelect: (job: Job) => void }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const q = searchParams.get("q") ?? "";
  const location = searchParams.get("location") ?? "";
  const jobType = searchParams.get("type") ?? "";
  const source = searchParams.get("source") ?? "";
  const posted = searchParams.get("posted") ?? "";
  const page = pageFromParams(searchParams);

  const [qInput, setQInput] = useState(q);
  const [lastUrlQ, setLastUrlQ] = useState(q);
  const [filterOptions, setFilterOptions] = useState<JobFilterOptions | null>(null);
  const [items, setItems] = useState<Job[] | null>(null);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Keep the text input in sync when the URL changes (back/forward, clear all).
  if (lastUrlQ !== q) {
    setLastUrlQ(q);
    setQInput(q);
  }

  const hasFilters = Boolean(q || location || jobType || source || posted);

  const updateParams = useCallback(
    (updates: Record<string, string | null>, replace = false) => {
      const next = new URLSearchParams(searchParams);
      for (const [key, value] of Object.entries(updates)) {
        if (value) next.set(key, value);
        else next.delete(key);
      }
      setSearchParams(next, { replace });
    },
    [searchParams, setSearchParams],
  );

  const goToPage = (next: number) => {
    updateParams({ page: String(next) });
    window.scrollTo({ top: 0 });
  };

  const clearFilters = () => {
    setQInput("");
    updateParams({ q: null, location: null, type: null, source: null, posted: null, page: null });
  };

  useEffect(() => {
    jobsApi
      .filterOptions()
      .then(setFilterOptions)
      .catch(() => setFilterOptions({ job_types: [], sources: [], locations: [] }));
  }, []);

  // Debounce free-text keyword input so we don't fire a request per keystroke.
  useEffect(() => {
    const timer = setTimeout(() => {
      const next = qInput.trim();
      if (next !== q) updateParams({ q: next || null, page: null }, true);
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [qInput, q, updateParams]);

  useEffect(() => {
    setItems(null);
    jobsApi
      .browse({
        q,
        location,
        job_type: jobType,
        source,
        posted_within: posted || undefined,
        page,
        page_size: PAGE_SIZE,
      })
      .then((res) => {
        setItems(res.items);
        setTotal(res.total);
        // Clamp an out-of-range page (e.g. after filters narrowed the results).
        const maxPage = Math.max(1, Math.ceil(res.total / PAGE_SIZE));
        if (page > maxPage) updateParams({ page: String(maxPage) });
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load jobs."));
  }, [q, location, jobType, source, posted, page, updateParams]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="stack">
      <div className="browse-toolbar-wrap">
        <div className="browse-toolbar" role="search">
          <div className="browse-search">
            <SearchIcon size={15} />
            <label htmlFor="browse-q" className="sr-only">
              Keyword
            </label>
            <input
              id="browse-q"
              type="text"
              placeholder="Search title, company, or keyword"
              value={qInput}
              onChange={(e) => setQInput(e.target.value)}
            />
          </div>
          <label htmlFor="browse-location" className="sr-only">
            Location
          </label>
          <select
            id="browse-location"
            className="browse-select"
            value={location}
            onChange={(e) => updateParams({ location: e.target.value || null, page: null })}
          >
            <option value="">Any location</option>
            {filterOptions?.locations.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
          <label htmlFor="browse-type" className="sr-only">
            Job type
          </label>
          <select
            id="browse-type"
            className="browse-select"
            value={jobType}
            onChange={(e) => updateParams({ type: e.target.value || null, page: null })}
          >
            <option value="">Any type</option>
            {filterOptions?.job_types.map((t) => (
              <option key={t} value={t}>
                {humanizeJobType(t)}
              </option>
            ))}
          </select>
          <label htmlFor="browse-source" className="sr-only">
            Source
          </label>
          <select
            id="browse-source"
            className="browse-select"
            value={source}
            onChange={(e) => updateParams({ source: e.target.value || null, page: null })}
          >
            <option value="">Any source</option>
            {filterOptions?.sources.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <label htmlFor="browse-posted" className="sr-only">
            Posted within
          </label>
          <select
            id="browse-posted"
            className="browse-select"
            value={posted}
            onChange={(e) => updateParams({ posted: e.target.value || null, page: null })}
          >
            <option value="">Any time</option>
            <option value="24h">Past 24 hours</option>
            <option value="3d">Past 3 days</option>
            <option value="7d">Past week</option>
            <option value="30d">Past month</option>
          </select>
          {hasFilters && (
            <button type="button" className="btn btn-sm btn-ghost browse-clear" onClick={clearFilters}>
              <XIcon size={13} /> Clear
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="error">
          <AlertIcon size={15} />
          {error}
        </div>
      )}

      {items === null ? (
        <div className="job-grid">
          {Array.from({ length: 6 }, (_, i) => (
            <div key={i} className="skeleton skeleton-card job-skeleton" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={<SearchIcon size={24} />}
          title="No jobs match those filters"
          message="Try loosening a filter, or check back after the next 4-hour scan."
          action={
            hasFilters ? (
              <button type="button" className="btn" onClick={clearFilters}>
                <XIcon size={14} /> Clear filters
              </button>
            ) : undefined
          }
        />
      ) : (
        <>
          <div className="job-grid">
            {items.map((job) => (
              <JobCard key={job.id} job={job} onSelect={onSelect} />
            ))}
          </div>
          <div className="browse-footer">
            <p className="hint" style={{ margin: 0 }}>
              {total} job{total === 1 ? "" : "s"} · page {page} of {totalPages}
            </p>
            <div className="pagination">
              <button
                type="button"
                className="page-btn"
                disabled={page <= 1}
                onClick={() => goToPage(page - 1)}
                aria-label="Previous page"
              >
                <ArrowLeftIcon size={13} />
              </button>
              {pageWindow(page, totalPages).map((p, i) =>
                p === "gap" ? (
                  <span key={`gap-${i}`} className="page-gap">
                    …
                  </span>
                ) : (
                  <button
                    type="button"
                    key={p}
                    className={p === page ? "page-btn active" : "page-btn"}
                    aria-current={p === page ? "page" : undefined}
                    onClick={() => goToPage(p)}
                  >
                    {p}
                  </button>
                ),
              )}
              <button
                type="button"
                className="page-btn"
                disabled={page >= totalPages}
                onClick={() => goToPage(page + 1)}
                aria-label="Next page"
              >
                <ArrowRightIcon size={13} />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function SubscriptionList({
  subscriptions,
  onTogglePause,
  onRemove,
  onCreate,
}: {
  subscriptions: JobSubscription[] | null;
  onTogglePause: (sub: JobSubscription) => void;
  onRemove: (sub: JobSubscription) => void;
  onCreate: () => void;
}) {
  if (subscriptions === null) return <SkeletonList count={2} height={70} />;
  if (subscriptions.length === 0) {
    return (
      <EmptyState
        icon={<BellIcon size={24} />}
        title="No subscriptions yet"
        message="Add the job titles or keywords you're looking for, and pick a channel to get notified on."
        action={
          <button className="btn btn-primary" onClick={onCreate}>
            <PlusIcon size={15} /> Create your first subscription
          </button>
        }
      />
    );
  }
  return (
    <div className="stack">
      {subscriptions.map((sub) => {
        const meta = CHANNEL_META[sub.channel];
        const Icon = meta.icon;
        return (
          <div className="card list-item" key={sub.id}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
              <div>
                <h3 style={{ margin: "0 0 4px" }}>{sub.keyword}</h3>
                <p className="hint" style={{ margin: 0, display: "flex", alignItems: "center", gap: 6 }}>
                  <Icon size={13} /> {meta.label} · {sub.channel_target}
                  {!sub.active && <span className="badge">Paused</span>}
                </p>
              </div>
              <div className="btn-row">
                <button
                  type="button"
                  className="btn btn-sm btn-ghost"
                  onClick={() => onTogglePause(sub)}
                  title={sub.active ? "Pause notifications" : "Resume notifications"}
                >
                  {sub.active ? <PauseIcon size={14} /> : <PlayIcon size={14} />}
                  {sub.active ? "Pause" : "Resume"}
                </button>
                <button
                  type="button"
                  className="btn btn-sm btn-ghost"
                  onClick={() => onRemove(sub)}
                  title="Delete subscription"
                >
                  <TrashIcon size={14} />
                </button>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function SubscriptionModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [keyword, setKeyword] = useState("");
  const [channel, setChannel] = useState<JobChannel>("email");
  const [channelTarget, setChannelTarget] = useState("");
  const [telegramStatus, setTelegramStatus] = useState<TelegramStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    telegramApi
      .status()
      .then((s) => {
        setTelegramStatus(s);
        if (s.linked && s.chat_id) setChannelTarget((prev) => prev || s.chat_id!);
      })
      .catch(() => setTelegramStatus({ linked: false, chat_id: null, username: null }));
  }, []);

  useEffect(() => {
    if (channel === "telegram") {
      setChannelTarget(telegramStatus?.linked ? telegramStatus.chat_id ?? "" : "");
    } else {
      setChannelTarget("");
    }
  }, [channel, telegramStatus]);

  const submit = async () => {
    const trimmedKeyword = keyword.trim();
    const trimmedTarget = channelTarget.trim();
    if (!trimmedKeyword) {
      setError("Please enter a job title or keyword to track.");
      return;
    }
    if (channel === "telegram" && !telegramStatus?.linked) {
      setError("Connect your Telegram account first.");
      return;
    }
    if (!trimmedTarget) {
      setError(`Please enter a ${CHANNEL_META[channel].label.toLowerCase()} destination.`);
      return;
    }
    setError(null);
    setBusy(true);
    try {
      await jobsApi.createSubscription(trimmedKeyword, channel, trimmedTarget);
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
      setBusy(false);
    }
  };

  return (
    <div
      className="modal-overlay"
      ref={overlayRef}
      onMouseDown={(e) => {
        if (e.target === overlayRef.current) onClose();
      }}
    >
      <div className="modal" role="dialog" aria-modal="true" aria-label="New job subscription">
        <div className="modal-head">
          <h3>New subscription</h3>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close">
            <XIcon size={16} />
          </button>
        </div>
        <form
          className="stack"
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
        >
          {error && (
            <div className="error">
              <AlertIcon size={15} />
              {error}
            </div>
          )}
          <div className="field">
            <label htmlFor="sub-keyword">Job title or keyword</label>
            <input
              id="sub-keyword"
              type="text"
              autoFocus
              required
              placeholder="e.g. backend engineer"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
            />
          </div>
          <div>
            <label>Notify me on</label>
            <div className="radio-group">
              {(Object.keys(CHANNEL_META) as JobChannel[]).map((key) => {
                const meta = CHANNEL_META[key];
                const Icon = meta.icon;
                return (
                  <label key={key} className={`radio-option${channel === key ? " selected" : ""}`}>
                    <input
                      type="radio"
                      name="channel"
                      value={key}
                      checked={channel === key}
                      onChange={() => setChannel(key)}
                    />
                    <span>
                      <strong style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <Icon size={14} /> {meta.label}
                      </strong>
                    </span>
                  </label>
                );
              })}
            </div>
          </div>
          {channel === "telegram" ? (
            <TelegramConnectField status={telegramStatus} onStatusChange={setTelegramStatus} />
          ) : (
            <div className="field">
              <label htmlFor="sub-target">{CHANNEL_META[channel].label} destination</label>
              <input
                id="sub-target"
                type={channel === "email" ? "email" : "text"}
                required
                placeholder={CHANNEL_META[channel].placeholder}
                value={channelTarget}
                onChange={(e) => setChannelTarget(e.target.value)}
              />
              <p className="hint">{CHANNEL_META[channel].hint}</p>
            </div>
          )}
          <div className="modal-actions">
            <button type="button" className="btn" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={busy}>
              {busy ? (
                <>
                  <span className="spinner" /> Creating…
                </>
              ) : (
                "Create subscription"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function TelegramConnectField({
  status,
  onStatusChange,
}: {
  status: TelegramStatus | null;
  onStatusChange: (s: TelegramStatus) => void;
}) {
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const attemptsRef = useRef(0);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    setConnecting(false);
  };

  const startConnect = async () => {
    setError(null);
    try {
      const { deep_link } = await telegramApi.createConnectToken();
      window.open(deep_link, "_blank", "noopener,noreferrer");
      setConnecting(true);
      attemptsRef.current = 0;
      pollRef.current = setInterval(async () => {
        attemptsRef.current += 1;
        try {
          const s = await telegramApi.status();
          if (s.linked) {
            onStatusChange(s);
            stopPolling();
            return;
          }
        } catch {
          // ignore transient errors while polling — the next tick retries
        }
        if (attemptsRef.current >= 24) {
          stopPolling();
          setError("Didn't see a connection yet — try again, or check you tapped Start in Telegram.");
        }
      }, 2500);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to start the Telegram connection.");
    }
  };

  const disconnect = async () => {
    setError(null);
    try {
      await telegramApi.unlink();
      onStatusChange({ linked: false, chat_id: null, username: null });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to disconnect Telegram.");
    }
  };

  return (
    <div className="field">
      <label>Telegram</label>
      {status === null ? (
        <p className="hint">Checking connection…</p>
      ) : status.linked ? (
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span className="meta-chip">
            <CheckIcon size={11} /> Connected{status.username ? ` as @${status.username}` : ""}
          </span>
          <button type="button" className="btn btn-sm btn-ghost" onClick={disconnect}>
            Disconnect
          </button>
        </div>
      ) : (
        <div>
          <button type="button" className="btn btn-soft" onClick={startConnect} disabled={connecting}>
            {connecting ? (
              <>
                <span className="spinner" /> Waiting for you in Telegram…
              </>
            ) : (
              <>
                <TelegramIcon size={14} /> Connect Telegram
              </>
            )}
          </button>
          <p className="hint">Opens Telegram — tap Start there, then come back here.</p>
        </div>
      )}
      {error && (
        <div className="error" style={{ marginTop: 8 }}>
          <AlertIcon size={15} />
          {error}
        </div>
      )}
    </div>
  );
}
