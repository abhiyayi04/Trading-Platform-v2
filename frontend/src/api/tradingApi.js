import { fetchJSON } from "./client";

export const tradingApi = {
  // ---- auth ----
  me: () => fetchJSON("/api/me"),

  register: (full_name, username, email, password, role = "customer", admin_key = "") =>
    fetchJSON("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ full_name, username, email, password, role, admin_key }),
    }),

  login: (email, password) =>
    fetchJSON("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    }),

  logout: () =>
    fetchJSON("/api/auth/logout", {
      method: "POST",
    }),

  // ---- read data ----
  stocks: () => fetchJSON("/api/stocks"),
  orders: () => fetchJSON("/api/orders"),
  portfolio: () => fetchJSON("/api/portfolio"),
  funds: () => fetchJSON("/api/funds"),
  marketStatus: () => fetchJSON("/api/market/status"),
  adminStocks: () => fetchJSON("/api/admin/stocks"),

  // ---- actions ----
  placeOrder: (side, stock_id, quantity) =>
    fetchJSON("/api/orders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ side, stock_id, quantity }),
    }),

  executeOrder: (orderId) =>
    fetchJSON(`/api/orders/${orderId}/execute`, { method: "POST" }),

  cancelOrder: (orderId) =>
    fetchJSON(`/api/orders/${orderId}/cancel`, { method: "POST" }),

  deposit: (amount, payment_method_id = null) =>
    fetchJSON("/api/funds/deposit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amount, payment_method_id }),
    }),

  withdraw: (amount) =>
    fetchJSON("/api/funds/withdraw", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amount }),
    }),

  adminToggleMarket: () =>
  fetchJSON("/api/admin/market/toggle", {
    method: "POST",
  }),

  adminCreateStock: (company_name, symbol, price, volume) =>
  fetchJSON("/api/admin/stocks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ company_name, symbol, price, volume }),
  }),

adminDeleteStock: (stockId) =>
  fetchJSON(`/api/admin/stocks/${stockId}`, {
    method: "DELETE",
  }),

adminSetMarketHours: (open_time, close_time) =>
  fetchJSON("/api/admin/market/hours", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ open_time, close_time }),
  }),

adminSetClosedDates: (dates) =>
  fetchJSON("/api/admin/market/closed-dates", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dates }),
  }),
};