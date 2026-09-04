import { ListEditor } from "./ListEditor";
import type { ImpactEntry, LeadershipEntry } from "../../types/resume";

interface Props {
  impact: ImpactEntry[];
  leadership: LeadershipEntry[];
  onChangeImpact: (items: ImpactEntry[]) => void;
  onChangeLeadership: (items: LeadershipEntry[]) => void;
}

export function ImpactLeadershipTab({ impact, leadership, onChangeImpact, onChangeLeadership }: Props) {
  return (
    <div className="stack">
      <ListEditor
        title="Selected Engineering Impact"
        items={impact}
        blank={() => ({ lead: "", text: "" })}
        onChange={onChangeImpact}
        renderItem={(item, update) => (
          <div className="stack">
            <div className="field">
              <label>Lead</label>
              <input type="text" value={item.lead} onChange={(e) => update({ lead: e.target.value })} />
            </div>
            <div className="field">
              <label>Text</label>
              <textarea rows={2} value={item.text} onChange={(e) => update({ text: e.target.value })} />
            </div>
          </div>
        )}
      />
      <ListEditor
        title="Leadership & Community"
        items={leadership}
        blank={() => ({ role: "", org: "", dates: "", description: "" })}
        onChange={onChangeLeadership}
        renderItem={(item, update) => (
          <div className="stack">
            <div className="row">
              <div className="field">
                <label>Role</label>
                <input type="text" value={item.role} onChange={(e) => update({ role: e.target.value })} />
              </div>
              <div className="field">
                <label>Organization</label>
                <input type="text" value={item.org} onChange={(e) => update({ org: e.target.value })} />
              </div>
            </div>
            <div className="field">
              <label>Dates</label>
              <input type="text" value={item.dates} onChange={(e) => update({ dates: e.target.value })} />
            </div>
            <div className="field">
              <label>Description</label>
              <textarea
                rows={2}
                value={item.description}
                onChange={(e) => update({ description: e.target.value })}
              />
            </div>
          </div>
        )}
      />
    </div>
  );
}
