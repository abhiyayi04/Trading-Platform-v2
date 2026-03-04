import { useEffect, useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useNavigate } from "react-router-dom";
import "./App.css";
import { tradingApi } from "./api/tradingApi";

import RegisterPage from "./pages/RegisterPage";
import LoginPage from "./pages/LoginPage";

import PortfolioPage from "./pages/PortfolioPage";
import MarketPage from "./pages/MarketPage";
import TransactionsPage from "./pages/TransactionsPage";
import FundsPage from "./pages/FundsPage";
import ProfilePage from "./pages/ProfilePage";

import AdminDashboardPage from "./pages/AdminDashboardPage";
import AdminMarketPage from "./pages/AdminMarketPage";
import AdminStocksPage from "./pages/AdminStocksPage";

import AppLayout from "./components/AppLayout";
import AdminLayout from "./components/AdminLayout";

function App() {
  const navigate = useNavigate();
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

          const isAdmin = me.role === "admin";
          navigate(isAdmin ? "/admin" : "/portfolio", { replace: true });

          if (!isAdmin) {
            await loadStocks();
            await loadOrders();
            await loadPortfolio();
            await loadMarketStatus();
          }
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
    if (user.role === "admin") return;

    const id = setInterval(async () => {
      try {
        await loadStocks();
        await loadOrders();
        await loadPortfolio();
        await refreshMe();
        await loadMarketStatus();
      } catch (e) {
      }
    }, 10000);

    return () => clearInterval(id);
  }, [user?.id, user?.role]);

  async function register(fullName, username, email, password, role, adminKey) {
    setError("");
    setNotice("");

    try {
      await tradingApi.register(fullName, username, email, password, role, adminKey);
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

      const isAdmin = data.user.role === "admin";
      navigate(isAdmin ? "/admin" : "/portfolio", { replace: true });

      if (!isAdmin) {
        await loadStocks();
        await loadOrders();
        await loadPortfolio();
        await loadMarketStatus();
      }
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
    setMarket(null);
    setNotice("");
    setError("");
  }

  // NOTE: These are still here but we will move buy/sell UI into MarketPage/PortfolioPage in the next step.
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
          {/* ---------- AUTH ROUTES ---------- */}
          <Route
            path="/register"
            element={
              user ? (
                <Navigate to={user.role === "admin" ? "/admin" : "/portfolio"} replace />
              ) : (
                <RegisterPage onRegister={register} error={error} />
              )
            }
          />

          <Route
            path="/login"
            element={
              user ? (
                <Navigate to={user.role === "admin" ? "/admin" : "/portfolio"} replace />
              ) : (
                <LoginPage onLogin={login} error={error} />
              )
            }
          />

          {/* ---------- ADMIN ROUTES ---------- */}
          <Route
            path="/admin"
            element={
              !user ? (
                <Navigate to="/login" replace />
              ) : user.role !== "admin" ? (
                <Navigate to="/portfolio" replace />
              ) : (
                <AdminLayout user={user} onLogout={logout}>
                  <AdminDashboardPage user={user} />
                </AdminLayout>
              )
            }
          />

          <Route
            path="/admin/market"
            element={
              !user ? (
                <Navigate to="/login" replace />
              ) : user.role !== "admin" ? (
                <Navigate to="/portfolio" replace />
              ) : (
                <AdminLayout user={user} onLogout={logout}>
                  <AdminMarketPage user={user} />
                </AdminLayout>
              )
            }
          />

          <Route
            path="/admin/stocks"
            element={
              !user ? (
                <Navigate to="/login" replace />
              ) : user.role !== "admin" ? (
                <Navigate to="/portfolio" replace />
              ) : (
                <AdminLayout user={user} onLogout={logout}>
                  <AdminStocksPage user={user} />
                </AdminLayout>
              )
            }
          />

          {/* ---------- CUSTOMER ROUTES ---------- */}
          <Route
            path="/portfolio"
            element={
              !user ? (
                <Navigate to="/login" replace />
              ) : user.role === "admin" ? (
                <Navigate to="/admin" replace />
              ) : (
                <AppLayout user={user} onLogout={logout}>
                  <PortfolioPage />
                </AppLayout>
              )
            }
          />

          <Route
            path="/market"
            element={
              !user ? (
                <Navigate to="/login" replace />
              ) : user.role === "admin" ? (
                <Navigate to="/admin" replace />
              ) : (
                <AppLayout user={user} onLogout={logout}>
                  <MarketPage />
                </AppLayout>
              )
            }
          />

          <Route
            path="/funds"
            element={
              !user ? (
                <Navigate to="/login" replace />
              ) : user.role === "admin" ? (
                <Navigate to="/admin" replace />
              ) : (
                <AppLayout user={user} onLogout={logout}>
                  <FundsPage user={user} onLogout={logout} />
                </AppLayout>
              )
            }
          />

          <Route
            path="/transactions"
            element={
              !user ? (
                <Navigate to="/login" replace />
              ) : user.role === "admin" ? (
                <Navigate to="/admin" replace />
              ) : (
                <AppLayout user={user} onLogout={logout}>
                  <TransactionsPage />
                </AppLayout>
              )
            }
          />

          <Route
            path="/profile"
            element={
              !user ? (
                <Navigate to="/login" replace />
              ) : user.role === "admin" ? (
                <Navigate to="/admin" replace />
              ) : (
                <AppLayout user={user} onLogout={logout}>
                  <ProfilePage user={user} onLogout={logout} />
                </AppLayout>
              )
            }
          />

          {/* Default route */}
          <Route
            path="*"
            element={
              <Navigate
                to={
                  user
                    ? (user.role === "admin" ? "/admin" : "/portfolio")
                    : "/login"
                }
                replace
              />
            }
          />
        </Routes>
      )}
    </>
  );
}

export default App;