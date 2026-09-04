import { api } from "./client";
import type { Profile } from "../types/resume";

export const profilesApi = {
  list: () => api.get<Profile[]>("/api/profiles"),
  get: (id: number) => api.get<Profile>(`/api/profiles/${id}`),
  create: (name: string, headline?: string) =>
    api.post<Profile>("/api/profiles", { name, headline: headline || null }),
  update: (id: number, name: string, headline?: string) =>
    api.patch<Profile>(`/api/profiles/${id}`, { name, headline: headline || null }),
  remove: (id: number) => api.delete<void>(`/api/profiles/${id}`),
};
