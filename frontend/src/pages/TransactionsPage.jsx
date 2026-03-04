import { useEffect, useState } from "react";
import { tradingApi } from "../api/tradingApi";

export default function TransactionsPage() {
  const [orders, setOrders] = useState([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function load() {
    setError("");
    try {
      const data = await tradingApi.orders();

      // Show only BUY/SELL orders (they should already be only BUY/SELL, but filtering is safe)
      const onlyStockOrders = (data || []).filter(
        (o) => o.side === "BUY" || o.side === "SELL"
      );

      setOrders(onlyStockOrders);
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    load();
    }, []);

  async function executeOrder(orderId) {
    setError("");
    setNotice("");
    try {
      const res = await tradingApi.executeOrder(orderId);
      setNotice(res.message || "Order executed.");
      await load();
    } catch (e) {
      setError(e.message);
    }
  }

  async function cancelOrder(orderId) {
    setError("");
    setNotice("");
    try {
      const res = await tradingApi.cancelOrder(orderId);
      setNotice(res.message || "Order canceled.");
      await load();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div className="page">
        <div className="panel">
      <div className="cardHeader">
        <div>
          <h1 className="title">Transactions</h1>
          <p className="muted" style={{ marginTop: 6 }}>
            Review and manage your BUY/SELL orders. Execute or cancel pending orders.
          </p>
        </div>
        <button className="btn" onClick={load}>Refresh</button>
      </div>

      {notice && <div className="alert ok" style={{ marginTop: 12 }}>{notice}</div>}
      {error && <div className="alert bad" style={{ marginTop: 12 }}>{error}</div>}

      <div style={{ marginTop: 16 }}>
        {orders.length === 0 ? (
          <p className="muted">No stock orders yet.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Symbol</th>
                <th>Company</th>
                <th>Side</th>
                <th>Qty</th>
                <th>Price Locked</th>
                <th>Status</th>
                <th style={{ width: 220 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => (
                <tr key={o.id}>
                  <td>{o.created_at ? new Date(o.created_at).toLocaleString() : "-"}</td>
                  <td>{o.symbol}</td>
                  <td>{o.company_name}</td>
                  <td>{o.side}</td>
                  <td>{o.quantity}</td>
                  <td>${Number(o.price_locked).toFixed(2)}</td>
                  <td>{o.status}</td>
                  <td>
                    {o.status === "PENDING" ? (
                      <div style={{ display: "flex", gap: 10 }}>
                        <button className="btn" onClick={() => executeOrder(o.id)}>
                          Execute
                        </button>
                        <button className="btn danger" onClick={() => cancelOrder(o.id)}>
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <p className="muted" style={{ marginTop: 14 }}>
        Buy orders are placed from <b>Market</b>. Sell orders are placed from <b>Portfolio</b>.
      </p>
      </div>
    </div>
  );
}