import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { authApi, type PasswordResetResponse } from "../api/auth";
import { ApiError } from "../api/client";
import { AuthLayout } from "../components/AuthLayout";
import { AlertIcon, ArrowLeftIcon, MailIcon } from "../components/icons";

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState<PasswordResetResponse | null>(null);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const res = await authApi.forgotPassword(email);
      setSent(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Request failed.");
    } finally {
      setBusy(false);
    }
  };

  if (sent) {
    return (
      <AuthLayout
        title="Check your inbox"
        subtitle={
          sent.reset_token
            ? "Email delivery isn't configured on this server — use the reset link below."
            : `If an account exists for ${email}, we've sent a link to reset your password.`
        }
        footer={
          <p className="switch-link">
            <Link to="/login">
              <ArrowLeftIcon size={13} style={{ verticalAlign: -2, marginRight: 4 }} />
              Back to login
            </Link>
          </p>
        }
      >
        <div className="auth-success">
          <span className="auth-success-icon">
            <MailIcon size={22} />
          </span>
          <p>
            Request received. The reset link is valid for 30 minutes and can only be used once.
          </p>
        </div>
        {sent.reset_token && (
          <Link
            className="btn btn-primary btn-block"
            to={`/reset-password?token=${encodeURIComponent(sent.reset_token)}`}
          >
            Open reset link
          </Link>
        )}
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="Forgot your password?"
      subtitle="Enter your account email and we'll send you a reset link."
      footer={
        <p className="switch-link">
          Remembered it? <Link to="/login">Back to login</Link>
        </p>
      }
    >
      <form onSubmit={onSubmit} className="auth-form">
        {error && (
          <div className="error">
            <AlertIcon size={15} />
            {error}
          </div>
        )}
        <div className="field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            required
            autoComplete="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <button className="btn btn-primary btn-block" type="submit" disabled={busy}>
          {busy ? (
            <>
              <span className="spinner" /> Sending…
            </>
          ) : (
            "Send reset link"
          )}
        </button>
      </form>
    </AuthLayout>
  );
}
