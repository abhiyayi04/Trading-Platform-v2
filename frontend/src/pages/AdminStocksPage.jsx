import { useEffect, useState } from "react";
import { tradingApi } from "../api/tradingApi";

export default function AdminStocksPage() {
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

    if (!companyName.trim() || !symbol.trim() || price === "" || volume === "") {
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
    <div className="page">
      <div className="panel">
        <div className="cardHeader">
          <div>
            <h1 className="title">Manage Stocks</h1>
            <p className="muted" style={{ marginTop: 6 }}>
              Create new stocks and remove existing listings.
            </p>
          </div>
          <button className="btn" onClick={loadStocks}>
            Refresh
          </button>
        </div>

        {notice && (
          <div className="alert ok" style={{ marginTop: 12 }}>
            {notice}
          </div>
        )}
        {error && (
          <div className="alert bad" style={{ marginTop: 12 }}>
            {error}
          </div>
        )}

        {/* Create Stock */}
        <div style={{ marginTop: 16 }}>
          <div className="kv">
            <div className="k">Create Stock</div>

            <div
              style={{
                display: "flex",
                gap: 10,
                flexWrap: "wrap",
                marginTop: 10,
                alignItems: "flex-end",
              }}
            >
              <div style={{ minWidth: 260, flex: "1 1 260px" }}>
                <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>
                  Company name
                </div>
                <input
                  className="input"
                  placeholder="e.g. Apple Inc."
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                />
              </div>

              <div style={{ minWidth: 160, flex: "0 1 160px" }}>
                <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>
                  Symbol
                </div>
                <input
                  className="input"
                  placeholder="e.g. AAPL"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                />
              </div>

              <div style={{ minWidth: 140, flex: "0 1 140px" }}>
                <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>
                  Price
                </div>
                <input
                  className="input"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="0.00"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                />
              </div>

              <div style={{ minWidth: 160, flex: "0 1 160px" }}>
                <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>
                  Volume
                </div>
                <input
                  className="input"
                  type="number"
                  step="1"
                  min="0"
                  placeholder="0"
                  value={volume}
                  onChange={(e) => setVolume(e.target.value)}
                />
              </div>

              <button className="btn" onClick={createStock}>
                Create
              </button>
            </div>

            <p className="muted" style={{ marginTop: 10, fontSize: 13 }}>
              Tip: Use short, unique symbols (e.g., TSLA, GOOGL).
            </p>
          </div>
        </div>

        {/* Stocks Table */}
        <div style={{ marginTop: 18 }}>
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 900 }}>Stocks</h2>

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
                    <th style={{ width: 160 }}>Actions</th>
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
                        <button className="btn danger" onClick={() => deleteStock(s.id)}>
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}

                  {stocks.length === 0 && (
                    <tr>
                      <td colSpan="5" className="muted" style={{ textAlign: "center" }}>
                        No stocks yet.
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