import { useState } from "react";
import { Link } from "react-router-dom";

export default function LoginPage({ onLogin, error }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  function submit(e) {
    e.preventDefault();
    onLogin(email, password);
  }

  return (
    <div className="appShell">
      <main className="authWrap">
        <div className="authCard">
          <div className="panel">
            <div>
              <h1 className="title">Welcome back</h1>
              <p className="muted" style={{ marginTop: 6 }}>
                Sign in to continue to your portfolio.
              </p>
            </div>

            {error && (
              <div className="alert bad" style={{ marginTop: 12 }}>
                {error}
              </div>
            )}

            <form className="formGrid" onSubmit={submit}>
              <div>
                <label className="label">Email</label>
                <input
                  className="input"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                />
              </div>

              <div>
                <label className="label">Password</label>
                <input
                  className="input"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                />
              </div>

              <button className="btn btnFull" type="submit">
                Login
              </button>
            </form>

            <p className="muted" style={{ marginTop: 14 }}>
              Don’t have an account?{" "}
              <Link to="/register" style={{ color: "rgba(255,255,255,0.92)", fontWeight: 800 }}>
                Register
              </Link>
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}