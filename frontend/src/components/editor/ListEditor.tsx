import type { ReactNode } from "react";
import { PlusIcon, XIcon } from "../icons";

interface ListEditorProps<T> {
  title: string;
  items: T[];
  blank: () => T;
  onChange: (items: T[]) => void;
  renderItem: (item: T, update: (patch: Partial<T>) => void) => ReactNode;
}

export function ListEditor<T>({ title, items, blank, onChange, renderItem }: ListEditorProps<T>) {
  const updateAt = (i: number, patch: Partial<T>) => {
    const next = items.slice();
    next[i] = { ...next[i], ...patch };
    onChange(next);
  };
  const removeAt = (i: number) => onChange(items.filter((_, idx) => idx !== i));
  const add = () => onChange([...items, blank()]);

  return (
    <div className="stack">
      <div className="list-editor-head">
        <h3>{title}</h3>
        <span className="badge">{items.length}</span>
        <button
          type="button"
          className="btn btn-sm"
          style={{ marginLeft: "auto" }}
          onClick={add}
        >
          <PlusIcon size={14} /> Add
        </button>
      </div>
      {items.length === 0 ? (
        <p className="hint" style={{ margin: 0 }}>
          Nothing here yet — add your first entry below.
        </p>
      ) : (
        items.map((item, i) => (
          // Index as key is fine here: these are plain form entries with no
          // identity beyond position, and edits are controlled-input driven.
          // eslint-disable-next-line react/no-array-index-key
          <div className="list-item" key={i}>
            <button
              type="button"
              className="icon-btn icon-btn-danger remove-btn"
              onClick={() => removeAt(i)}
              title="Remove"
              aria-label={`Remove ${title} entry ${i + 1}`}
            >
              <XIcon size={15} />
            </button>
            {renderItem(item, (patch) => updateAt(i, patch))}
          </div>
        ))
      )}
      <button type="button" className="add-block-btn" onClick={add}>
        <PlusIcon size={15} style={{ display: "inline", verticalAlign: -2, marginRight: 6 }} />
        Add {title.toLowerCase()}
      </button>
    </div>
  );
}
