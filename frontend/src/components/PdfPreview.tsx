import { FileIcon } from "./icons";

interface Props {
  pages: string[];
  loading?: boolean;
  error?: string | null;
}

export function PdfPreview({ pages, loading, error }: Props) {
  if (error) return <div className="error">{error}</div>;
  if (pages.length === 0) {
    return (
      <div className="preview-frame">
        <FileIcon size={28} style={{ color: "var(--text-muted)", marginBottom: 8 }} />
        <p className="hint" style={{ margin: 0 }}>
          {loading ? "Rendering…" : "No preview yet."}
        </p>
      </div>
    );
  }
  return (
    <div>
      {loading && (
        <p className="hint" style={{ marginTop: 0 }}>
          Refreshing preview…
        </p>
      )}
      {pages.map((src, i) => (
        // eslint-disable-next-line react/no-array-index-key
        <img key={i} src={src} alt={`Page ${i + 1}`} className="preview-page" />
      ))}
    </div>
  );
}
