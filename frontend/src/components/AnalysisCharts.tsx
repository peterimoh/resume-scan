import type { AtsChartData, HrChartData } from "../lib/analysisPayload";
import { CheckIcon, XIcon } from "./icons";

type Tone = "success" | "warning" | "danger" | "accent";

function toneForPct(pct: number): Tone {
  if (pct >= 70) return "success";
  if (pct >= 40) return "warning";
  return "danger";
}

function Gauge({ value, label, sublabel }: { value: number; label: string; sublabel?: string }) {
  const pct = Math.max(0, Math.min(100, Math.round(value)));
  const tone = toneForPct(pct);
  const r = 42;
  const c = 2 * Math.PI * r;
  const offset = c - (pct / 100) * c;
  return (
    <div className="chart-gauge">
      <div className="chart-gauge-ring">
        <svg viewBox="0 0 100 100" width={104} height={104} aria-hidden="true">
          <circle cx="50" cy="50" r={r} className="chart-gauge-track" />
          <circle
            cx="50"
            cy="50"
            r={r}
            className={`chart-gauge-fill chart-tone-${tone}`}
            strokeDasharray={c}
            strokeDashoffset={offset}
            transform="rotate(-90 50 50)"
          />
        </svg>
        <div className="chart-gauge-value">{pct}%</div>
      </div>
      <div className="chart-gauge-caption">
        <span className="chart-gauge-label">{label}</span>
        {sublabel && <span className="chart-gauge-sub">{sublabel}</span>}
      </div>
    </div>
  );
}

function BarMeter({
  label,
  value,
  max,
  tone,
  valueLabel,
}: {
  label: string;
  value: number;
  max: number;
  tone: Tone;
  valueLabel?: string;
}) {
  const pct = max > 0 ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
  return (
    <div className="chart-bar-row">
      <div className="chart-bar-row-head">
        <span className="chart-bar-row-label">{label}</span>
        <span className="chart-bar-row-value">{valueLabel ?? `${value} / ${max}`}</span>
      </div>
      <div className="chart-bar-track">
        <div className={`chart-bar-fill chart-tone-${tone}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function SectionChips({ present, missing }: { present: string[]; missing: string[] }) {
  if (present.length === 0 && missing.length === 0) return null;
  return (
    <div className="chart-chip-row">
      {present.map((s) => (
        <span key={`p-${s}`} className="chart-chip chart-chip-success">
          <CheckIcon size={11} /> {s}
        </span>
      ))}
      {missing.map((s) => (
        <span key={`m-${s}`} className="chart-chip chart-chip-danger">
          <XIcon size={11} /> {s}
        </span>
      ))}
    </div>
  );
}

export function AtsCharts({ data }: { data: AtsChartData }) {
  const mustHaveMissing = data.missing_keywords.filter((k) => k.priority === "must_have");
  const niceHaveMissing = data.missing_keywords.filter((k) => k.priority === "nice_to_have");

  return (
    <div className="card chart-card">
      <h3 className="chart-card-title">At a glance</h3>
      <div className="chart-grid">
        <Gauge value={data.match_score} label="Match score" />
        <div className="chart-bars">
          <BarMeter
            label="Must-have requirements"
            value={data.must_have.matched}
            max={Math.max(data.must_have.total, 1)}
            tone={toneForPct((data.must_have.matched / Math.max(data.must_have.total, 1)) * 100)}
          />
          <BarMeter
            label="Nice-to-have requirements"
            value={data.nice_to_have.matched}
            max={Math.max(data.nice_to_have.total, 1)}
            tone="accent"
          />
        </div>
      </div>

      {(mustHaveMissing.length > 0 || niceHaveMissing.length > 0) && (
        <div className="chart-section">
          <span className="chart-section-label">Missing keywords</span>
          {mustHaveMissing.length > 0 && (
            <div className="chart-chip-row">
              {mustHaveMissing.map((k) => (
                <span key={k.term} className="chart-chip chart-chip-danger">
                  {k.term}
                </span>
              ))}
            </div>
          )}
          {niceHaveMissing.length > 0 && (
            <div className="chart-chip-row">
              {niceHaveMissing.map((k) => (
                <span key={k.term} className="chart-chip chart-chip-warning">
                  {k.term}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {(data.sections_present.length > 0 || data.sections_missing.length > 0) && (
        <div className="chart-section">
          <span className="chart-section-label">Section coverage</span>
          <SectionChips present={data.sections_present} missing={data.sections_missing} />
        </div>
      )}
    </div>
  );
}

export function HrCharts({ data }: { data: HrChartData }) {
  const gapCount = Math.max(data.standout_count, data.weakness_count, data.missing_requirements_count, 1);
  const totalAchievements = data.achievements.quantified + data.achievements.unquantified;

  return (
    <div className="card chart-card">
      <h3 className="chart-card-title">At a glance</h3>
      <div className="chart-grid">
        <Gauge value={data.fit_score} label="Fit score" sublabel={data.verdict} />
        <div className="chart-bars">
          <BarMeter
            label="What stands out"
            value={data.standout_count}
            max={gapCount}
            tone="success"
            valueLabel={String(data.standout_count)}
          />
          <BarMeter
            label="Flaws & weaknesses"
            value={data.weakness_count}
            max={gapCount}
            tone="warning"
            valueLabel={String(data.weakness_count)}
          />
          <BarMeter
            label="Missing requirements"
            value={data.missing_requirements_count}
            max={gapCount}
            tone="danger"
            valueLabel={String(data.missing_requirements_count)}
          />
        </div>
      </div>

      {totalAchievements > 0 && (
        <div className="chart-section">
          <span className="chart-section-label">Achievements tied to the role</span>
          <BarMeter
            label="Quantified with a number or metric"
            value={data.achievements.quantified}
            max={totalAchievements}
            tone="success"
            valueLabel={`${data.achievements.quantified} / ${totalAchievements}`}
          />
        </div>
      )}

      {data.scrutiny_flags > 0 && (
        <div className="chart-section">
          <span className="chart-section-label">HR scrutiny flags</span>
          <span className="chart-chip chart-chip-warning">
            {data.scrutiny_flags} flag{data.scrutiny_flags === 1 ? "" : "s"} raised
          </span>
        </div>
      )}
    </div>
  );
}
