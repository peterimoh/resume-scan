import ReactMarkdown from "react-markdown";
import remarkBreaks from "remark-breaks";
import remarkGfm from "remark-gfm";

interface MarkdownStreamProps {
  text: string;
  /** Render single newlines as line breaks (for prose like cover letters). */
  breaks?: boolean;
  /** Use the letter (paper) presentation instead of report styling. */
  letter?: boolean;
}

export function MarkdownStream({ text, breaks = false, letter = false }: MarkdownStreamProps) {
  return (
    <div className={letter ? "markdown-stream letter-stream" : "markdown-stream"}>
      <ReactMarkdown remarkPlugins={breaks ? [remarkGfm, remarkBreaks] : [remarkGfm]}>
        {text}
      </ReactMarkdown>
    </div>
  );
}
