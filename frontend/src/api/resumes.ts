import { API_BASE_URL, ApiError, api, downloadFile } from "./client";
import type { Resume, ResumeData, ResumeSummary } from "../types/resume";

export interface ResumeSaveBody {
  name?: string | null;
  template: string;
  font: string;
  data: ResumeData;
}

export const resumesApi = {
  list: (profileId: number) => api.get<ResumeSummary[]>(`/api/profiles/${profileId}/resumes`),
  get: (id: number) => api.get<Resume>(`/api/resumes/${id}`),
  create: (profileId: number, body: ResumeSaveBody) =>
    api.post<Resume>(`/api/profiles/${profileId}/resumes`, body),
  update: (id: number, body: ResumeSaveBody) => api.put<Resume>(`/api/resumes/${id}`, body),
  remove: (id: number) => api.delete<void>(`/api/resumes/${id}`),
  duplicate: (id: number) => api.post<Resume>(`/api/resumes/${id}/duplicate`),
  generatePdf: (id: number) => api.post<Resume>(`/api/resumes/${id}/pdf`),
  downloadPdf: (id: number, suggestedName: string) =>
    downloadFile(`/api/resumes/${id}/pdf`, `${suggestedName}.pdf`),
  downloadJson: (id: number, suggestedName: string) =>
    downloadFile(`/api/resumes/${id}/json`, `${suggestedName}.json`),
  thumbnailUrl: (id: number) => `/api/resumes/${id}/thumbnail`,
  preview: (template: string, font: string, data: ResumeData) =>
    api.post<{ pages: string[] }>("/api/resumes/preview", { template, font, data }),
  // Quick Check: profile-less scans, uploaded straight from a PDF.
  listQuick: () => api.get<ResumeSummary[]>("/api/quick-resumes"),
  uploadQuick: async (file: File): Promise<Resume> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE_URL}/api/quick-resumes`, {
      method: "POST",
      credentials: "include",
      body: form,
    });
    if (!res.ok) {
      let message = `Request failed (${res.status})`;
      try {
        const body = await res.json();
        if (typeof body?.detail === "string") message = body.detail;
      } catch {
        // fall through to the generic message
      }
      throw new ApiError(res.status, message);
    }
    return (await res.json()) as Resume;
  },
};
