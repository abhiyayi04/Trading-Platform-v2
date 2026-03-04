import NavBar from "./NavBar";

export default function AppLayout({ user, onLogout, children }) {
  return (
    <div className="appShell">
      <NavBar user={user} onLogout={onLogout} />

      <main className="appMain">
        <div className="appContainer">{children}</div>
      </main>
    </div>
  );
}