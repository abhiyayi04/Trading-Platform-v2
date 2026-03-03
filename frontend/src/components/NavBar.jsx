import { Link } from "react-router-dom";

export default function NavBar({ user, onLogout }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "16px 40px",
        borderBottom: "1px solid #ddd",
        fontFamily: "Arial",
      }}
    >
      <div style={{ display: "flex", gap: 20 }}>
        <Link to="/dashboard" style={{ textDecoration: "none" }}>
          Dashboard
        </Link>

        <Link to="/funds" style={{ textDecoration: "none" }}>
          Funds
        </Link>
      </div>

      <div style={{ display: "flex", gap: 20, alignItems: "center" }}>
        <span>
          {user.name} | ${Number(user.funds).toFixed(2)}
        </span>

        <button onClick={onLogout}>Logout</button>
      </div>
    </div>
  );
}