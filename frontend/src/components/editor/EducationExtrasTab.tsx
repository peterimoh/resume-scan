import { ListEditor } from "./ListEditor";
import { StrListEditor } from "./StrListEditor";
import type { EducationEntry, ResumeData } from "../../types/resume";

interface Props {
  data: ResumeData;
  onChangeEducation: (items: EducationEntry[]) => void;
  onChangeCertifications: (items: string[]) => void;
  onChange: (patch: Partial<ResumeData>) => void;
}

export function EducationExtrasTab({ data, onChangeEducation, onChangeCertifications, onChange }: Props) {
  return (
    <div className="stack">
      <ListEditor
        title="Education"
        items={data.education}
        blank={() => ({ degree: "", school: "", year: "" })}
        onChange={onChangeEducation}
        renderItem={(item, update) => (
          <div className="stack">
            <div className="field">
              <label>Degree</label>
              <input type="text" value={item.degree} onChange={(e) => update({ degree: e.target.value })} />
            </div>
            <div className="row">
              <div className="field">
                <label>School</label>
                <input type="text" value={item.school} onChange={(e) => update({ school: e.target.value })} />
              </div>
              <div className="field">
                <label>Year</label>
                <input type="text" value={item.year} onChange={(e) => update({ year: e.target.value })} />
              </div>
            </div>
          </div>
        )}
      />

      <StrListEditor title="Certifications" items={data.certifications} onChange={onChangeCertifications} />

      <div className="field">
        <label>Career Progression</label>
        <textarea
          rows={3}
          value={data.career_progression}
          onChange={(e) => onChange({ career_progression: e.target.value })}
        />
      </div>

      <div className="field">
        <label>Professional Profile</label>
        <textarea
          rows={3}
          value={data.professional_profile}
          onChange={(e) => onChange({ professional_profile: e.target.value })}
        />
      </div>

      <div className="field">
        <label>Technology Index (comma-separated)</label>
        <textarea
          rows={2}
          value={data.technology_index.join(", ")}
          onChange={(e) => onChange({ technology_index: e.target.value.split(",").map((s) => s.trim()) })}
        />
      </div>

      <div className="field">
        <label>References</label>
        <textarea rows={2} value={data.references} onChange={(e) => onChange({ references: e.target.value })} />
      </div>
    </div>
  );
}
