import { useEffect, useState } from "react";
import { tradingApi } from "../api/tradingApi";

export default function FundsPage() {
  const [cash, setCash] = useState(null);
  const [txns, setTxns] = useState([]);

  const [depositAmount, setDepositAmount] = useState("");
  const [withdrawAmount, setWithdrawAmount] = useState("");

  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  async function loadFunds() {
    setError("");
    try {
      const data = await tradingApi.funds();
      setCash(data.cash);
      const onlyCash = (data.recent_txns || []).filter(
        (t) => t.type === "DEPOSIT" || t.type === "WITHDRAW"
      );
      setTxns(onlyCash);
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    loadFunds();
  }, []);

  async function handleDeposit() {
    setError("");
    setNotice("");

    const amt = Number(depositAmount);
    if (!amt || amt <= 0) {
      setError("Enter a valid deposit amount.");
      return;
    }

    try {
      await tradingApi.deposit(amt);
      setNotice("Deposit successful.");
      setDepositAmount("");
      await loadFunds();
    } catch (e) {
      setError(e.message);
    }
  }

  async function handleWithdraw() {
    setError("");
    setNotice("");

    const amt = Number(withdrawAmount);
    if (!amt || amt <= 0) {
      setError("Enter a valid withdrawal amount.");
      return;
    }

    try {
      await tradingApi.withdraw(amt);
      setNotice("Withdrawal successful.");
      setWithdrawAmount("");
      await loadFunds();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div className="page">
      <div className="panel">
      <div className="cardHeader">
        <div>
          <h1 className="title">Fund Management</h1>
          <p className="muted" style={{ marginTop: 6 }}>
            Deposit or withdraw cash and review recent activity.
          </p>
        </div>
        <button className="btn" onClick={loadFunds}>
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

      <div style={{ marginTop: 16 }}>
        {cash === null ? (
          <p className="muted">Loading...</p>
        ) : (
          <div className="kv">
            <div className="k">Cash Balance</div>
            <div className="v">${Number(cash).toFixed(2)}</div>
          </div>
        )}
      </div>

      <div style={{ marginTop: 18 }}>
        <div className="grid2">
          <div className="kv">
            <div className="k">Deposit</div>
            <div style={{ display: "flex", gap: 10, alignItems: "center", marginTop: 10 }}>
              <input
                className="input"
                type="number"
                step="0.01"
                min="0"
                placeholder="Amount"
                value={depositAmount}
                onChange={(e) => setDepositAmount(e.target.value)}
              />
              <button className="btn" onClick={handleDeposit}>
                Deposit
              </button>
            </div>
            <p className="muted" style={{ marginTop: 10, fontSize: 13 }}>
              Uses your default payment method.
            </p>
          </div>

          <div className="kv">
            <div className="k">Withdraw</div>
            <div style={{ display: "flex", gap: 10, alignItems: "center", marginTop: 10 }}>
              <input
                className="input"
                type="number"
                step="0.01"
                min="0"
                placeholder="Amount"
                value={withdrawAmount}
                onChange={(e) => setWithdrawAmount(e.target.value)}
              />
              <button className="btn" onClick={handleWithdraw}>
                Withdraw
              </button>
            </div>
            <p className="muted" style={{ marginTop: 10, fontSize: 13 }}>
              Withdrawals are limited by your available cash balance.
            </p>
          </div>
        </div>
      </div>

      <div style={{ marginTop: 22 }}>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 800 }}>Cash Transactions</h2>

        {txns.length === 0 ? (
          <p className="muted" style={{ marginTop: 10 }}>
            No transactions yet.
          </p>
        ) : (
          <div style={{ marginTop: 10 }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Amount</th>
                  <th>Balance After</th>
                  <th>Note</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {txns.map((t) => (
                  <tr key={t.id}>
                    <td>{t.type}</td>
                    <td>${Number(t.amount).toFixed(2)}</td>
                    <td>${Number(t.balance_after).toFixed(2)}</td>
                    <td className="muted">{t.note || "-"}</td>
                    <td className="muted">
                      {t.created_at ? new Date(t.created_at).toLocaleString() : "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      </div>
    </div>
  );
}