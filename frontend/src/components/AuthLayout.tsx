import type { ReactNode } from "react";
import { BrandLogo } from "./BrandLogo";
import { CheckIcon } from "./icons";

const BRAND_POINTS = [
  "AI HR & ATS analysis for any job posting",
  "Live PDF preview while you type",
  "Multiple profiles — one place for every resume",
];

/** Split-screen shell shared by all auth pages: branding panel on the left,
 * form on the right. The brand panel collapses away on small screens. */
export function AuthLayout({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="auth-shell">
      <aside className="auth-brand">
        <BrandLogo to="/" />
        <div className="auth-brand-body">
          <h2>Forge resumes that get you shortlisted.</h2>
          <ul>
            {BRAND_POINTS.map((point) => (
              <li key={point}>
                <span className="auth-brand-check">
                  <CheckIcon size={12} />
                </span>
                {point}
              </li>
            ))}
          </ul>
        </div>
        <p className="auth-brand-quote">
          "Everything I need to tailor a resume — templates, preview, and an AI review — in one
          place."
        </p>
      </aside>

      <div className="auth-form-col">
        <div className="auth-panel">
          <div className="auth-mobile-brand">
            <BrandLogo to="/" />
          </div>
          <h2>{title}</h2>
          <p className="auth-sub">{subtitle}</p>
          {children}
          {footer}
        </div>
        <span className="auth-legal">
          By continuing you agree to our Terms of Service and Privacy Policy.
        </span>
      </div>
    </div>
  );
}
