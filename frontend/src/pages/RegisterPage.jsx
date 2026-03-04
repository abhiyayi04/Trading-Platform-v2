import { useState } from "react";
import { Link } from "react-router-dom";

export default function RegisterPage({ onRegister, error }) {
  const [fullName, setFullName] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [role, setRole] = useState("customer");
  const [adminKey, setAdminKey] = useState("");

  const [success, setSuccess] = useState(false);

  async function handleRegister(e) {
    e.preventDefault();

    const result = await onRegister(
      fullName,
      username,
      email,
      password,
      role,
      adminKey
    );

    if (result === "SUCCESS") setSuccess(true);
  }

  if (success) {
    return (
      <div className="appShell">
        <main className="authWrap">
          <div className="authCard">
            <div className="panel">
              <h1 className="title">Account created</h1>
              <p className="muted" style={{ marginTop: 6 }}>
                Registration successful. You can now log in.
              </p>

              <Link to="/login" style={{ textDecoration: "none" }}>
                <button className="btn btnFull" style={{ marginTop: 14 }}>
                  Go to Login
                </button>
              </Link>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="appShell">
      <main className="authWrap">
        <div className="authCard">
          <div className="panel">
            <div>
              <h1 className="title">Create account</h1>
              <p className="muted" style={{ marginTop: 6 }}>
                Set up your account to start trading.
              </p>
            </div>

            {error && (
              <div className="alert bad" style={{ marginTop: 12 }}>
                {error}
              </div>
            )}

            <form className="formGrid" onSubmit={handleRegister}>
              <div>
                <label className="label">Full name</label>
                <input
                  className="input"
                  placeholder="Abhi Chandra Yayi"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  autoComplete="name"
                />
              </div>

              <div>
                <label className="label">Username</label>
                <input
                  className="input"
                  placeholder="student353"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                />
              </div>

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
                  placeholder="min 6 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="new-password"
                />
              </div>

              <div>
                <label className="label">Account type</label>
                <select
                  className="select"
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                >
                  <option value="customer">Customer</option>
                  <option value="admin">Admin</option>
                </select>
              </div>

              {role === "admin" && (
                <div>
                  <label className="label">Admin secret key</label>
                  <input
                    className="input"
                    placeholder="Enter admin key"
                    value={adminKey}
                    onChange={(e) => setAdminKey(e.target.value)}
                  />
                </div>
              )}

              <button className="btn btnFull" type="submit">
                Register
              </button>
            </form>

            <p className="muted" style={{ marginTop: 14 }}>
              Already have an account?{" "}
              <Link to="/login" style={{ color: "rgba(255,255,255,0.92)", fontWeight: 800 }}>
                Login
              </Link>
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}