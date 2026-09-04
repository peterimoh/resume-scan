import { useEffect, useState } from "react";
import { Navigate, Outlet, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import { ProtectedRoute } from "./routes/ProtectedRoute";
import { ThemeToggle } from "./components/ThemeToggle";
import { AppSidebar } from "./components/AppSidebar";
import { MenuIcon } from "./components/icons";
import { LandingPage } from "./pages/LandingPage";
import { RegisterPage } from "./pages/RegisterPage";
import { LoginPage } from "./pages/LoginPage";
import { ForgotPasswordPage } from "./pages/ForgotPasswordPage";
import { ResetPasswordPage } from "./pages/ResetPasswordPage";
import { ProfilesPage } from "./pages/ProfilesPage";
import { ResumeLibraryPage } from "./pages/ResumeLibraryPage";
import { EditorPage } from "./pages/EditorPage";
import { AnalysisPage } from "./pages/AnalysisPage";
import { HistoryPage } from "./pages/HistoryPage";
import { QuickCheckPage } from "./pages/QuickCheckPage";
import { AllHistoryPage } from "./pages/AllHistoryPage";
import { JobBoardPage } from "./pages/JobBoardPage";
import { JobDetailPage } from "./pages/JobDetailPage";

function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [navOpen, setNavOpen] = useState(false);
  const [lastPath, setLastPath] = useState(location.pathname);
  if (lastPath !== location.pathname) {
    setLastPath(location.pathname);
    setNavOpen(false);
  }

  useEffect(() => {
    const mq = window.matchMedia("(min-width: 901px)");
    const onChange = () => {
      if (mq.matches) setNavOpen(false);
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    if (!navOpen) return;
    document.body.style.overflow = "hidden";
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setNavOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = "";
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [navOpen]);

  if (!user) return null;

  const onLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="app-shell">
      {navOpen && (
        <div className="sidebar-backdrop" onClick={() => setNavOpen(false)} aria-hidden="true" />
      )}
      <AppSidebar
        user={user}
        open={navOpen}
        onClose={() => setNavOpen(false)}
        onLogout={onLogout}
      />
      <div className="app-body">
        <header className="app-header">
          <button
            type="button"
            className="app-header-menu"
            onClick={() => setNavOpen(true)}
            aria-label="Open menu"
          >
            <MenuIcon size={18} />
          </button>
          <div className="app-header-actions">
            <ThemeToggle />
          </div>
        </header>
        <main className="main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function AppRoutes() {
  const { user, loading } = useAuth();

  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route
        path="/login"
        element={!loading && user ? <Navigate to="/profiles" replace /> : <LoginPage />}
      />
      <Route
        path="/register"
        element={!loading && user ? <Navigate to="/profiles" replace /> : <RegisterPage />}
      />
      <Route
        path="/forgot-password"
        element={!loading && user ? <Navigate to="/profiles" replace /> : <ForgotPasswordPage />}
      />
      <Route
        path="/reset-password"
        element={!loading && user ? <Navigate to="/profiles" replace /> : <ResetPasswordPage />}
      />
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/profiles" element={<ProfilesPage />} />
        <Route path="/profiles/:profileId/resumes" element={<ResumeLibraryPage />} />
        <Route path="/profiles/:profileId/resumes/:resumeId/edit" element={<EditorPage />} />
        <Route
          path="/profiles/:profileId/resumes/:resumeId/analysis/:mode"
          element={<AnalysisPage />}
        />
        <Route
          path="/profiles/:profileId/resumes/:resumeId/history"
          element={<HistoryPage />}
        />
        <Route path="/quick-check" element={<QuickCheckPage />} />
        <Route path="/quick-check/:resumeId/analysis/:mode" element={<AnalysisPage />} />
        <Route path="/quick-check/:resumeId/history" element={<HistoryPage />} />
        <Route path="/history" element={<AllHistoryPage />} />
        <Route path="/jobs" element={<JobBoardPage />} />
        <Route path="/jobs/:jobId" element={<JobDetailPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </ThemeProvider>
  );
}
