import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { LogIn, Loader2 } from "lucide-react";
import { useAuth } from "../auth";
import { login as apiLogin } from "../api";
import { logger } from "../logger";

const log = logger("login");

export default function Login() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) {
      setError("Email is required");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const result = await apiLogin(email.trim());
      log.info("Authenticated, navigating to chat", { name: result.name });
      login({ token: result.token, user_id: result.user_id, name: result.name });
      navigate("/", { replace: true });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Login failed";
      log.warn("Login error", { email: email.trim(), error: msg });
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800 p-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mb-3 text-5xl">🧠</div>
          <h1 className="text-2xl font-bold text-white">
            Northwind Knowledge Assistant
          </h1>
          <p className="mt-2 text-sm text-slate-400">
            Sign in with your registered email to get started.
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="rounded-xl border border-slate-700 bg-slate-800/50 p-6 shadow-2xl backdrop-blur"
        >
          <div className="mb-5">
            <label htmlFor="login-email" className="mb-1.5 block text-sm font-medium text-slate-300">
              Email
            </label>
            <input
              id="login-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="alice@northwind.com"
              className="w-full rounded-lg border border-slate-600 bg-slate-700/50 px-3 py-2.5 text-white placeholder-slate-400 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {error && (
            <p className="mb-4 rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-400">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 font-medium text-white transition hover:bg-blue-500 disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <LogIn className="h-4 w-4" />
            )}
            Sign In
          </button>

          <p className="mt-4 text-center text-xs text-slate-500">
            Test account: <span className="text-slate-400">alice@northwind.com</span>
          </p>
        </form>
      </div>
    </div>
  );
}
