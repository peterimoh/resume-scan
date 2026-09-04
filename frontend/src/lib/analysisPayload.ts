// The HR/ATS analysis stream leads with a fenced ```json block of structured
// metrics (see backend/app/llm.py) followed by the markdown report. This
// splits the two apart as the stream arrives, so chart data becomes
// available the moment the fence closes and the markdown viewer never sees
// the raw JSON text.

export interface AtsChartData {
  match_score: number;
  must_have: { matched: number; total: number };
  nice_to_have: { matched: number; total: number };
  missing_keywords: { term: string; priority: "must_have" | "nice_to_have" }[];
  sections_present: string[];
  sections_missing: string[];
}

export interface HrChartData {
  verdict: string;
  fit_score: number;
  standout_count: number;
  weakness_count: number;
  achievements: { quantified: number; unquantified: number };
  missing_requirements_count: number;
  scrutiny_flags: number;
}

interface ParsedPayload<T> {
  /** Parsed chart data, once the leading JSON fence has closed and parsed cleanly. */
  chart: T | null;
  /** The markdown report, with the leading JSON fence stripped. */
  markdown: string;
  /** True while the leading fence has opened but not yet closed. */
  pending: boolean;
}

const FENCE_RE = /^\s*```(?:json)?[ \t]*\r?\n([\s\S]*?)\r?\n```[ \t]*\r?\n?/;

export function parseAnalysisPayload<T>(raw: string): ParsedPayload<T> {
  if (!/^\s*```/.test(raw)) {
    return { chart: null, markdown: raw, pending: false };
  }
  const match = raw.match(FENCE_RE);
  if (!match) {
    // Fence opened but hasn't closed yet — hide it rather than flashing raw JSON.
    return { chart: null, markdown: "", pending: true };
  }
  const rest = raw.slice(match[0].length);
  try {
    return { chart: JSON.parse(match[1]) as T, markdown: rest, pending: false };
  } catch {
    return { chart: null, markdown: rest, pending: false };
  }
}
