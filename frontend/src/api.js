/**
 * ExamShield API Client
 * Connects the React frontend to the FastAPI backend service with
 * authentication headers, session management, and RBAC support.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const TOKEN_KEY = "examshield_auth_token";
const USER_KEY = "examshield_auth_user";

// =========================================================================
// SESSION STORAGE HELPERS
// =========================================================================

export function getAuthToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setAuthToken(token) {
  try {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  } catch (err) {
    console.error("Failed to persist token:", err);
  }
}

export function getStoredUser() {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setStoredUser(user) {
  try {
    if (user) {
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(USER_KEY);
    }
  } catch (err) {
    console.error("Failed to persist user:", err);
  }
}

export function clearSession() {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  } catch (err) {
    console.error("Failed to clear session:", err);
  }
}

/**
 * Return headers with Bearer token injected if present
 */
function getAuthHeaders(customHeaders = {}) {
  const headers = { ...customHeaders };
  const token = getAuthToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

/**
 * Helper to handle fetch responses and extract error details
 */
async function handleResponse(response) {
  if (!response.ok) {
    let errorMessage = `HTTP Error ${response.status}: ${response.statusText}`;
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        if (typeof errorData.detail === "string") {
          errorMessage = errorData.detail;
        } else if (Array.isArray(errorData.detail)) {
          errorMessage = errorData.detail.map((err) => `${err.loc?.join(".") || "field"}: ${err.msg}`).join("; ");
        }
      }
    } catch {
      // Non-JSON response, keep default message
    }

    const error = new Error(errorMessage);
    error.status = response.status;

    // Handle session expiration
    if (response.status === 401 && typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("examshield-session-expired", { detail: { message: errorMessage } }));
    }

    throw error;
  }
  return response.json();
}

// =========================================================================
// AUTHENTICATION API CALLS
// =========================================================================

/**
 * Authenticate staff or administrator
 * POST /auth/login
 */
export async function login(usernameOrEmail, password) {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      username_or_email: usernameOrEmail,
      password: password,
    }),
  });

  const data = await handleResponse(response);
  if (data.access_token) {
    setAuthToken(data.access_token);
    setStoredUser(data.user);
  }
  return data;
}

/**
 * Logout and invalidate session server-side
 * POST /auth/logout
 */
export async function logout() {
  try {
    const token = getAuthToken();
    if (token) {
      await fetch(`${API_BASE_URL}/auth/logout`, {
        method: "POST",
        headers: getAuthHeaders({ Accept: "application/json" }),
      });
    }
  } catch (err) {
    console.warn("Logout request error (proceeding with local cleanup):", err);
  } finally {
    clearSession();
  }
}

/**
 * Get profile of currently authenticated user
 * GET /auth/me
 */
export async function getCurrentUser() {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    method: "GET",
    headers: getAuthHeaders({ Accept: "application/json" }),
  });
  const user = await handleResponse(response);
  setStoredUser(user);
  return user;
}

// =========================================================================
// USER MANAGEMENT API CALLS (ADMIN ONLY)
// =========================================================================

/**
 * List all users (ADMIN only)
 * GET /users
 */
export async function getUsers() {
  const response = await fetch(`${API_BASE_URL}/users`, {
    method: "GET",
    headers: getAuthHeaders({ Accept: "application/json" }),
  });
  return handleResponse(response);
}

/**
 * Create a new user account (ADMIN only)
 * POST /users
 */
export async function createUser(userData) {
  const response = await fetch(`${API_BASE_URL}/users`, {
    method: "POST",
    headers: getAuthHeaders({
      "Content-Type": "application/json",
      Accept: "application/json",
    }),
    body: JSON.stringify(userData),
  });
  return handleResponse(response);
}

/**
 * Activate or deactivate a user (ADMIN only)
 * PATCH /users/{userId}/status
 */
export async function updateUserStatus(userId, isActive) {
  const response = await fetch(`${API_BASE_URL}/users/${encodeURIComponent(userId)}/status`, {
    method: "PATCH",
    headers: getAuthHeaders({
      "Content-Type": "application/json",
      Accept: "application/json",
    }),
    body: JSON.stringify({ is_active: isActive }),
  });
  return handleResponse(response);
}

/**
 * Update user role (ADMIN only)
 * PATCH /users/{userId}/role
 */
export async function updateUserRole(userId, role) {
  const response = await fetch(`${API_BASE_URL}/users/${encodeURIComponent(userId)}/role`, {
    method: "PATCH",
    headers: getAuthHeaders({
      "Content-Type": "application/json",
      Accept: "application/json",
    }),
    body: JSON.stringify({ role: role }),
  });
  return handleResponse(response);
}

// =========================================================================
// EXAM OPERATIONS (AUTHENTICATED)
// =========================================================================

/**
 * Check backend health status
 * GET /
 */
export async function checkHealth() {
  const response = await fetch(`${API_BASE_URL}/`, {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  return handleResponse(response);
}

/**
 * Fetch all registered examination records
 * GET /exams (Staff & Admin)
 */
export async function getRegisteredExams() {
  const response = await fetch(`${API_BASE_URL}/exams`, {
    method: "GET",
    headers: getAuthHeaders({ Accept: "application/json" }),
  });
  return handleResponse(response);
}

/**
 * Register a new examination paper
 * POST /register-exam (Admin Only)
 * @param {FormData} formData
 */
export async function registerExamPaper(formData) {
  const response = await fetch(`${API_BASE_URL}/register-exam`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: formData,
  });
  return handleResponse(response);
}

/**
 * Verify candidate examination paper integrity against registered baseline
 * POST /verify-exam/{exam_id} (Staff & Admin)
 * @param {string} examId
 * @param {File} file
 */
export async function verifyExamPaper(examId, file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/verify-exam/${encodeURIComponent(examId)}`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: formData,
  });
  return handleResponse(response);
}

/**
 * Retrieve system audit trail logs
 * GET /audit-logs (Admin Only)
 * @param {string} [examId] - Optional exam_id filter
 */
export async function getAuditLogs(examId = null) {
  const url = examId
    ? `${API_BASE_URL}/audit-logs?exam_id=${encodeURIComponent(examId)}`
    : `${API_BASE_URL}/audit-logs`;
  const response = await fetch(url, {
    method: "GET",
    headers: getAuthHeaders({ Accept: "application/json" }),
  });
  return handleResponse(response);
}

export { API_BASE_URL };
