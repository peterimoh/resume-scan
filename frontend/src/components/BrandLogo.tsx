import { Link } from "react-router-dom";
import { BrandMark } from "./icons";

export function BrandLogo({ to = "/" }: { to?: string }) {
  return (
    <Link to={to} className="brand">
      <span className="brand-mark">
        <BrandMark size={16} />
      </span>
      ResumeForge
    </Link>
  );
}
