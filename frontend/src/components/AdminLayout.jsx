import AdminNavBar from "./AdminNavBar";

export default function AdminLayout({ user, onLogout, children }) {
  return (
    <div className="appShell">
      <AdminNavBar user={user} onLogout={onLogout} />

      <main className="appMain">
        <div className="appContainer">{children}</div>
      </main>
    </div>
  );
}