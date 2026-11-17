const API_BASE = "/api";

export async function api(path, options = {}) {
  const { token: suppliedToken, ...requestOptions } = options;
  const token = suppliedToken ?? window.localStorage.getItem("restaurant-token");
  const response = await fetch(`${API_BASE}${path}`, {
    ...requestOptions,
    headers: {
      ...(requestOptions.body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...requestOptions.headers,
    },
  });

  if (response.status === 204) return null;
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(payload?.detail || `Request failed (${response.status})`);
  }
  return payload;
}
