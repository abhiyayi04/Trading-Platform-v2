import { Link, NavLink, useNavigate } from "react-router-dom";
import { useEffect, useRef, useState } from "react";

export default function NavBar({ user, onLogout }) {
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
  const initial = (user?.name?.[0] || "U").toUpperCase();

  return (
    <header className="topbar">
      <div className="topbarInner">
        <Link to="/portfolio" className="brand">
          <span className="brandIcon">💰</span>
          <span>Stock Trading System</span>
        </Link>

        <nav className="navLinks">
          <NavLink className="navItem" to="/portfolio">Portfolio</NavLink>
          <NavLink className="navItem" to="/market">Stock Market</NavLink>
          <NavLink className="navItem" to="/funds">Fund Management</NavLink>
          <NavLink className="navItem" to="/transactions">Transactions</NavLink>
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
              <button
                className="menuItem"
                onClick={() => {
                  setOpen(false);
                  navigate("/profile");
                }}
              >
                Profile
              </button>
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