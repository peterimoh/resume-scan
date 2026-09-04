import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { authApi } from "../api/auth";
import { ApiError } from "../api/client";
import { AuthLayout } from "../components/AuthLayout";
import { PasswordInput } from "../components/PasswordInput";
import { AlertIcon, GoogleIcon } from "../components/icons";

const OAUTH_ERRORS: Record<string, string> = {
  google_unconfigured: "Google sign-in isn't configured on this server yet.",
  google_state: "The sign-in session expired. Please try again.",
  google_failed: "Couldn't complete Google sign-in. Please try again.",
  google_email: "Your Google account email couldn't be verified.",
};

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const oauthError = searchParams.get("error");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email, password);
      navigate("/profiles");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Log in to keep forging your resume."
      footer={
        <p className="switch-link">
          Need an account? <Link to="/register">Create one free</Link>
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
        {oauthError && (
          <div className="error">
            <AlertIcon size={15} />
            {OAUTH_ERRORS[oauthError] ?? "Sign-in failed. Please try again."}
          </div>
        )}
        <a className="btn google-btn" href={authApi.googleAuthUrl()}>
          <GoogleIcon size={18} />
          Sign in with Google
        </a>
        <div className="auth-divider">or continue with email</div>
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
        <div className="field">
          <div className="field-label-row">
            <label htmlFor="password">Password</label>
            <Link className="field-link" to="/forgot-password">
              Forgot password?
            </Link>
          </div>
          <PasswordInput
            id="password"
            required
            autoComplete="current-password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        <button className="btn btn-primary btn-block" type="submit" disabled={busy}>
          {busy ? (
            <>
              <span className="spinner" /> Logging in…
            </>
          ) : (
            "Log in"
          )}
        </button>
      </form>
    </AuthLayout>
  );
}
