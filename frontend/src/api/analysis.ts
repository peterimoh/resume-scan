import { API_BASE_URL, ApiError, postAndDownloadFile } from "./client";

/**
 * Consume the backend's SSE-framed HR/ATS analysis stream.
 *
 * Native EventSource can't be used here: the request needs a JSON POST body
 * and the auth cookie, which EventSource doesn't support. Instead we read
 * the response body directly and parse the `data: "<json-string>"\n\n`
 * framing ourselves (each chunk is JSON-encoded so embedded newlines in the
 * markdown don't break event framing).
 */
export async function streamAnalysis(
  resumeId: number,
  mode: "hr" | "ats" | "cover-letter",
  jobDescription: string,
  onChunk: (text: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/resumes/${resumeId}/analysis/${mode}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ job_description: jobDescription }),
    signal,
  });
  if (!res.ok || !res.body) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // ignore
    }
    throw new ApiError(res.status, detail);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let sep;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const rawEvent = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);

      let eventType = "message";
      let dataLine: string | null = null;
      for (const line of rawEvent.split("\n")) {
        if (line.startsWith("event:")) eventType = line.slice(6).trim();
        else if (line.startsWith("data:")) dataLine = line.slice(5).trim();
      }
      if (eventType === "done") return;
      if (dataLine !== null) {
        try {
          onChunk(JSON.parse(dataLine) as string);
        } catch {
          // ignore malformed frame
        }
      }
    }
  }
}

/** Download a formatted PDF of a completed HR review or ATS check. */
export function downloadAnalysisPdf(
  resumeId: number,
  kind: "hr" | "ats",
  jobDescription: string,
  result: string,
  fallbackName: string,
): Promise<void> {
  return postAndDownloadFile(
    `/api/resumes/${resumeId}/analysis/pdf`,
    { kind, job_description: jobDescription, result },
    fallbackName,
  );
}
