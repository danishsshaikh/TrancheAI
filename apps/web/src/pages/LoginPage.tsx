import { useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../app/AuthContext";

export function LoginPage() {
  const auth = useAuth();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (auth.token) return <Navigate to={(location.state as { from?: string } | null)?.from ?? "/"} replace />;

  return (
    <main className="flex min-h-screen items-center justify-center bg-surface px-4">
      <form
        className="w-full max-w-sm space-y-4 rounded-md border border-line bg-panel p-5"
        onSubmit={async (event) => {
          event.preventDefault();
          setLoading(true);
          setError("");
          try {
            await auth.login(email, password);
          } catch (err) {
            setError(err instanceof Error ? err.message : "Login failed.");
          } finally {
            setLoading(false);
          }
        }}
      >
        <div>
          <p className="text-sm text-muted">TrancheAI</p>
          <h1 className="text-2xl font-semibold">Sign in</h1>
        </div>
        <label className="block text-sm font-medium">
          Email
          <input className="focus-ring mt-1 w-full rounded-md border border-line bg-surface px-3 py-2" value={email} onChange={(event) => setEmail(event.target.value)} />
        </label>
        <label className="block text-sm font-medium">
          Password
          <input className="focus-ring mt-1 w-full rounded-md border border-line bg-surface px-3 py-2" type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
        </label>
        {error ? <div className="rounded-md border border-danger p-2 text-sm text-danger">{error}</div> : null}
        <button className="focus-ring w-full rounded-md bg-accent px-4 py-2 text-sm font-medium text-surface" disabled={loading}>
          {loading ? "Signing in" : "Sign in"}
        </button>
      </form>
    </main>
  );
}
