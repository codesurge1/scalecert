import { useState } from "react";
import { supabase, API_BASE } from "./supabaseClient";

export default function App() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [session, setSession] = useState(null);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  async function login(e) {
    e.preventDefault();
    setError(null);
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      setError(error.message);
      return;
    }
    setSession(data.session);
  }

  async function call(path, authed) {
    setResult(null);
    setError(null);
    try {
      const headers = authed ? { Authorization: `Bearer ${session.access_token}` } : {};
      const res = await fetch(`${API_BASE}${path}`, { headers });
      const body = await res.json();
      setResult({ path, status: res.status, body });
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div style={{ fontFamily: "monospace", padding: "2rem", maxWidth: 640 }}>
      <h1>ScaleCert — walking skeleton</h1>

      {!session ? (
        <form onSubmit={login}>
          <div>
            <input
              placeholder="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div>
            <input
              placeholder="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <button type="submit">Log in</button>
        </form>
      ) : (
        <div>
          <p>Logged in as {session.user.email}</p>
          <button onClick={() => call("/health", false)}>Call /health</button>{" "}
          <button onClick={() => call("/whoami", true)}>Call /whoami</button>{" "}
          <button onClick={() => call("/whoami/debug", true)}>Call /whoami/debug</button>
        </div>
      )}

      {error && <pre style={{ color: "red" }}>{error}</pre>}
      {result && <pre>{JSON.stringify(result, null, 2)}</pre>}
    </div>
  );
}
