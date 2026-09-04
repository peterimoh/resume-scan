import { api, API_BASE_URL } from "./client";
import type { User } from "../types/resume";

export interface PasswordResetResponse {
  ok: boolean;
  /** Only set while the server has no mailer configured (dev fallback). */
  reset_token?: string | null;
  note?: string | null;
}

export const authApi = {
  register: (email: string, password: string, signupCode?: string) =>
    api.post<User>("/api/auth/register", { email, password, signup_code: signupCode || null }),
  login: (email: string, password: string) => api.post<User>("/api/auth/login", { email, password }),
  logout: () => api.post<void>("/api/auth/logout"),
  me: () => api.get<User>("/api/auth/me"),
  forgotPassword: (email: string) =>
    api.post<PasswordResetResponse>("/api/auth/forgot-password", { email }),
  resetPassword: (token: string, password: string) =>
    api.post<PasswordResetResponse>("/api/auth/reset-password", { token, password }),
  /** Top-level navigation target for "Sign in with Google" / "Sign up with Google". */
  googleAuthUrl: (signupCode?: string) =>
    signupCode
      ? `${API_BASE_URL}/api/auth/google?${new URLSearchParams({ signup_code: signupCode })}`
      : `${API_BASE_URL}/api/auth/google`,
};
