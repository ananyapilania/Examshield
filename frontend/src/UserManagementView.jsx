import React, { useState, useEffect } from "react";
import {
  Users,
  UserPlus,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Check,
  LoaderCircle,
  Layers,
  UserCheck,
  UserX,
  Shield,
  ShieldAlert,
} from "lucide-react";
import {
  getUsers,
  createUser,
  updateUserStatus,
  updateUserRole,
} from "./api";

/**
 * ExamShield Administrator User Management Dashboard
 * Enforces server-side RBAC, account activation/deactivation,
 * and role assignment with live audit logging.
 */
export default function UserManagementView({ currentUser }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // User creation form drawer state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newUser, setNewUser] = useState({
    username: "",
    email: "",
    password: "",
    role: "STAFF",
    is_active: true,
  });
  const [submitting, setSubmitting] = useState(false);

  const loadUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getUsers();
      setUsers(data);
    } catch (err) {
      setError(err.message || "Failed to load user list.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newUser.username.trim() || !newUser.email.trim() || !newUser.password) {
      setError("Please fill all required user fields.");
      return;
    }
    if (newUser.password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    setSubmitting(true);
    setError(null);
    setSuccess(null);
    try {
      await createUser({
        username: newUser.username.trim(),
        email: newUser.email.trim(),
        password: newUser.password,
        role: newUser.role,
        is_active: newUser.is_active,
      });
      setSuccess(`User '${newUser.username}' created successfully.`);
      setNewUser({
        username: "",
        email: "",
        password: "",
        role: "STAFF",
        is_active: true,
      });
      setShowCreateModal(false);
      await loadUsers();
    } catch (err) {
      setError(err.message || "Failed to create user account.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleStatus = async (user) => {
    if (user.user_id === currentUser.user_id) {
      setError("Administrators cannot deactivate their own active account.");
      return;
    }
    setError(null);
    setSuccess(null);
    try {
      await updateUserStatus(user.user_id, !user.is_active);
      setSuccess(`User '${user.username}' is now ${!user.is_active ? "ACTIVE" : "DEACTIVATED"}.`);
      await loadUsers();
    } catch (err) {
      setError(err.message || "Failed to update account status.");
    }
  };

  const handleToggleRole = async (user) => {
    const newRole = user.role === "ADMIN" ? "STAFF" : "ADMIN";
    setError(null);
    setSuccess(null);
    try {
      await updateUserRole(user.user_id, newRole);
      setSuccess(`User '${user.username}' role changed to ${newRole}.`);
      await loadUsers();
    } catch (err) {
      setError(err.message || "Failed to update user role.");
    }
  };

  return (
    <div className="space-y-8">
      {/* Header Section */}
      <section className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-purple-400/20 bg-purple-400/10 px-3 py-1 text-xs font-medium text-purple-300">
            <Users className="size-3.5" />
            Administrator Access Control
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white">
            Staff & Administrator Accounts
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Manage operational credentials, assign roles, and audit account status.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            id="toggle-create-user-modal"
            onClick={() => setShowCreateModal(!showCreateModal)}
            className="inline-flex items-center gap-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 text-xs font-semibold shadow-md shadow-blue-900/20 transition cursor-pointer"
          >
            <UserPlus className="size-3.5" />
            {showCreateModal ? "Cancel" : "Add New User"}
          </button>
          <button
            type="button"
            id="refresh-users-button"
            onClick={loadUsers}
            disabled={loading}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900/80 px-4 py-2 text-xs font-medium text-slate-200 hover:bg-slate-800 transition cursor-pointer"
          >
            <RefreshCw className={`size-3.5 ${loading ? "spin-slow text-blue-400" : ""}`} />
            Refresh
          </button>
        </div>
      </section>

      {/* Alerts */}
      {error && (
        <div className="flex items-center gap-3 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-300">
          <AlertTriangle className="size-5 shrink-0 text-rose-400" />
          <div>{error}</div>
        </div>
      )}

      {success && (
        <div className="flex items-center gap-3 rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-300">
          <CheckCircle2 className="size-5 shrink-0 text-emerald-400" />
          <div>{success}</div>
        </div>
      )}

      {/* Add User Drawer / Card */}
      {showCreateModal && (
        <div className="glass rounded-2xl border border-blue-500/30 p-6 drop-glow space-y-4">
          <div className="flex items-center gap-2 text-sm font-bold text-white border-b border-slate-800 pb-3">
            <UserPlus className="size-4 text-blue-400" />
            <span>Create New User Account</span>
          </div>
          <form onSubmit={handleCreate} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Username *</label>
              <input
                type="text"
                value={newUser.username}
                onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                placeholder="e.g. ops_proctor"
                required
                className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Email Address *</label>
              <input
                type="email"
                value={newUser.email}
                onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                placeholder="e.g. proctor@examshield.org"
                required
                className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Password (min 8 chars, hashed with Argon2id) *
              </label>
              <input
                type="password"
                value={newUser.password}
                onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                placeholder="Secure initial password"
                required
                className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Assigned Role</label>
              <select
                value={newUser.role}
                onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
                className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
              >
                <option value="STAFF">STAFF (Paper Verification & Permitted Records)</option>
                <option value="ADMIN">ADMIN (Full Security Controls & Audit Log)</option>
              </select>
            </div>
            <div className="md:col-span-2 flex items-center justify-between pt-2">
              <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={newUser.is_active}
                  onChange={(e) => setNewUser({ ...newUser, is_active: e.target.checked })}
                  className="rounded border-slate-700 bg-slate-900 text-blue-600 focus:ring-0"
                />
                <span>Account active immediately</span>
              </label>
              <button
                type="submit"
                disabled={submitting}
                className="inline-flex items-center gap-2 rounded-xl bg-blue-600 hover:bg-blue-500 px-5 py-2 text-xs font-bold text-white transition disabled:opacity-50 cursor-pointer"
              >
                {submitting ? <LoaderCircle className="size-3.5 spin-slow" /> : <Check className="size-3.5" />}
                Save User Account
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Users Table */}
      <div className="glass rounded-3xl border border-slate-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-800 bg-slate-950/60 text-xs uppercase tracking-wider text-slate-400 font-semibold">
              <tr>
                <th className="px-5 py-3.5">User Identity</th>
                <th className="px-5 py-3.5">Email</th>
                <th className="px-5 py-3.5">Role</th>
                <th className="px-5 py-3.5">Status</th>
                <th className="px-5 py-3.5">Created</th>
                <th className="px-5 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {users.map((u) => {
                const isSelf = u.user_id === currentUser.user_id;
                return (
                  <tr key={u.user_id} className="transition hover:bg-slate-900/40">
                    <td className="px-5 py-3.5">
                      <div className="font-semibold text-white flex items-center gap-2">
                        <span>{u.username}</span>
                        {isSelf && (
                          <span className="rounded bg-blue-500/20 px-1.5 py-0.5 text-[10px] text-blue-300 border border-blue-400/30">
                            Current User
                          </span>
                        )}
                      </div>
                      <div className="font-mono text-[11px] text-slate-500">{u.user_id}</div>
                    </td>
                    <td className="px-5 py-3.5 text-xs text-slate-300">{u.email}</td>
                    <td className="px-5 py-3.5">
                      <span
                        className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold ${
                          u.role === "ADMIN"
                            ? "border-purple-500/30 bg-purple-500/10 text-purple-300"
                            : "border-blue-500/30 bg-blue-500/10 text-blue-300"
                        }`}
                      >
                        {u.role}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      <span
                        className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${
                          u.is_active
                            ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                            : "border-rose-500/30 bg-rose-500/10 text-rose-300"
                        }`}
                      >
                        <span className={`size-1.5 rounded-full ${u.is_active ? "bg-emerald-400" : "bg-rose-400"}`} />
                        {u.is_active ? "Active" : "Deactivated"}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-xs text-slate-400 font-mono">
                      {u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}
                    </td>
                    <td className="px-5 py-3.5 text-right space-x-2">
                      <button
                        type="button"
                        onClick={() => handleToggleRole(u)}
                        disabled={isSelf}
                        title={isSelf ? "Cannot change own role" : `Switch role to ${u.role === "ADMIN" ? "STAFF" : "ADMIN"}`}
                        className="inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-800/80 px-2.5 py-1 text-xs text-slate-300 hover:text-white hover:bg-slate-700 disabled:opacity-40 transition cursor-pointer"
                      >
                        <Layers className="size-3" />
                        <span>{u.role === "ADMIN" ? "Demote to Staff" : "Promote to Admin"}</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => handleToggleStatus(u)}
                        disabled={isSelf}
                        title={isSelf ? "Cannot deactivate own account" : u.is_active ? "Deactivate account" : "Activate account"}
                        className={`inline-flex items-center gap-1 rounded-lg border px-2.5 py-1 text-xs transition disabled:opacity-40 cursor-pointer ${
                          u.is_active
                            ? "border-rose-500/30 bg-rose-500/10 text-rose-300 hover:bg-rose-500/20"
                            : "border-emerald-500/30 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20"
                        }`}
                      >
                        {u.is_active ? (
                          <>
                            <UserX className="size-3" /> Deactivate
                          </>
                        ) : (
                          <>
                            <UserCheck className="size-3" /> Activate
                          </>
                        )}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
