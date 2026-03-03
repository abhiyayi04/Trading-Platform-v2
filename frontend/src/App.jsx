import { useEffect, useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import "./App.css";
import { tradingApi } from "./api/tradingApi";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import FundsPage from "./pages/FundsPage";
import RegisterPage from "./pages/RegisterPage";

function App() {
  const [user, setUser] = useState(null);
  const [stocks, setStocks] = useState([]);
  const [orders, setOrders] = useState([]);
  const [portfolio, setPortfolio] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [buyQty, setBuyQty] = useState({});
  const [sellQty, setSellQty] = useState({});

  const [market, setMarket] = useState(null);

  async function refreshMe() {
    const me = await tradingApi.me();
    if (me.authenticated) setUser(me);
  }

  async function loadStocks() {
    const data = await tradingApi.stocks();
    setStocks(data);
  }

  async function loadOrders() {
    const data = await tradingApi.orders();
    setOrders(data);
  }

  async function loadPortfolio() {
    const data = await tradingApi.portfolio();
    setPortfolio(data);
  }

  async function loadMarketStatus() {
    const data = await tradingApi.marketStatus();
    setMarket(data);
  }

  // ---------- AUTH CHECK ----------
  useEffect(() => {
    async function init() {
      try {
        const me = await tradingApi.me();
        if (me.authenticated) {
          setUser(me);
          await loadStocks();
          await loadOrders();
          await loadPortfolio();
          await loadMarketStatus();
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    init();
  }, []);

  useEffect(() => {
    if (!user) return;

    const id = setInterval(async () => {
      try {
        await loadStocks();
        await loadOrders();
        await loadPortfolio();
        await refreshMe();
        await loadMarketStatus();
      } catch (e) {
        // ignore polling errors
      }
    }, 5000);

    return () => clearInterval(id);
  }, [user]);

  async function register(fullName, username, email, password) {
    setError("");
    setNotice("");

    try {
      await tradingApi.register(fullName, username, email, password);
      return "SUCCESS";
    } catch (e) {
      setError(e.message);
    }
  }

  // ---------- LOGIN ----------
  async function login(emailInput, passwordInput) {
    setError("");
    setNotice("");
    try {
      const data = await tradingApi.login(emailInput, passwordInput);
      setUser(data.user);
      await loadStocks();
      await loadOrders();
      await loadPortfolio();
    } catch (e) {
      setError(e.message);
    }
  }

  // ---------- LOGOUT ----------
  async function logout() {
    try {
      await tradingApi.logout();
    } catch (e) {
      // ignore logout errors; we'll still reset UI
    }
    setUser(null);
    setStocks([]);
    setOrders([]);
    setPortfolio(null);
    setNotice("");
    setError("");
  }

  // ---------- PLACE BUY ORDER ----------
  async function placeBuyOrder(stockId) {
    setError("");
    setNotice("");

    const qty = Number(buyQty[stockId] ?? 1);
    if (!qty || qty <= 0) {
      setError("Quantity must be a positive number.");
      return;
    }

    try {
      const data = await tradingApi.placeOrder("BUY", stockId, qty);

      setNotice(
        `Buy order placed (PENDING): ${qty} shares @ $${Number(
          data.order.price_locked
        ).toFixed(2)}`
      );

      await loadOrders();
      await refreshMe();

      setBuyQty((prev) => ({ ...prev, [stockId]: 1 }));
    } catch (e) {
      setError(e.message);
    }
  }

  async function placeSellOrder(stockId) {
    setError("");
    setNotice("");

    const qty = Number(sellQty[stockId] ?? 1);
    if (!qty || qty <= 0) {
      setError("Quantity must be a positive number.");
      return;
    }

    try {
      const data = await tradingApi.placeOrder("SELL", stockId, qty);

      setNotice(
        `Sell order placed (PENDING): ${qty} shares @ $${Number(
          data.order.price_locked
        ).toFixed(2)}`
      );

      await loadOrders();
      await refreshMe();

      setSellQty((prev) => ({ ...prev, [stockId]: 1 }));
    } catch (e) {
      setError(e.message);
    }
  }

  // ---------- EXECUTE / CANCEL ----------
  async function executeOrder(orderId) {
    setError("");
    setNotice("");
    try {
      const data = await tradingApi.executeOrder(orderId);
      setNotice(data.message || "Order executed.");

      await loadOrders();
      await loadPortfolio();
      await refreshMe();
      await loadStocks();
    } catch (e) {
      setError(e.message);
    }
  }

  async function cancelOrder(orderId) {
    setError("");
    setNotice("");
    try {
      const data = await tradingApi.cancelOrder(orderId);
      setNotice(data.message || "Order canceled.");
      await loadOrders();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <>
      {loading ? (
        <p style={{ padding: 20 }}>Loading...</p>
      ) : (
        <Routes>
          <Route
            path="/register"
            element={
              user ? (
                <Navigate to="/dashboard" replace />
              ) : (
                <RegisterPage onRegister={register} error={error} />
              )
            }
          />
          <Route
            path="/login"
            element={
              user ? (
                <Navigate to="/dashboard" replace />
              ) : (
                <LoginPage onLogin={login} error={error} />
              )
            }
          />

          <Route
            path="/dashboard"
            element={
              user ? (
                <DashboardPage
                  user={user}
                  stocks={stocks}
                  orders={orders}
                  portfolio={portfolio}
                  buyQty={buyQty}
                  setBuyQty={setBuyQty}
                  sellQty={sellQty}
                  setSellQty={setSellQty}
                  notice={notice}
                  error={error}
                  market={market}
                  onLogout={logout}
                  onPlaceBuy={placeBuyOrder}
                  onPlaceSell={placeSellOrder}
                  onExecuteOrder={executeOrder}
                  onCancelOrder={cancelOrder}
                />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />

          {/* Default route */}
          <Route
            path="*"
            element={<Navigate to={user ? "/dashboard" : "/login"} replace />}
          />

          <Route
            path="/funds"
            element={
              user ? (
                <FundsPage user={user} onLogout={logout} />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
        </Routes>
      )}
    </>
  );
}

export default App;