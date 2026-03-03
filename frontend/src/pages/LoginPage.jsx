import { useState } from "react";
import { Link } from "react-router-dom";

export default function LoginPage({ onLogin, error }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  return (
    <div style={{ maxWidth: 400, margin: "100px auto", fontFamily: "Arial" }}>
      <h2>Login</h2>
      {error && <p style={{ color: "red" }}>{error}</p>}

      <input
        placeholder="Email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        style={{ width: "100%", padding: 10, marginBottom: 10 }}
      />

      <input
        type="password"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        style={{ width: "100%", padding: 10, marginBottom: 10 }}
      />

      <button
        onClick={() => onLogin(email, password)}
        style={{ width: "100%", padding: 10 }}
      >
        Login
      </button>
      <p style={{ marginTop: 12 }}>
        Don’t have an account? <Link to="/register">Register</Link>
        </p>
    </div>
  );
}