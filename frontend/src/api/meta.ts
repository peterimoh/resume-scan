import { api } from "./client";
import type { FontMeta, TemplateMeta } from "../types/resume";

export const metaApi = {
  templates: () => api.get<Record<string, TemplateMeta>>("/api/meta/templates"),
  fonts: () => api.get<Record<string, FontMeta>>("/api/meta/fonts"),
};
