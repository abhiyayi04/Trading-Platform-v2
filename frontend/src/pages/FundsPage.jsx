import { useEffect, useState } from "react";
import NavBar from "../components/NavBar";
import { tradingApi } from "../api/tradingApi";

export default function FundsPage({ user, onLogout }) {
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
      setTxns(data.recent_txns || []);
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
      await loadFunds(); // refresh cash + txns
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
      await loadFunds(); // refresh cash + txns
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div style={{ maxWidth: 1100, margin: "40px auto", fontFamily: "Arial" }}>
      <NavBar user={user} onLogout={onLogout} />

      <h1 style={{ marginTop: 24 }}>Funds</h1>

      {notice && <p style={{ color: "green" }}>{notice}</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}

      {cash === null ? (
        <p>Loading...</p>
      ) : (
        <p>
          <b>Cash Balance:</b> ${Number(cash).toFixed(2)}
        </p>
      )}

      <div style={{ marginTop: 20, paddingTop: 12, borderTop: "1px solid #ddd" }}>
        <h2>Deposit</h2>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <input
            type="number"
            step="0.01"
            min="0"
            placeholder="Amount"
            value={depositAmount}
            onChange={(e) => setDepositAmount(e.target.value)}
            style={{ padding: 10, width: 200 }}
          />
          <button onClick={handleDeposit} style={{ padding: "10px 16px" }}>
            Deposit
          </button>
        </div>
        <p style={{ color: "#666", marginTop: 8 }}>
          Uses your default payment method. Next step we’ll add payment method selection.
        </p>
      </div>

      <div style={{ marginTop: 20, paddingTop: 12, borderTop: "1px solid #ddd" }}>
        <h2>Withdraw</h2>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <input
            type="number"
            step="0.01"
            min="0"
            placeholder="Amount"
            value={withdrawAmount}
            onChange={(e) => setWithdrawAmount(e.target.value)}
            style={{ padding: 10, width: 200 }}
          />
          <button onClick={handleWithdraw} style={{ padding: "10px 16px" }}>
            Withdraw
          </button>
        </div>
      </div>

      <div style={{ marginTop: 20, paddingTop: 12, borderTop: "1px solid #ddd" }}>
        <h2>Recent Transactions</h2>

        {txns.length === 0 ? (
          <p style={{ color: "#666" }}>No transactions yet.</p>
        ) : (
          <table width="100%" cellPadding="10">
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
                  <td style={{ color: "#666" }}>{t.note || "-"}</td>
                  <td style={{ color: "#666" }}>
                    {t.created_at ? new Date(t.created_at).toLocaleString() : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}