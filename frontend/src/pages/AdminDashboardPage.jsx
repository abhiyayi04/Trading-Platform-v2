import { useEffect, useState } from "react";
import AdminNavBar from "../components/AdminNavBar";
import { tradingApi } from "../api/tradingApi";

export default function AdminDashboardPage({ user, onLogout }) {
  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadStocks() {
    setError("");
    const data = await tradingApi.adminStocks();
    setStocks(data);
  }

  useEffect(() => {
    (async () => {
      try {
        await loadStocks();
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div style={{ maxWidth: 1100, margin: "40px auto", fontFamily: "Arial" }}>
      <AdminNavBar user={user} onLogout={onLogout} />

      <h1 style={{ marginTop: 24 }}>Admin Dashboard</h1>
      <p style={{ color: "#666" }}>
        Logged in as <b>{user?.name}</b> ({user?.role})
      </p>

      {error && <p style={{ color: "red" }}>{error}</p>}

      <h2 style={{ marginTop: 20 }}>Stocks (Admin View)</h2>

      {loading ? (
        <p>Loading stocks...</p>
      ) : (
        <table width="100%" cellPadding="10">
          <thead>
            <tr>
              <th>Company</th>
              <th>Symbol</th>
              <th>Price</th>
              <th>Volume</th>
            </tr>
          </thead>
          <tbody>
            {stocks.map((s) => (
              <tr key={s.id}>
                <td>{s.company_name}</td>
                <td>{s.symbol}</td>
                <td>${Number(s.price).toFixed(2)}</td>
                <td>{Number(s.volume).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}