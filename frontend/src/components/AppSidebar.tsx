import { NavLink } from "react-router-dom";
import { BrandLogo } from "./BrandLogo";
import { BellIcon, InboxIcon, LibraryIcon, LogOutIcon, TargetIcon, XIcon } from "./icons";
import type { User } from "../types/resume";

function displayNameFromEmail(email: string) {
  const local = email.split("@")[0] ?? "";
  const parts = local.split(/[._-]+/).filter(Boolean);
  if (parts.length === 0) return local || "Account";
  return parts.map((p) => p.charAt(0).toUpperCase() + p.slice(1)).join(" ");
}

function initialsOf(name: string) {
  const words = name.split(" ").filter(Boolean);
  if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

interface AppSidebarProps {
  user: User;
  open: boolean;
  onClose: () => void;
  onLogout: () => void;
}

export function AppSidebar({ user, open, onClose, onLogout }: AppSidebarProps) {
  const name = displayNameFromEmail(user.email);
  const initials = initialsOf(name);

  return (
    <aside className={`sidebar${open ? " open" : ""}`}>
      <div className="sidebar-head">
        <BrandLogo to="/profiles" />
        <button type="button" className="sidebar-close" onClick={onClose} aria-label="Close menu">
          <XIcon size={16} />
        </button>
      </div>
      <nav className="sidebar-nav">
        <div className="sidebar-label">Menu</div>
        <NavLink to="/profiles" className="sidebar-link" onClick={onClose}>
          <LibraryIcon size={17} />
          My profiles
        </NavLink>
        <NavLink to="/quick-check" className="sidebar-link" onClick={onClose}>
          <TargetIcon size={17} />
          Quick Check
        </NavLink>
        <NavLink to="/jobs" className="sidebar-link" onClick={onClose}>
          <BellIcon size={17} />
          Job Board
        </NavLink>
        <NavLink to="/history" className="sidebar-link" onClick={onClose}>
          <InboxIcon size={17} />
          History
        </NavLink>
      </nav>
      <div className="sidebar-footer">
        <div className="sidebar-user" title={user.email}>
          <span className="avatar avatar-sm">{initials}</span>
          <span className="sidebar-user-info">
            <span className="sidebar-user-name">{name}</span>
            <span className="sidebar-user-email">{user.email}</span>
          </span>
        </div>
        <button type="button" className="sidebar-link sidebar-logout" onClick={onLogout}>
          <LogOutIcon size={16} />
          Sign out
        </button>
      </div>
    </aside>
  );
}
