import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { BrandLogo } from "../components/BrandLogo";
import { ThemeToggle } from "../components/ThemeToggle";
import {
  CheckIcon,
  CodeIcon,
  DownloadIcon,
  FileIcon,
  LayoutIcon,
  SparklesIcon,
  TargetIcon,
  UsersIcon,
} from "../components/icons";

const FEATURES = [
  {
    icon: <SparklesIcon size={22} />,
    title: "AI HR review",
    text: "Get a recruiter's-eye critique of your resume against any job description, streamed in real time.",
  },
  {
    icon: <TargetIcon size={22} />,
    title: "ATS optimization",
    text: "Beat the keyword filters with a dedicated ATS-mode breakdown that shows exactly what to fix.",
  },
  {
    icon: <FileIcon size={22} />,
    title: "Live PDF preview",
    text: "Watch your resume recompile as you type. Print-ready, typeset PDFs — no formatting fights.",
  },
  {
    icon: <LayoutIcon size={22} />,
    title: "Templates & fonts",
    text: "Switch between professional LaTeX templates and typefaces with a single click.",
  },
  {
    icon: <UsersIcon size={22} />,
    title: "Multiple profiles",
    text: "Manage resumes for different people or personas — perfect for coaches, consultants, and job families.",
  },
  {
    icon: <CodeIcon size={22} />,
    title: "Own your data",
    text: "Import and export resumes as JSON, duplicate variations, and download every PDF you generate.",
  },
];

const STEPS = [
  {
    title: "Create a profile",
    text: "A profile holds a person's resume library. Set one up for yourself or each client in seconds.",
  },
  {
    title: "Build with live preview",
    text: "Fill in guided sections — experience, skills, impact — and watch the polished PDF compile instantly.",
  },
  {
    title: "Tailor with AI",
    text: "Paste a job posting and run HR or ATS analysis to get concrete, actionable improvement suggestions.",
  },
];

function HeroMock() {
  return (
    <div className="hero-visual" aria-hidden="true">
      <div className="mock-window">
        <div className="mock-titlebar">
          <span className="dot" />
          <span className="dot" />
          <span className="dot" />
        </div>
        <div className="mock-body">
          <div className="mock-doc">
            <div className="mock-line name" />
            <div className="mock-line w65" />
            <div className="mock-line heading" style={{ width: "40%" }} />
            <div className="mock-line w90" />
            <div className="mock-line w80" />
            <div className="mock-line w65" />
            <div className="mock-line heading" style={{ width: "35%" }} />
            <div className="mock-line w90" />
            <div className="mock-line w80" />
          </div>
          <div className="mock-panel">
            <div className="score-card">
              <div className="score-ring">
                <span>87</span>
              </div>
              <div>
                <strong>ATS Score</strong>
                <span className="hint">Strong keyword match</span>
              </div>
            </div>
            <div className="suggest-card">
              <strong>Suggestions</strong>
              <div className="suggest-line">
                <span className="tick">
                  <CheckIcon size={10} />
                </span>
                Add "CI/CD" to skills
              </div>
              <div className="suggest-line">
                <span className="tick">
                  <CheckIcon size={10} />
                </span>
                Quantify impact bullets
              </div>
              <div className="suggest-line">
                <span className="tick">
                  <CheckIcon size={10} />
                </span>
                Mirror job title keywords
              </div>
            </div>
          </div>
        </div>
      </div>
      <div className="float-chip fc-1">
        <span className="chip-icon">
          <SparklesIcon size={15} />
        </span>
        AI analysis ready
      </div>
      <div className="float-chip fc-2">
        <span className="chip-icon">
          <DownloadIcon size={15} />
        </span>
        PDF generated
      </div>
    </div>
  );
}

export function LandingPage() {
  const { user } = useAuth();
  const appHref = user ? "/profiles" : "/register";
  const ctaLabel = user ? "Open app" : "Get started free";

  return (
    <div className="landing">
      <header className="landing-nav">
        <BrandLogo />
        <nav className="landing-nav-links">
          <a href="#features">Features</a>
          <a href="#how-it-works">How it works</a>
        </nav>
        <div className="landing-nav-cta">
          <ThemeToggle />
          {user ? (
            <Link className="btn btn-sm btn-primary" to={appHref}>
              Open app
            </Link>
          ) : (
            <>
              <Link className="btn btn-sm btn-ghost" to="/login">
                Log in
              </Link>
              <Link className="btn btn-sm btn-primary" to="/register">
                Get started
              </Link>
            </>
          )}
        </div>
      </header>

      <main>
        <section className="hero">
          <div className="hero-inner">
            <div className="hero-copy">
              <span className="hero-badge">
                <SparklesIcon size={14} />
                AI-powered resume builder
              </span>
              <h1>
                Resumes that get you <span className="grad-text">shortlisted</span>
              </h1>
              <p className="lede">
                ResumeForge combines beautifully typeset templates with AI-powered HR and ATS
                analysis, so every resume you send is tailored, polished, and filter-proof.
              </p>
              <div className="hero-actions">
                <Link className="btn btn-primary btn-lg" to={appHref}>
                  {ctaLabel}
                  <SparklesIcon size={16} />
                </Link>
                <a className="btn btn-lg" href="#how-it-works">
                  See how it works
                </a>
              </div>
              <p className="hero-note">Free to start · No credit card required</p>
            </div>
            <HeroMock />
          </div>
        </section>

        <section className="landing-section" id="features">
          <div className="section-head">
            <span className="eyebrow">Features</span>
            <h2>Everything you need to land the interview</h2>
            <p>
              From first draft to tailored submission — one tool for writing, polishing, and
              beating the filters.
            </p>
          </div>
          <div className="features-grid">
            {FEATURES.map((f) => (
              <div className="feature-card" key={f.title}>
                <div className="feature-icon">{f.icon}</div>
                <h3>{f.title}</h3>
                <p>{f.text}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="landing-section" id="how-it-works">
          <div className="section-head">
            <span className="eyebrow">How it works</span>
            <h2>Three steps to a stronger resume</h2>
          </div>
          <div className="steps-grid">
            {STEPS.map((s, i) => (
              <div className="step-card" key={s.title}>
                <span className="step-num">{i + 1}</span>
                <h3>{s.title}</h3>
                <p>{s.text}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="cta-band">
          <div className="cta-inner">
            <h2>Ready to forge your best resume?</h2>
            <p>
              Create an account and generate your first polished, ATS-ready PDF in minutes.
            </p>
            <Link className="btn btn-lg btn-white" to={appHref}>
              {ctaLabel}
            </Link>
          </div>
        </section>
      </main>

      <footer className="landing-footer">
        <div className="landing-footer-inner">
          <span className="hint">© {new Date().getFullYear()} ResumeForge</span>
          <span className="hint">Built with LaTeX-quality typesetting and AI review.</span>
        </div>
      </footer>
    </div>
  );
}
