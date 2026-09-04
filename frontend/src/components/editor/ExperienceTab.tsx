import { ListEditor } from "./ListEditor";
import type { ExperienceEntry } from "../../types/resume";

interface Props {
  items: ExperienceEntry[];
  onChange: (items: ExperienceEntry[]) => void;
}

export function ExperienceTab({ items, onChange }: Props) {
  return (
    <ListEditor
      title="Professional Experience"
      items={items}
      blank={() => ({ role: "", company: "", type: "", dates: "", highlights: [] })}
      onChange={onChange}
      renderItem={(item, update) => (
        <div className="stack">
          <div className="row">
            <div className="field">
              <label>Role</label>
              <input type="text" value={item.role} onChange={(e) => update({ role: e.target.value })} />
            </div>
            <div className="field">
              <label>Company</label>
              <input type="text" value={item.company} onChange={(e) => update({ company: e.target.value })} />
            </div>
          </div>
          <div className="row">
            <div className="field">
              <label>Type</label>
              <input type="text" value={item.type} onChange={(e) => update({ type: e.target.value })} />
            </div>
            <div className="field">
              <label>Dates</label>
              <input type="text" value={item.dates} onChange={(e) => update({ dates: e.target.value })} />
            </div>
          </div>
          <div className="field">
            <label>Highlights (one per line)</label>
            <textarea
              rows={4}
              value={item.highlights.join("\n")}
              onChange={(e) => update({ highlights: e.target.value.split("\n") })}
            />
          </div>
        </div>
      )}
    />
  );
}
