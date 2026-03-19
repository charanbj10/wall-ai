// ─────────────────────────────────────────────
// API HELPER
// All HTTP calls go through here.
// Bearer token is injected automatically from localStorage.
// ─────────────────────────────────────────────

async function http(path, opts = {}) {
  const token = localStorage.getItem('wai_token')

  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  Object.assign(headers, opts.headers || {})

  const res = await fetch(CONFIG.BASE_URL + path, { ...opts, headers })

  // Token expired → auto logout
  if (res.status === 401) {
    Auth.logout()
    throw new Error('Session expired — please sign in again')
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Server error ${res.status}`)
  }

  if (res.status === 204) return null
  return res.json()
}

// Build query string from an object, skipping empty values
// e.g. qs({ topic: 'bird', skip: 0 }) → '?topic=bird&skip=0'
function qs(params = {}) {
  const p = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== '' && v !== null && v !== undefined) p.set(k, v)
  })
  const s = p.toString()
  return s ? '?' + s : ''
}
