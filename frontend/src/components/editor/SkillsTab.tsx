import { ListEditor } from "./ListEditor";
import type { SkillGroup } from "../../types/resume";

interface Props {
  skills: SkillGroup[];
  capabilities: SkillGroup[];
  onChangeSkills: (items: SkillGroup[]) => void;
  onChangeCapabilities: (items: SkillGroup[]) => void;
}

function skillGroupFields(item: SkillGroup, update: (patch: Partial<SkillGroup>) => void) {
  return (
    <div className="stack">
      <div className="field">
        <label>Group</label>
        <input type="text" value={item.group} onChange={(e) => update({ group: e.target.value })} />
      </div>
      <div className="field">
        <label>Items (comma-separated)</label>
        <input type="text" value={item.items} onChange={(e) => update({ items: e.target.value })} />
      </div>
    </div>
  );
}

export function SkillsTab({ skills, capabilities, onChangeSkills, onChangeCapabilities }: Props) {
  return (
    <div className="stack">
      <ListEditor
        title="Core Technical Skills"
        items={skills}
        blank={() => ({ group: "", items: "" })}
        onChange={onChangeSkills}
        renderItem={skillGroupFields}
      />
      <ListEditor
        title="Technical Capabilities"
        items={capabilities}
        blank={() => ({ group: "", items: "" })}
        onChange={onChangeCapabilities}
        renderItem={skillGroupFields}
      />
    </div>
  );
}
