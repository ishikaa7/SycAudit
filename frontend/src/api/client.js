import axios from "axios";

export const TOKEN_KEY = "sycaudit_token";
export const USER_KEY = "sycaudit_user";

const baseURL = import.meta.env.VITE_API_BASE_URL || "/api";

export const api = axios.create({
  baseURL,
  headers: { "Content-Type": "application/json" },
});

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || "null");
  } catch {
    return null;
  }
}

export function storeAuth(token, user) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function extractAuthPayload(data) {
  const d = data && typeof data === "object" ? data : {};
  const token = d.access_token || d.token || d.jwt || null;
  const user =
    d.user && typeof d.user === "object"
      ? {
          user_id: d.user.user_id ?? d.user.id ?? null,
          name: d.user.name ?? null,
          email: d.user.email ?? null,
          role: d.user.role ?? "user",
        }
      : d.name || d.email
        ? {
            user_id: d.user_id ?? d.id ?? null,
            name: d.name ?? null,
            email: d.email ?? null,
            role: d.role ?? "user",
          }
        : null;
  return { token, user };
}

export function errorMessage(error) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0];
    if (first?.msg) return first.msg;
  }
  if (error?.message) return error.message;
  return "Something went wrong. Please try again.";
}

api.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    const url = error?.config?.url || "";
    if (status === 401 && !url.includes("/auth/")) {
      clearAuth();
      if (!window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);