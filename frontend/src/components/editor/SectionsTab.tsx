import { DEFAULT_SECTION_LABELS, SECTION_KEYS, type ResumeData } from "../../types/resume";

interface Props {
  data: ResumeData;
  onChange: (patch: Partial<ResumeData>) => void;
}

export function SectionsTab({ data, onChange }: Props) {
  const reset = () => onChange({ sections: {}, section_labels: {} });

  return (
    <div className="card">
      <div className="card-title">
        <h3>Sections</h3>
        <button type="button" className="btn btn-sm btn-ghost" onClick={reset}>
          Reset
        </button>
      </div>
      <p className="hint" style={{ marginTop: -8, marginBottom: 8 }}>
        Show or hide a section, and optionally override its heading.
      </p>
      <div>
        {SECTION_KEYS.map((key) => {
          const visible = data.sections[key] ?? true;
          const label = data.section_labels[key] ?? DEFAULT_SECTION_LABELS[key];
          return (
            <div className="section-toggle-row" key={key}>
              <label className="inline">
                <input
                  type="checkbox"
                  checked={visible}
                  onChange={(e) => onChange({ sections: { ...data.sections, [key]: e.target.checked } })}
                />
                {DEFAULT_SECTION_LABELS[key]}
              </label>
              <input
                type="text"
                value={label}
                aria-label={`Heading for ${DEFAULT_SECTION_LABELS[key]}`}
                onChange={(e) =>
                  onChange({ section_labels: { ...data.section_labels, [key]: e.target.value } })
                }
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
