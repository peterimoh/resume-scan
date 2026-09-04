import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { profilesApi } from "../api/profiles";
import { ApiError } from "../api/client";
import type { Profile } from "../types/resume";
import { EmptyState } from "../components/ui";
import {
  AlertIcon,
  ArrowRightIcon,
  FileIcon,
  MoreIcon,
  PencilIcon,
  PlusIcon,
  TrashIcon,
  UsersIcon,
  XIcon,
} from "../components/icons";

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]!.toUpperCase())
    .join("");
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function relativeTime(iso: string): string {
  const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo ago`;
  return `${Math.floor(months / 12)}y ago`;
}

function useDismissable(onDismiss: () => void) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const onPointerDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onDismiss();
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onDismiss();
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [onDismiss]);
  return ref;
}

function CardMenu({
  onEdit,
  onDelete,
}: {
  onEdit: () => void;
  onDelete: () => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useDismissable(() => setOpen(false));

  return (
    <div className="menu-wrap" ref={ref}>
      <button
        type="button"
        className="icon-btn menu-btn"
        onClick={() => setOpen((o) => !o)}
        aria-label="Profile actions"
        aria-expanded={open}
      >
        <MoreIcon size={16} />
      </button>
      {open && (
        <div className="menu-dropdown" role="menu">
          <button
            type="button"
            className="menu-item"
            role="menuitem"
            onClick={() => {
              setOpen(false);
              onEdit();
            }}
          >
            <PencilIcon size={14} /> Edit profile
          </button>
          <button
            type="button"
            className="menu-item danger"
            role="menuitem"
            onClick={() => {
              setOpen(false);
              onDelete();
            }}
          >
            <TrashIcon size={14} /> Delete profile
          </button>
        </div>
      )}
    </div>
  );
}

interface ModalState {
  mode: "create" | "edit";
  profile?: Profile;
}

export function ProfilesPage() {
  const [profiles, setProfiles] = useState<Profile[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState<ModalState | null>(null);

  const load = () => {
    profilesApi
      .list()
      .then(setProfiles)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load profiles."));
  };

  useEffect(load, []);

  const removeProfile = async (profile: Profile) => {
    if (!confirm(`Delete "${profile.name}" and all of its resumes? This cannot be undone.`)) return;
    setError(null);
    try {
      await profilesApi.remove(profile.id);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete profile.");
    }
  };

  return (
    <div className="stack-lg">
      <div className="page-head">
        <div>
          <h2>Profiles</h2>
          <p className="subtitle">
            A profile represents a person whose resumes you manage — one per person.
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setModal({ mode: "create" })}>
          <PlusIcon size={15} /> New profile
        </button>
      </div>

      {error && (
        <div className="error">
          <AlertIcon size={15} />
          {error}
        </div>
      )}

      {profiles === null ? (
        <div className="grid">
          {Array.from({ length: 3 }, (_, i) => (
            <div key={i} className="skeleton skeleton-card" style={{ height: 240 }} />
          ))}
        </div>
      ) : profiles.length === 0 ? (
        <EmptyState
          icon={<UsersIcon size={24} />}
          title="No profiles yet"
          message="Create a profile for yourself — or for each person whose resumes you manage."
          action={
            <button className="btn btn-primary" onClick={() => setModal({ mode: "create" })}>
              <PlusIcon size={15} /> Create your first profile
            </button>
          }
        />
      ) : (
        <div className="grid">
          {profiles.map((p) => (
            <div className="profile-card" key={p.id}>
              <div className="profile-cover" aria-hidden="true" />
              <div className="profile-body">
                <div className="profile-top">
                  <span className="avatar profile-avatar">{initials(p.name)}</span>
                  <CardMenu
                    onEdit={() => setModal({ mode: "edit", profile: p })}
                    onDelete={() => removeProfile(p)}
                  />
                </div>
                <h3 className="profile-name" title={p.name}>
                  {p.name}
                </h3>
                <p
                  className={`profile-headline${p.headline ? "" : " profile-no-headline"}`}
                  title={p.headline ?? undefined}
                >
                  {p.headline ?? "No headline yet"}
                </p>
                <div className="profile-stats">
                  {typeof p.resume_count === "number" && (
                    <>
                      <span className="profile-stat">
                        <FileIcon size={14} />
                        {p.resume_count} {p.resume_count === 1 ? "resume" : "resumes"}
                      </span>
                      <span className="profile-stat-sep" />
                    </>
                  )}
                  <span
                    className="profile-stat"
                    title={`Created ${formatDate(p.created_at)}`}
                  >
                    Updated {relativeTime(p.updated_at)}
                  </span>
                </div>
                <Link className="btn btn-soft btn-block" to={`/profiles/${p.id}/resumes`}>
                  Open library
                  <ArrowRightIcon size={14} />
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}

      {modal && (
        <ProfileModal
          state={modal}
          onClose={() => setModal(null)}
          onSaved={() => {
            setModal(null);
            load();
          }}
        />
      )}
    </div>
  );
}

function ProfileModal({
  state,
  onClose,
  onSaved,
}: {
  state: ModalState;
  onClose: () => void;
  onSaved: () => void;
}) {
  const editing = state.mode === "edit";
  const [name, setName] = useState(state.profile?.name ?? "");
  const [headline, setHeadline] = useState(state.profile?.headline ?? "");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const overlayRef = useRef<HTMLDivElement>(null);

  const submit = async () => {
    const trimmed = name.trim();
    if (!trimmed) {
      setError("Please give the profile a name.");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      if (editing && state.profile) {
        await profilesApi.update(state.profile.id, trimmed, headline.trim() || undefined);
      } else {
        await profilesApi.create(trimmed, headline.trim() || undefined);
      }
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
      setBusy(false);
    }
  };

  return (
    <div
      className="modal-overlay"
      ref={overlayRef}
      onMouseDown={(e) => {
        if (e.target === overlayRef.current) onClose();
      }}
    >
      <div className="modal" role="dialog" aria-modal="true" aria-label={editing ? "Edit profile" : "New profile"}>
        <div className="modal-head">
          <h3>{editing ? "Edit profile" : "New profile"}</h3>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close">
            <XIcon size={16} />
          </button>
        </div>
        <form
          className="stack"
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
        >
          {error && (
            <div className="error">
              <AlertIcon size={15} />
              {error}
            </div>
          )}
          <div className="field">
            <label htmlFor="profile-name">Name</label>
            <input
              id="profile-name"
              type="text"
              autoFocus
              required
              placeholder="e.g. Jane Doe"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="profile-headline">Headline (optional)</label>
            <input
              id="profile-headline"
              type="text"
              placeholder="e.g. Senior Backend Engineer"
              value={headline}
              onChange={(e) => setHeadline(e.target.value)}
            />
          </div>
          <div className="modal-actions">
            <button type="button" className="btn" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={busy}>
              {busy ? (
                <>
                  <span className="spinner" /> {editing ? "Saving…" : "Creating…"}
                </>
              ) : editing ? (
                "Save changes"
              ) : (
                "Create profile"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
