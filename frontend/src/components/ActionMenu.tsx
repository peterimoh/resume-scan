import { useEffect, useRef, useState, type ReactNode } from "react";
import { MoreIcon } from "./icons";

export interface ActionMenuItem {
  label: string;
  icon: ReactNode;
  onClick: () => void;
  danger?: boolean;
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

export function ActionMenu({ items, label = "More actions" }: { items: ActionMenuItem[]; label?: string }) {
  const [open, setOpen] = useState(false);
  const ref = useDismissable(() => setOpen(false));

  return (
    <div className="menu-wrap" ref={ref}>
      <button
        type="button"
        className="icon-btn menu-btn"
        onClick={() => setOpen((o) => !o)}
        aria-label={label}
        aria-expanded={open}
      >
        <MoreIcon size={16} />
      </button>
      {open && (
        <div className="menu-dropdown" role="menu">
          {items.map((item) => (
            <button
              key={item.label}
              type="button"
              className={`menu-item${item.danger ? " danger" : ""}`}
              role="menuitem"
              onClick={() => {
                setOpen(false);
                item.onClick();
              }}
            >
              {item.icon} {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
