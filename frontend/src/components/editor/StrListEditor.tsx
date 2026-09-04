interface StrListEditorProps {
  title: string;
  items: string[];
  onChange: (items: string[]) => void;
  placeholder?: string;
  rows?: number;
}

export function StrListEditor({ title, items, onChange, placeholder, rows = 4 }: StrListEditorProps) {
  return (
    <div className="field">
      <label>{title}</label>
      <textarea
        rows={rows}
        value={items.join("\n")}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value.split("\n"))}
      />
      <div className="hint">One per line.</div>
    </div>
  );
}
