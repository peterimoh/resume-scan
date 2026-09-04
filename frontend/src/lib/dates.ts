import { format, formatDistanceToNowStrict, parseISO } from "date-fns";

function toDate(value: string): Date | null {
  const date = parseISO(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** "3 days ago" style label, falling back to the raw string when unparsable. */
export function relativeDate(value: string): string {
  const date = toDate(value);
  if (!date) return value;
  return formatDistanceToNowStrict(date, { addSuffix: true });
}

/** Short absolute date, e.g. "4 Sep 2026". */
export function shortDate(value: string): string {
  const date = toDate(value);
  if (!date) return value;
  return format(date, "d MMM yyyy");
}

/** Card-friendly posted label: relative for recent posts, absolute once old. */
export function postedLabel(value: string): string {
  const date = toDate(value);
  if (!date) return value;
  const ageDays = (Date.now() - date.getTime()) / 86_400_000;
  return ageDays <= 30 ? relativeDate(value) : shortDate(value);
}

/** Full date + time for detail views, e.g. "Fri, 4 Sep 2026 at 14:05". */
export function fullDate(value: string): string {
  const date = toDate(value);
  if (!date) return value;
  return format(date, "EEE, d MMM yyyy 'at' HH:mm");
}
