import NavBar from "../components/NavBar";

export default function DashboardPage({
  user,
  stocks,
  orders,
  portfolio,
  buyQty,
  setBuyQty,
  sellQty,
  setSellQty,
  notice,
  error,
  market,
  onLogout,
  onPlaceBuy,
  onPlaceSell,
  onExecuteOrder,
  onCancelOrder,
}) {
  return (
    <div style={{ maxWidth: 1100, margin: "40px auto", fontFamily: "Arial" }}>
      <NavBar user={user} onLogout={onLogout} />

      {notice && <p style={{ color: "green", marginTop: 16 }}>{notice}</p>}
      {error && <p style={{ color: "red", marginTop: 16 }}>{error}</p>}

      {market && (
        <p style={{ marginTop: 10, color: market.is_open ? "green" : "red" }}>
            <b>Market:</b> {market.is_open ? "OPEN" : "CLOSED"}{" "}
            <span style={{ color: "#666" }}>({market.reason})</span>
        </p>
        )}

      <h2 style={{ marginTop: 24 }}>Market</h2>
      <table width="100%" cellPadding="10" style={{ marginBottom: 30 }}>
        <thead>
          <tr>
            <th>Company</th>
            <th>Symbol</th>
            <th>Price</th>
            <th>Volume</th>
            <th style={{ width: 220 }}>Buy</th>
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
                <div style={{ display: "flex", gap: 8 }}>
                  <input
                    type="number"
                    min="1"
                    step="1"
                    value={buyQty[s.id] ?? 1}
                    onChange={(e) =>
                      setBuyQty((prev) => ({ ...prev, [s.id]: e.target.value }))
                    }
                    style={{ width: 80, padding: 6 }}
                  />
                  <button onClick={() => onPlaceBuy(s.id)}>BUY</button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>Your Orders</h2>
      <table width="100%" cellPadding="10">
        <thead>
          <tr>
            <th>ID</th>
            <th>Stock</th>
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
              <td>{o.id}</td>
              <td>
                {o.symbol}{" "}
                <span style={{ color: "#666" }}>({o.company_name})</span>
              </td>
              <td>{o.side}</td>
              <td>{o.quantity}</td>
              <td>${Number(o.price_locked).toFixed(2)}</td>
              <td>{o.status}</td>
              <td>
                {o.status === "PENDING" ? (
                  <div style={{ display: "flex", gap: 8 }}>
                    <button onClick={() => onExecuteOrder(o.id)}>Execute</button>
                    <button onClick={() => onCancelOrder(o.id)}>Cancel</button>
                  </div>
                ) : (
                  <span style={{ color: "#777" }}>—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 style={{ marginTop: 30 }}>Portfolio</h2>

      {!portfolio ? (
        <p>Loading portfolio...</p>
      ) : (
        <>
          <div style={{ display: "flex", gap: 20, marginBottom: 12 }}>
            <div>
              <b>Cash:</b> ${Number(portfolio.cash).toFixed(2)}
            </div>
            <div>
              <b>Holdings Value:</b>{" "}
              ${Number(portfolio.holdings_value).toFixed(2)}
            </div>
            <div>
              <b>Total Equity:</b> ${Number(portfolio.total_equity).toFixed(2)}
            </div>
          </div>

          {portfolio.holdings.length === 0 ? (
            <p style={{ color: "#666" }}>
              No holdings yet. Execute a BUY order to get shares.
            </p>
          ) : (
            <table width="100%" cellPadding="10">
              <thead>
                <tr>
                  <th>Stock</th>
                  <th>Qty</th>
                  <th>Avg Cost</th>
                  <th>Current</th>
                  <th>Market Value</th>
                  <th>Unrealized P/L</th>
                  <th>P/L %</th>
                  <th style={{ width: 240 }}>Sell</th>
                </tr>
              </thead>
              <tbody>
                {portfolio.holdings.map((h) => (
                  <tr key={h.stock_id}>
                    <td>
                      {h.symbol}{" "}
                      <span style={{ color: "#666" }}>({h.company_name})</span>
                    </td>
                    <td>{h.quantity}</td>
                    <td>${Number(h.avg_cost).toFixed(2)}</td>
                    <td>${Number(h.current_price).toFixed(2)}</td>
                    <td>${Number(h.market_value).toFixed(2)}</td>
                    <td
                      style={{
                        color: Number(h.unrealized_pl) >= 0 ? "green" : "red",
                      }}
                    >
                      ${Number(h.unrealized_pl).toFixed(2)}
                    </td>
                    <td
                      style={{
                        color:
                          Number(h.unrealized_pl_pct) >= 0 ? "green" : "red",
                      }}
                    >
                      {Number(h.unrealized_pl_pct).toFixed(2)}%
                    </td>

                    <td>
                      <div style={{ display: "flex", gap: 8 }}>
                        <input
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
                          style={{ width: 90, padding: 6 }}
                        />
                        <button onClick={() => onPlaceSell(h.stock_id)}>
                          SELL
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </div>
  );
}