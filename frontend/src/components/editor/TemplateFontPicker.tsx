import type { FontMeta, TemplateMeta } from "../../types/resume";

interface Props {
  templates: Record<string, TemplateMeta>;
  fonts: Record<string, FontMeta>;
  template: string;
  font: string;
  onTemplateChange: (t: string) => void;
  onFontChange: (f: string) => void;
}

export function TemplateFontPicker({ templates, fonts, template, font, onTemplateChange, onFontChange }: Props) {
  const missingFonts = Object.entries(fonts).filter(([, meta]) => !meta.available);

  return (
    <div className="stack">
      <div>
        <label>Template</label>
        <div className="radio-group">
          {Object.entries(templates).map(([key, meta]) => (
            <label
              key={key}
              className={`radio-option${template === key ? " selected" : ""}`}
            >
              <input
                type="radio"
                name="template"
                value={key}
                checked={template === key}
                onChange={() => onTemplateChange(key)}
              />
              <span>
                <strong>{meta.label}</strong>
                <div className="hint">{meta.description}</div>
              </span>
            </label>
          ))}
        </div>
      </div>

      <div>
        <label>Font</label>
        <div className="radio-group">
          {Object.entries(fonts)
            .filter(([, meta]) => meta.available)
            .map(([key, meta]) => (
              <label key={key} className={`radio-option${font === key ? " selected" : ""}`}>
                <input
                  type="radio"
                  name="font"
                  value={key}
                  checked={font === key}
                  onChange={() => onFontChange(key)}
                />
                <span>{meta.label}</span>
              </label>
            ))}
        </div>
        {missingFonts.length > 0 && (
          <p className="hint">
            Not installed on the server: {missingFonts.map(([, m]) => m.label).join(", ")}
          </p>
        )}
      </div>
    </div>
  );
}
