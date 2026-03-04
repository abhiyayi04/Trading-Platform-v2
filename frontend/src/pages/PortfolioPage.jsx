import { useEffect, useState } from "react";
import { tradingApi } from "../api/tradingApi";

export default function PortfolioPage() {
  const [data, setData] = useState(null);
  const [sellQty, setSellQty] = useState({}); // { [stockId]: qty }
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  async function load() {
    setError("");
    try {
      const res = await tradingApi.portfolio();
      setData(res);
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    load();
    }, []);

  async function placeSell(stockId) {
    setError("");
    setNotice("");

    const qty = Number(sellQty[stockId] ?? 1);
    if (!qty || qty <= 0) {
      setError("Quantity must be a positive number.");
      return;
    }

    try {
      const res = await tradingApi.placeOrder("SELL", stockId, qty);
      setNotice(
        `Sell order placed (PENDING): ${qty} shares @ $${Number(
          res.order.price_locked
        ).toFixed(2)}`
      );
      setSellQty((prev) => ({ ...prev, [stockId]: 1 }));
      await load(); // refresh holdings view
    } catch (e) {
      setError(e.message);
    }
  }

  if (error) return <div className="card">Error: {error}</div>;
  if (!data) return <div className="card">Loading portfolio...</div>;

  return (
    <div className="page">
      <div className="panel">
        <div className="cardHeader">
            <div>
            <h1 className="title">Portfolio</h1>
            <p className="muted" style={{ marginTop: 6 }}>
                Cash: ${Number(data.cash).toFixed(2)} • Holdings: $
                {Number(data.holdings_value).toFixed(2)} • Total: $
                {Number(data.total_equity).toFixed(2)}
            </p>
            </div>
            <button className="btn" onClick={load}>Refresh</button>
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

        <div style={{ marginTop: 16 }}>
            {data.holdings.length === 0 ? (
            <p className="muted">No holdings yet. Buy stocks from the Market page.</p>
            ) : (
            <table className="table">
                <thead>
                <tr>
                    <th>Symbol</th>
                    <th>Qty Owned</th>
                    <th>Avg Cost</th>
                    <th>Current Price</th>
                    <th>Market Value</th>
                    <th>Unrealized P/L</th>
                    <th style={{ width: 180 }}>Sell Qty</th>
                    <th style={{ width: 140 }}>Action</th>
                </tr>
                </thead>
                <tbody>
                {data.holdings.map((h) => (
                    <tr key={h.stock_id}>
                    <td>{h.symbol}</td>
                    <td>{h.quantity}</td>
                    <td>${Number(h.avg_cost).toFixed(2)}</td>
                    <td>${Number(h.current_price).toFixed(2)}</td>
                    <td>${Number(h.market_value).toFixed(2)}</td>
                    <td>
                        ${Number(h.unrealized_pl).toFixed(2)} (
                        {Number(h.unrealized_pl_pct).toFixed(2)}%)
                    </td>

                    <td>
                        <input
                        className="input"
                        type="number"
                        min="1"
                        step="1"
                        value={sellQty[h.stock_id] ?? 1}
                        onChange={(e) =>
                            setSellQty((prev) => ({
                            ...prev,
                            [h.stock_id]: e.target.value,
                            }))
                        }
                        />
                        <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>
                        Max: {h.quantity}
                        </div>
                    </td>

                    <td>
                        <button className="btn" onClick={() => placeSell(h.stock_id)}>
                        Sell
                        </button>
                    </td>
                    </tr>
                ))}
                </tbody>
            </table>
            )}
        </div>

        <div className="muted" style={{ marginTop: 14 }}>
            Note: Selling places a <b>PENDING</b> order. Execute/cancel from the Orders feature (we’ll wire that next if you want).
        </div>
      </div>
    </div>
  );
}