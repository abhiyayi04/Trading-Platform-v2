import { useEffect, useState } from "react";
import { tradingApi } from "../api/tradingApi";

export default function AdminDashboardPage({ user }) {
  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadStocks() {
    setError("");
    const data = await tradingApi.adminStocks();
    setStocks(data || []);
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
    <div className="page">
      <div className="panel">
        <div className="cardHeader">
          <div>
            <h1 className="title">Admin Dashboard</h1>
            <p className="muted" style={{ marginTop: 6 }}>
              Logged in as <b>{user?.name}</b> ({user?.role})
            </p>
          </div>

          <button className="btn" onClick={loadStocks}>
            Refresh
          </button>
        </div>

        {error && (
          <div className="alert bad" style={{ marginTop: 12 }}>
            {error}
          </div>
        )}

        <div style={{ marginTop: 18 }}>
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 800 }}>
            Stocks (Admin View)
          </h2>

          {loading ? (
            <p className="muted" style={{ marginTop: 10 }}>
              Loading stocks...
            </p>
          ) : (
            <div style={{ marginTop: 10 }}>
              <table className="table">
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

                  {stocks.length === 0 && (
                    <tr>
                      <td colSpan="4" className="muted">
                        No stocks found.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}