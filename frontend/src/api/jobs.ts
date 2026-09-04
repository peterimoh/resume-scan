import { api } from "./client";
import type { Job, JobChannel, JobFilterOptions, JobListResponse, JobNotification, JobSubscription } from "../types/resume";

export interface JobBrowseFilters {
  q?: string;
  location?: string;
  job_type?: string;
  source?: string;
  /** Posted-at window, e.g. "24h", "3d", "7d", "30d". */
  posted_within?: string;
  page?: number;
  page_size?: number;
}

function toQueryString(filters: JobBrowseFilters): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null && value !== "") params.set(key, String(value));
  }
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export const jobsApi = {
  listSubscriptions: () => api.get<JobSubscription[]>("/api/job-subscriptions"),
  createSubscription: (keyword: string, channel: JobChannel, channelTarget: string) =>
    api.post<JobSubscription>("/api/job-subscriptions", {
      keyword,
      channel,
      channel_target: channelTarget,
    }),
  pauseSubscription: (id: number) => api.patch<JobSubscription>(`/api/job-subscriptions/${id}/pause`),
  resumeSubscription: (id: number) => api.patch<JobSubscription>(`/api/job-subscriptions/${id}/resume`),
  removeSubscription: (id: number) => api.delete<void>(`/api/job-subscriptions/${id}`),
  feed: () => api.get<JobNotification[]>("/api/jobs/feed"),
  browse: (filters: JobBrowseFilters) => api.get<JobListResponse>(`/api/jobs${toQueryString(filters)}`),
  filterOptions: () => api.get<JobFilterOptions>("/api/jobs/filter-options"),
  get: (jobId: number) => api.get<Job>(`/api/jobs/${jobId}`),
};
