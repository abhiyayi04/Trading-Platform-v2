import { Link } from "react-router-dom";

export default function AdminNavBar({ user, onLogout }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div style={{ display: "flex", gap: 18 }}>
          <Link to="/admin">Admin Dashboard</Link>
          <Link to="/admin/stocks">Manage Stocks</Link>
          <Link to="/admin/market">Change Market Schedule</Link>
        </div>

        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <span>
            {user?.name} | ${Number(user?.funds ?? 0).toFixed(2)}
          </span>
          <button onClick={onLogout}>Logout</button>
        </div>
      </div>

      <hr style={{ marginTop: 12 }} />
    </div>
  );
}