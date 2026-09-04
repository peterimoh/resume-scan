import type { ResumeData } from "../../types/resume";

interface Props {
  data: ResumeData;
  onChange: (patch: Partial<ResumeData>) => void;
}

export function HeaderFields({ data, onChange }: Props) {
  const setContact = (patch: Partial<ResumeData["contact"]>) =>
    onChange({ contact: { ...data.contact, ...patch } });

  return (
    <div className="stack">
      <div className="card-title" style={{ marginBottom: 0 }}>
        <h3>Basics</h3>
      </div>
      <div className="field">
        <label htmlFor="title">Resume title</label>
        <input
          id="title"
          type="text"
          value={data.title}
          onChange={(e) => onChange({ title: e.target.value })}
          placeholder="Library label — defaults to name if blank"
        />
      </div>
      <div className="field">
        <label htmlFor="name">Full name</label>
        <input id="name" type="text" value={data.name} onChange={(e) => onChange({ name: e.target.value })} />
      </div>
      <div className="field">
        <label htmlFor="headline">Headline</label>
        <input
          id="headline"
          type="text"
          value={data.headline}
          onChange={(e) => onChange({ headline: e.target.value })}
        />
      </div>
      <div className="row">
        <div className="field">
          <label>Location</label>
          <input type="text" value={data.contact.location} onChange={(e) => setContact({ location: e.target.value })} />
        </div>
        <div className="field">
          <label>Email</label>
          <input type="text" value={data.contact.email} onChange={(e) => setContact({ email: e.target.value })} />
        </div>
        <div className="field">
          <label>Phone</label>
          <input type="text" value={data.contact.phone} onChange={(e) => setContact({ phone: e.target.value })} />
        </div>
      </div>
      <div className="row">
        <div className="field">
          <label>GitHub</label>
          <input
            type="text"
            value={data.contact.github}
            placeholder="github.com/username"
            onChange={(e) => setContact({ github: e.target.value })}
          />
        </div>
        <div className="field">
          <label>LinkedIn</label>
          <input
            type="text"
            value={data.contact.linkedin}
            placeholder="linkedin.com/in/username"
            onChange={(e) => setContact({ linkedin: e.target.value })}
          />
        </div>
      </div>
      <div className="field">
        <label htmlFor="profile">Profile</label>
        <textarea id="profile" rows={3} value={data.profile} onChange={(e) => onChange({ profile: e.target.value })} />
      </div>
    </div>
  );
}
