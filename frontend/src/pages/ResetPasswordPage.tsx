import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { authApi } from "../api/auth";
import { ApiError } from "../api/client";
import { AuthLayout } from "../components/AuthLayout";
import { PasswordInput } from "../components/PasswordInput";
import { AlertIcon, CheckIcon, KeyIcon } from "../components/icons";

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  if (!token) {
    return (
      <AuthLayout
        title="Invalid reset link"
        subtitle="This link is missing its reset token."
        footer={
          <p className="switch-link">
            <Link to="/forgot-password">Request a new reset link</Link>
          </p>
        }
      >
        <div className="auth-success">
          <span className="auth-success-icon danger">
            <AlertIcon size={22} />
          </span>
          <p>Reset links expire after 30 minutes and can only be used once.</p>
        </div>
      </AuthLayout>
    );
  }

  if (done) {
    return (
      <AuthLayout
        title="Password updated"
        subtitle="Your password has been changed. You've been logged out on all devices."
        footer={
          <p className="switch-link">
            <Link to="/login">Continue to login</Link>
          </p>
        }
      >
        <div className="auth-success">
          <span className="auth-success-icon">
            <CheckIcon size={22} />
          </span>
          <p>All set — log in with your new password.</p>
        </div>
        <button className="btn btn-primary btn-block" onClick={() => navigate("/login")}>
          Go to login
        </button>
      </AuthLayout>
    );
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (password !== confirm) {
      setError("Passwords don't match.");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      await authApi.resetPassword(token, password);
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Reset failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthLayout
      title="Choose a new password"
      subtitle="Pick something strong you don't use anywhere else."
      footer={
        <p className="switch-link">
          <Link to="/login">Back to login</Link>
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
          <label htmlFor="password">New password</label>
          <PasswordInput
            id="password"
            required
            minLength={8}
            autoComplete="new-password"
            placeholder="At least 8 characters"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="confirm">Confirm new password</label>
          <PasswordInput
            id="confirm"
            required
            minLength={8}
            autoComplete="new-password"
            placeholder="Repeat your new password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
          />
        </div>
        <button className="btn btn-primary btn-block" type="submit" disabled={busy}>
          {busy ? (
            <>
              <span className="spinner" /> Updating…
            </>
          ) : (
            <>
              <KeyIcon size={15} /> Update password
            </>
          )}
        </button>
      </form>
    </AuthLayout>
  );
}
