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

  async function handleRegister() {
    const result = await onRegister(
      fullName,
      username,
      email,
      password,
      role,
      adminKey
    );

    if (result === "SUCCESS") {
      setSuccess(true);
    }
  }

  if (success) {
    return (
      <div style={{ maxWidth: 400, margin: "100px auto", fontFamily: "Arial" }}>
        <h2>Account Created</h2>
        <p style={{ color: "green" }}>
          Registration successful. You can now log in.
        </p>

        <Link to="/login">
          <button style={{ width: "100%", padding: 10, marginTop: 10 }}>
            Go to Login
          </button>
        </Link>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 400, margin: "100px auto", fontFamily: "Arial" }}>
      <h2>Create Account</h2>

      {error && <p style={{ color: "red" }}>{error}</p>}

      <input
        placeholder="Full name"
        value={fullName}
        onChange={(e) => setFullName(e.target.value)}
        style={{ width: "100%", padding: 10, marginBottom: 10 }}
      />

      <input
        placeholder="Username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        style={{ width: "100%", padding: 10, marginBottom: 10 }}
      />

      <input
        placeholder="Email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        style={{ width: "100%", padding: 10, marginBottom: 10 }}
      />

      <input
        type="password"
        placeholder="Password (min 6 chars)"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        style={{ width: "100%", padding: 10, marginBottom: 10 }}
      />

      <div style={{ marginBottom: 10 }}>
        <label style={{ display: "block", marginBottom: 6, color: "#333" }}>
          Account type
        </label>
        <select
          value={role}
          onChange={(e) => setRole(e.target.value)}
          style={{ width: "100%", padding: 10 }}
        >
          <option value="customer">Customer</option>
          <option value="admin">Admin</option>
        </select>
      </div>

      {role === "admin" && (
        <input
          placeholder="Admin secret key"
          value={adminKey}
          onChange={(e) => setAdminKey(e.target.value)}
          style={{ width: "100%", padding: 10, marginBottom: 10 }}
        />
      )}

      <button onClick={handleRegister} style={{ width: "100%", padding: 10 }}>
        Register
      </button>

      <p style={{ marginTop: 12 }}>
        Already have an account? <Link to="/login">Login</Link>
      </p>
    </div>
  );
}