import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { authApi } from "../api/auth";
import { ApiError } from "../api/client";
import { AuthLayout } from "../components/AuthLayout";
import { PasswordInput } from "../components/PasswordInput";
import { AlertIcon, GoogleIcon } from "../components/icons";

export function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [signupCode, setSignupCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await register(email, password, signupCode);
      navigate("/profiles");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Registration failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Start building resumes that get shortlisted."
      footer={
        <p className="switch-link">
          Already have an account? <Link to="/login">Log in</Link>
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
        <a className="btn google-btn" href={authApi.googleAuthUrl(signupCode)}>
          <GoogleIcon size={18} />
          Sign up with Google
        </a>
        <div className="auth-divider">or sign up with email</div>
        <div className="field">
          <label htmlFor="signupCode">Invite code</label>
          <input
            id="signupCode"
            type="text"
            autoComplete="off"
            placeholder="Leave blank if you weren't given one"
            value={signupCode}
            onChange={(e) => setSignupCode(e.target.value)}
          />
        </div>
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
          <label htmlFor="password">Password</label>
          <PasswordInput
            id="password"
            required
            minLength={8}
            autoComplete="new-password"
            placeholder="At least 8 characters"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <div className="hint" style={{ marginTop: 5 }}>
            At least 8 characters.
          </div>
        </div>
        <button className="btn btn-primary btn-block" type="submit" disabled={busy}>
          {busy ? (
            <>
              <span className="spinner" /> Creating account…
            </>
          ) : (
            "Create account"
          )}
        </button>
      </form>
    </AuthLayout>
  );
}
