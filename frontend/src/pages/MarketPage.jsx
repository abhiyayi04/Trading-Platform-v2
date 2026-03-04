import { useEffect, useState } from "react";
import { tradingApi } from "../api/tradingApi";

export default function MarketPage() {
  const [stocks, setStocks] = useState([]);
  const [market, setMarket] = useState(null);

  const [buyQty, setBuyQty] = useState({}); // { [stockId]: qty }
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  async function load() {
    setError("");
    try {
      const s = await tradingApi.stocks();
      const m = await tradingApi.marketStatus();
      setStocks(s);
      setMarket(m);
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    load();
    }, []);

  async function placeBuy(stockId) {
    setError("");
    setNotice("");

    const qty = Number(buyQty[stockId] ?? 1);
    if (!qty || qty <= 0) {
      setError("Quantity must be a positive number.");
      return;
    }

    try {
      const res = await tradingApi.placeOrder("BUY", stockId, qty);
      setNotice(
        `Buy order placed (PENDING): ${qty} shares @ $${Number(
          res.order.price_locked
        ).toFixed(2)}`
      );
      setBuyQty((prev) => ({ ...prev, [stockId]: 1 }));
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div className="page">
        <div className="panel">
      <div className="cardHeader">
        <h1 className="title">Stock Market</h1>
        <button className="btn" onClick={load}>Refresh</button>
      </div>

      <p className="muted">
        Market: <b>{market?.is_open ? "OPEN" : "CLOSED"}</b>{" "}
        <span style={{ opacity: 0.7 }}>({market?.reason || "..."})</span>
      </p>

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

      <div style={{ marginTop: 16 }}>
        <table className="table">
          <thead>
            <tr>
              <th>Company</th>
              <th>Symbol</th>
              <th>Price</th>
              <th>Volume</th>
              <th style={{ width: 180 }}>Buy Qty</th>
              <th style={{ width: 140 }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {stocks.map((s) => (
              <tr key={s.id}>
                <td>{s.company_name}</td>
                <td>{s.symbol}</td>
                <td>${Number(s.price).toFixed(2)}</td>
                <td>{Number(s.volume).toFixed(2)}</td>

                <td>
                  <input
                    className="input"
                    type="number"
                    min="1"
                    step="1"
                    value={buyQty[s.id] ?? 1}
                    onChange={(e) =>
                      setBuyQty((prev) => ({
                        ...prev,
                        [s.id]: e.target.value,
                      }))
                    }
                  />
                </td>

                <td>
                  <button className="btn" onClick={() => placeBuy(s.id)}>
                    Buy
                  </button>
                </td>
              </tr>
            ))}
            {stocks.length === 0 && (
              <tr>
                <td colSpan="6" className="muted">
                  No stocks available.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      </div>
    </div>
  );
}