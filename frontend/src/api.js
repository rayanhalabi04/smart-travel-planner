const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

export class UnauthorizedError extends ApiError {
  constructor(message = "Your session expired. Please log in again.") {
    super(message, 401, null);
    this.name = "UnauthorizedError";
  }
}

function extractErrorMessage(payload, fallbackMessage) {
  if (!payload) {
    return fallbackMessage;
  }

  if (typeof payload === "string") {
    return payload;
  }

  if (typeof payload.detail === "string") {
    return payload.detail;
  }

  if (Array.isArray(payload.detail)) {
    return payload.detail
      .map((item) => (typeof item === "string" ? item : item.msg || JSON.stringify(item)))
      .join(", ");
  }

  return fallbackMessage;
}

async function request(path, { method = "GET", body, token } = {}) {
  const headers = {};
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    if (response.status === 401) {
      throw new UnauthorizedError();
    }

    const message = extractErrorMessage(payload, "Request failed. Please try again.");
    throw new ApiError(message, response.status, payload);
  }

  return payload;
}

export function register(email, password) {
  return request("/api/auth/register", {
    method: "POST",
    body: { email, password },
  });
}

export function login(email, password) {
  return request("/api/auth/login", {
    method: "POST",
    body: { email, password },
  });
}

export function runAgent(inputText, token) {
  return request("/api/agent/run", {
    method: "POST",
    token,
    body: { input_text: inputText },
  });
}

export function getRunTools(runId, token) {
  return request(`/api/agent/runs/${runId}/tools`, {
    method: "GET",
    token,
  });
}
