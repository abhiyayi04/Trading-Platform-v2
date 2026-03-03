import { useEffect, useState } from "react";
import AdminNavBar from "../components/AdminNavBar";
import { tradingApi } from "../api/tradingApi";

export default function AdminStocksPage({ user, onLogout }) {
  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(true);

  const [companyName, setCompanyName] = useState("");
  const [symbol, setSymbol] = useState("");
  const [price, setPrice] = useState("");
  const [volume, setVolume] = useState("");

  const [notice, setNotice] = useState("");
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

  async function createStock() {
    setError("");
    setNotice("");

    if (!companyName.trim() || !symbol.trim() || !price || volume === "") {
      setError("Please fill all fields.");
      return;
    }

    try {
      await tradingApi.adminCreateStock(
        companyName.trim(),
        symbol.trim(),
        Number(price),
        Number(volume)
      );

      setNotice("Stock created.");
      setCompanyName("");
      setSymbol("");
      setPrice("");
      setVolume("");

      await loadStocks();
    } catch (e) {
      setError(e.message);
    }
  }

  async function deleteStock(stockId) {
    setError("");
    setNotice("");

    try {
      await tradingApi.adminDeleteStock(stockId);
      setNotice("Stock deleted.");
      await loadStocks();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div style={{ maxWidth: 1100, margin: "40px auto", fontFamily: "Arial" }}>
      <AdminNavBar user={user} onLogout={onLogout} />

      <h1 style={{ marginTop: 24 }}>Manage Stocks</h1>

      {notice && <p style={{ color: "green" }}>{notice}</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}

      <div style={{ marginTop: 16, padding: 12, border: "1px solid #ddd" }}>
        <h2 style={{ marginTop: 0 }}>Create Stock</h2>

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <input
            placeholder="Company name"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            style={{ padding: 10, width: 260 }}
          />
          <input
            placeholder="Symbol (e.g. AAPL)"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            style={{ padding: 10, width: 160 }}
          />
          <input
            type="number"
            step="0.01"
            min="0"
            placeholder="Price"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            style={{ padding: 10, width: 140 }}
          />
          <input
            type="number"
            step="1"
            min="0"
            placeholder="Volume"
            value={volume}
            onChange={(e) => setVolume(e.target.value)}
            style={{ padding: 10, width: 160 }}
          />

          <button onClick={createStock} style={{ padding: "10px 16px" }}>
            Create
          </button>
        </div>
      </div>

      <h2 style={{ marginTop: 24 }}>Stocks</h2>

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
              <th style={{ width: 140 }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {stocks.map((s) => (
              <tr key={s.id}>
                <td>{s.company_name}</td>
                <td>{s.symbol}</td>
                <td>${Number(s.price).toFixed(2)}</td>
                <td>{Number(s.volume).toLocaleString()}</td>
                <td>
                  <button
                    onClick={() => deleteStock(s.id)}
                    style={{ padding: "8px 12px" }}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {stocks.length === 0 && (
              <tr>
                <td colSpan="5" style={{ color: "#666", textAlign: "center" }}>
                  No stocks yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}