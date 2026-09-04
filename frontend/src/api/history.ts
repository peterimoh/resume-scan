import { api } from "./client";
import type { Generation, GenerationKind, GenerationSummary, HistoryEntry } from "../types/resume";

export const historyApi = {
  list: (resumeId: number, kind?: GenerationKind) =>
    api.get<GenerationSummary[]>(
      `/api/resumes/${resumeId}/history${kind ? `?kind=${kind}` : ""}`,
    ),
  listAll: (kind?: GenerationKind) =>
    api.get<HistoryEntry[]>(`/api/history${kind ? `?kind=${kind}` : ""}`),
  get: (generationId: number) => api.get<Generation>(`/api/history/${generationId}`),
  remove: (generationId: number) => api.delete<void>(`/api/history/${generationId}`),
};
