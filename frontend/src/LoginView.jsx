import React, { useState } from "react";
import {
  ShieldCheck,
  ShieldAlert,
  LockKeyhole,
  User,
  Eye,
  EyeOff,
  LoaderCircle,
  AlertTriangle,
  Clock3,
  BadgeCheck,
} from "lucide-react";
import { login } from "./api";

/**
 * ExamShield Professional Cybersecurity Login Gateway
 * Supports Staff and Admin authentication with Argon2 backend validation,
 * expiring signed tokens, and connection error monitoring.
 */
export default function LoginView({
  backendStatus,
  sessionNotice,
  onLoginSuccess,
}) {
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const cleanId = identifier.trim();

    if (!cleanId) {
      setError("Please enter your username or email address.");
      return;
    }
    if (!password) {
      setError("Please enter your password.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await login(cleanId, password);
      onLoginSuccess(data.user);
    } catch (err) {
      if (err.status === 401) {
        // Generic response prevents account harvesting
        setError("Invalid username, email, or password.");
      } else if (err.status === 403) {
        setError(err.message || "Account is deactivated. Please contact an administrator.");
      } else if (
        !err.status ||
        err.message?.includes("Failed to fetch") ||
        err.message?.includes("NetworkError")
      ) {
        setError(
          "Cannot connect to the ExamShield security backend. Please verify the FastAPI service is running on 127.0.0.1:8000."
        );
      } else {
        setError(err.message || "An authentication error occurred. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid-bg flex flex-col justify-center items-center px-4 py-12 text-slate-100">
      <div className="w-full max-w-md space-y-6">
        {/* Branding & Visual Header */}
        <div className="text-center space-y-3">
          <div className="mx-auto grid size-16 place-items-center rounded-2xl bg-blue-600/15 ring-1 ring-blue-400/30 shadow-lg shadow-blue-950/60 drop-glow">
            <ShieldCheck className="size-9 text-blue-400" />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
              ExamShield
            </h1>
            <p className="text-[10px] uppercase tracking-[0.25em] text-blue-400 font-semibold mt-1">
              Examination Paper Security Platform
            </p>
          </div>
          <p className="text-xs text-slate-400 max-w-xs mx-auto">
            Authorized Staff & Administrator Gateway. Cryptographic integrity and access monitoring active.
          </p>
        </div>

        {/* System Warnings & Notices */}
        {backendStatus === "offline" && (
          <div className="flex items-center gap-2.5 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-xs text-rose-300">
            <AlertTriangle className="size-4 shrink-0 text-rose-400" />
            <span>FastAPI Backend Offline (127.0.0.1:8000). Ensure the backend server is active.</span>
          </div>
        )}

        {sessionNotice && (
          <div className="flex items-center gap-2.5 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-xs text-amber-300">
            <Clock3 className="size-4 shrink-0 text-amber-400" />
            <span>{sessionNotice}</span>
          </div>
        )}

        {error && (
          <div className="flex items-start gap-2.5 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-xs text-rose-300">
            <ShieldAlert className="size-4 shrink-0 text-rose-400 mt-0.5" />
            <div className="flex-1">{error}</div>
          </div>
        )}

        {/* Main Login Glass Card */}
        <div className="glass rounded-2xl border border-slate-800/80 p-6 sm:p-8 drop-glow">
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Username / Email */}
            <div>
              <label
                htmlFor="login-identifier"
                className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2"
              >
                Username or Email
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-500">
                  <User className="size-4" />
                </div>
                <input
                  id="login-identifier"
                  type="text"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  placeholder="e.g. security_admin or admin@examshield.org"
                  required
                  autoFocus
                  className="w-full rounded-xl border border-slate-700/80 bg-slate-900/90 pl-10 pr-4 py-2.5 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 transition"
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label
                htmlFor="login-password"
                className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2"
              >
                Password
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-500">
                  <LockKeyhole className="size-4" />
                </div>
                <input
                  id="login-password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your security password"
                  required
                  className="w-full rounded-xl border border-slate-700/80 bg-slate-900/90 pl-10 pr-10 py-2.5 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 transition"
                />
                <button
                  type="button"
                  id="toggle-password-visibility"
                  onClick={() => setShowPassword(!showPassword)}
                  tabIndex={-1}
                  className="absolute inset-y-0 right-0 flex items-center pr-3 text-slate-400 hover:text-slate-200 transition"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              </div>
            </div>

            {/* Login Button */}
            <button
              type="submit"
              id="login-submit-button"
              disabled={loading || backendStatus === "offline"}
              className="w-full flex items-center justify-center gap-2 rounded-xl bg-blue-600 hover:bg-blue-500 active:scale-[0.99] disabled:opacity-50 disabled:pointer-events-none text-white px-5 py-3 text-sm font-semibold shadow-md shadow-blue-900/30 transition cursor-pointer"
            >
              {loading ? (
                <>
                  <LoaderCircle className="size-4 spin-slow" />
                  <span>Verifying Credentials...</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="size-4" />
                  <span>Sign In to ExamShield</span>
                </>
              )}
            </button>
          </form>

          {/* Security Features Info */}
          <div className="mt-6 pt-5 border-t border-slate-800/80 text-[11px] text-slate-400 space-y-2">
            <div className="flex items-center gap-2">
              <BadgeCheck className="size-3.5 text-blue-400 shrink-0" />
              <span>Argon2id cryptographic password protection</span>
            </div>
            <div className="flex items-center gap-2">
              <BadgeCheck className="size-3.5 text-blue-400 shrink-0" />
              <span>Signed expiring JWT sessions & RBAC enforcement</span>
            </div>
            <div className="flex items-center gap-2">
              <BadgeCheck className="size-3.5 text-blue-400 shrink-0" />
              <span>All authentication events immutably audited</span>
            </div>
          </div>
        </div>

        {/* Security Footer Notice */}
        <p className="text-center text-[11px] text-slate-500">
          ExamShield Core Security System • Unauthorized access is strictly prohibited
        </p>
      </div>
    </div>
  );
}
