import { useEffect, useState } from "react";
import { resumesApi } from "../api/resumes";
import { fetchImageObjectUrl } from "../api/client";

export function ResumeThumbnail({ resumeId, width = 96 }: { resumeId: number; width?: number }) {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    fetchImageObjectUrl(resumesApi.thumbnailUrl(resumeId))
      .then((u) => {
        if (cancelled) {
          URL.revokeObjectURL(u);
          return;
        }
        objectUrl = u;
        setUrl(u);
      })
      .catch(() => {
        /* no pdf yet, or fetch failed — just skip the thumbnail */
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [resumeId]);

  if (!url) return null;
  return <img src={url} alt="Resume preview" className="resume-thumb" style={{ width }} />;
}
