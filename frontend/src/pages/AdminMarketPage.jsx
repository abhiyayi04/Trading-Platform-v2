import { useEffect, useMemo, useState } from "react";
import { tradingApi } from "../api/tradingApi";

function parseClosedDates(value) {
  if (!value) return [];
  return value
    .split(",")
    .map((d) => d.trim())
    .filter(Boolean);
}

export default function AdminMarketPage() {
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

  const marketLabel = status?.is_open ? "OPEN" : "CLOSED";
  const marketReason = status?.reason || "...";
  const overrideLabel = status?.admin_override ? "ON" : "OFF";

  return (
    <div className="page">
      <div className="panel">
        <div className="cardHeader">
          <div>
            <h1 className="title">Change Market Schedule</h1>
            <p className="muted" style={{ marginTop: 6 }}>
              Manage market hours, closures, and admin override.
            </p>
          </div>
          <button className="btn" onClick={loadStatus}>
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

        {loading || !status ? (
          <p className="muted" style={{ marginTop: 14 }}>
            Loading market status...
          </p>
        ) : (
          <>
            {/* Current Status */}
            <div style={{ marginTop: 16 }}>
              <div className="kv">
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    gap: 14,
                    flexWrap: "wrap",
                    alignItems: "center",
                  }}
                >
                  <div>
                    <div className="k">Current Status</div>
                    <div style={{ marginTop: 10 }}>
                      <div className="muted" style={{ marginBottom: 6 }}>
                        <b>Admin Override:</b> {overrideLabel}
                      </div>
                      <div>
                        <span className="muted">
                          <b>Market:</b>{" "}
                        </span>
                        <span style={{ fontWeight: 900 }}>
                          {marketLabel}
                        </span>{" "}
                        <span className="muted" style={{ opacity: 0.75 }}>
                          ({marketReason})
                        </span>
                      </div>
                    </div>
                  </div>

                  <button className="btn" onClick={toggleMarket}>
                    Toggle Open / Close (Admin Override)
                  </button>
                </div>
              </div>
            </div>

            {/* Controls */}
            <div style={{ marginTop: 16 }}>
              <div className="grid2">
                {/* Market Hours */}
                <div className="kv">
                  <div className="k">Market Hours</div>

                  <div
                    style={{
                      display: "flex",
                      gap: 10,
                      alignItems: "flex-end",
                      flexWrap: "wrap",
                      marginTop: 10,
                    }}
                  >
                    <div style={{ minWidth: 200 }}>
                      <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>
                        Open
                      </div>
                      <input
                        className="input"
                        type="time"
                        value={openTime}
                        onChange={(e) => setOpenTime(e.target.value)}
                      />
                    </div>

                    <div style={{ minWidth: 200 }}>
                      <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>
                        Close
                      </div>
                      <input
                        className="input"
                        type="time"
                        value={closeTime}
                        onChange={(e) => setCloseTime(e.target.value)}
                      />
                    </div>

                    <button className="btn" onClick={saveHours}>
                      Update Hours
                    </button>
                  </div>

                  <p className="muted" style={{ marginTop: 10, fontSize: 13 }}>
                    Times are in 24-hour format.
                  </p>
                </div>

                {/* Closed Dates */}
                <div className="kv">
                  <div className="k">Closed Dates</div>

                  <div
                    style={{
                      display: "flex",
                      gap: 10,
                      alignItems: "flex-end",
                      flexWrap: "wrap",
                      marginTop: 10,
                    }}
                  >
                    <div style={{ minWidth: 220 }}>
                      <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>
                        Add a date
                      </div>
                      <input
                        className="input"
                        type="date"
                        value={newDate}
                        onChange={(e) => setNewDate(e.target.value)}
                      />
                    </div>

                    <button className="btn" onClick={addClosedDate}>
                      Add Date
                    </button>

                    <button className="btn" onClick={saveClosedDates}>
                      Save Closed Dates
                    </button>
                  </div>

                  {closedDatesSorted.length === 0 ? (
                    <p className="muted" style={{ marginTop: 10, fontSize: 13 }}>
                      No closed dates yet.
                    </p>
                  ) : (
                    <div style={{ marginTop: 12, display: "grid", gap: 8 }}>
                      {closedDatesSorted.map((d) => (
                        <div
                          key={d}
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            gap: 10,
                            padding: "10px 12px",
                            borderRadius: 12,
                            border: "1px solid rgba(255,255,255,0.10)",
                            background: "rgba(255,255,255,0.04)",
                          }}
                        >
                          <span style={{ fontWeight: 800 }}>{d}</span>
                          <button className="btn danger" onClick={() => removeClosedDate(d)}>
                            Remove
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  <p className="muted" style={{ marginTop: 10, fontSize: 13 }}>
                    Click <b>Save Closed Dates</b> to persist to the database.
                  </p>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}