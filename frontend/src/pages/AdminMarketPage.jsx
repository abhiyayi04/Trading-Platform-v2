import { useEffect, useMemo, useState } from "react";
import AdminNavBar from "../components/AdminNavBar";
import { tradingApi } from "../api/tradingApi";

function parseClosedDates(value) {
  if (!value) return [];
  return value
    .split(",")
    .map((d) => d.trim())
    .filter(Boolean);
}

export default function AdminMarketPage({ user, onLogout }) {
  const [status, setStatus] = useState(null);

  const [openTime, setOpenTime] = useState("09:30");
  const [closeTime, setCloseTime] = useState("16:00");

  const [closedDates, setClosedDates] = useState([]); // ["YYYY-MM-DD"]
  const [newDate, setNewDate] = useState("");

  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const closedDatesSorted = useMemo(() => {
    return [...closedDates].sort();
  }, [closedDates]);

  async function loadStatus() {
    setError("");
    const data = await tradingApi.marketStatus();
    setStatus(data);

    // If your /api/market/status includes open_time/close_time/closed_dates, use them.
    // If not, we’ll keep defaults for now.
    if (data.open_time) setOpenTime(data.open_time);
    if (data.close_time) setCloseTime(data.close_time);

    if (typeof data.closed_dates === "string") {
      setClosedDates(parseClosedDates(data.closed_dates));
    } else if (Array.isArray(data.closed_dates)) {
      setClosedDates(data.closed_dates);
    }
  }

  useEffect(() => {
    (async () => {
      try {
        await loadStatus();
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  async function toggleMarket() {
    setError("");
    setNotice("");
    try {
      await tradingApi.adminToggleMarket();
      setNotice("Market toggle successful.");
      await loadStatus();
    } catch (e) {
      setError(e.message);
    }
  }

  async function saveHours() {
    setError("");
    setNotice("");

    if (!openTime || !closeTime) {
      setError("Please set both open and close time.");
      return;
    }

    try {
      await tradingApi.adminSetMarketHours(openTime, closeTime);
      setNotice("Market hours updated.");
      await loadStatus();
    } catch (e) {
      setError(e.message);
    }
  }

  function addClosedDate() {
    setError("");
    setNotice("");

    if (!newDate) {
      setError("Pick a date first.");
      return;
    }
    if (closedDates.includes(newDate)) {
      setError("That date is already in the list.");
      return;
    }
    setClosedDates((prev) => [...prev, newDate]);
    setNewDate("");
  }

  function removeClosedDate(d) {
    setClosedDates((prev) => prev.filter((x) => x !== d));
  }

  async function saveClosedDates() {
    setError("");
    setNotice("");
    try {
      await tradingApi.adminSetClosedDates(closedDatesSorted);
      setNotice("Closed dates updated.");
      await loadStatus();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div style={{ maxWidth: 1100, margin: "40px auto", fontFamily: "Arial" }}>
      <AdminNavBar user={user} onLogout={onLogout} />

      <h1 style={{ marginTop: 24 }}>Change Market Schedule</h1>

      {notice && <p style={{ color: "green" }}>{notice}</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}

      {loading || !status ? (
        <p>Loading market status...</p>
      ) : (
        <>
          <div style={{ marginTop: 16, padding: 12, border: "1px solid #ddd" }}>
            <h2 style={{ marginTop: 0 }}>Current Status</h2>
            <p style={{ marginTop: 0 }}>
              <b>Admin Override:</b> {status.admin_override ? "ON" : "OFF"}
            </p>
            <p>
              <b>Market:</b>{" "}
              <span style={{ color: status.is_open ? "green" : "red" }}>
                {status.is_open ? "OPEN" : "CLOSED"}
              </span>{" "}
              <span style={{ color: "#666" }}>({status.reason})</span>
            </p>

            <button onClick={toggleMarket} style={{ padding: "10px 16px" }}>
              Toggle Open / Close (Admin Override)
            </button>
          </div>

          <div
            style={{
              marginTop: 16,
              padding: 12,
              border: "1px solid #ddd",
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 16,
            }}
          >
            {/* Market Hours */}
            <div>
              <h2 style={{ marginTop: 0 }}>Market Hours</h2>

              <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                <div>
                  <div style={{ fontSize: 12, color: "#666" }}>Open</div>
                  <input
                    type="time"
                    value={openTime}
                    onChange={(e) => setOpenTime(e.target.value)}
                    style={{ padding: 10, width: 180 }}
                  />
                </div>

                <div>
                  <div style={{ fontSize: 12, color: "#666" }}>Close</div>
                  <input
                    type="time"
                    value={closeTime}
                    onChange={(e) => setCloseTime(e.target.value)}
                    style={{ padding: 10, width: 180 }}
                  />
                </div>

                <button onClick={saveHours} style={{ padding: "10px 16px" }}>
                  Update Hours
                </button>
              </div>

              <p style={{ color: "#666", marginTop: 10 }}>
                Times should be in 24-hour format (input handles this).
              </p>
            </div>

            {/* Closed Dates */}
            <div>
              <h2 style={{ marginTop: 0 }}>Closed Dates</h2>

              <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                <input
                  type="date"
                  value={newDate}
                  onChange={(e) => setNewDate(e.target.value)}
                  style={{ padding: 10, width: 200 }}
                />
                <button onClick={addClosedDate} style={{ padding: "10px 16px" }}>
                  Add Date
                </button>
                <button
                  onClick={saveClosedDates}
                  style={{ padding: "10px 16px" }}
                >
                  Save Closed Dates
                </button>
              </div>

              {closedDatesSorted.length === 0 ? (
                <p style={{ color: "#666", marginTop: 10 }}>No closed dates yet.</p>
              ) : (
                <div style={{ marginTop: 10 }}>
                  {closedDatesSorted.map((d) => (
                    <div
                      key={d}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        border: "1px solid #eee",
                        padding: "8px 10px",
                        marginBottom: 6,
                        borderRadius: 6,
                      }}
                    >
                      <span>{d}</span>
                      <button onClick={() => removeClosedDate(d)}>Remove</button>
                    </div>
                  ))}
                </div>
              )}

              <p style={{ color: "#666", marginTop: 10 }}>
                Click “Save Closed Dates” to persist to the database.
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}