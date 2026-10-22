// Every request to the FastAPI backend goes through apiFetch, so the login token,
// JSON handling and error messages are dealt with in one place.

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api'
const TOKEN_KEY = 'uor_hedge_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function saveToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

// An error from the backend, carrying the HTTP status and FastAPI's message
export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

export async function apiFetch(path, { method = 'GET', body, form } = {}) {
  const headers = {}
  const token = getToken()
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  let requestBody
  if (form) {
    requestBody = new URLSearchParams(form) // /login expects form fields, not JSON
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    requestBody = JSON.stringify(body)
  }

  let response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { method, headers, body: requestBody })
  } catch {
    throw new ApiError(0, 'Cannot reach the server. Is the backend running?')
  }

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    if (response.status === 401 && token) {
      clearToken() // the token expired or is invalid, so forget it
    }
    throw new ApiError(response.status, errorMessage(data, response.status))
  }
  return data
}

function errorMessage(data, status) {
  const detail = data?.detail
  if (typeof detail === 'string') {
    return detail // HTTPException(detail="...")
  }
  if (Array.isArray(detail)) {
    return detail.map((error) => error.msg).join('; ') // 422 validation errors
  }
  return `Request failed (${status})`
}