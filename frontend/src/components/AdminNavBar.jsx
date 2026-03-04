import { NavLink, useNavigate } from "react-router-dom";
import { useEffect, useRef, useState } from "react";

export default function AdminNavBar({ user, onLogout }) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    function onDocClick(e) {
      if (!menuRef.current) return;
      if (!menuRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  async function handleLogout() {
    await onLogout();
    navigate("/login", { replace: true });
  }

  const funds = Number(user?.funds ?? 0).toFixed(2);
  const initial = (user?.name?.[0] || "A").toUpperCase();

  return (
    <header className="topbar">
      <div className="topbarInner container">
        <div className="brand" style={{ cursor: "default" }}>
          <span className="brandIcon">🛠️</span>
          <span>Admin Console</span>
        </div>

        <nav className="navLinks">
          <NavLink className="navItem" to="/admin">
            Dashboard
          </NavLink>
          <NavLink className="navItem" to="/admin/stocks">
            Manage Stocks
          </NavLink>
          <NavLink className="navItem" to="/admin/market">
            Market Schedule
          </NavLink>
        </nav>

        <div className="navRight" ref={menuRef}>
          <div className="pill">
            <span className="muted">{user?.name}</span>
            <span className="dot">•</span>
            <span>${funds}</span>
          </div>

          <button className="profileBtn" onClick={() => setOpen((v) => !v)}>
            <span className="avatar">{initial}</span>
            <span className="caret">▾</span>
          </button>

          {open && (
            <div className="menu">
              <button className="menuItem danger" onClick={handleLogout}>
                Logout
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}