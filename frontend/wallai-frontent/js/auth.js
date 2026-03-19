// ─────────────────────────────────────────────
// AUTH MODULE
// Handles: signup, signin, logout, session restore
//
// Your API endpoints used:
//   POST /auth/signup  { email, name, password }
//   POST /auth/signin  { email, password }
// ─────────────────────────────────────────────

const Auth = (() => {

  // ── MODAL CONTROL ──────────────────────────
  function openModal(panel = 'login') {
    document.getElementById('authModal').classList.add('open')
    switchPanel(panel)
  }

  function closeModal() {
    document.getElementById('authModal').classList.remove('open')
  }

  function switchPanel(panel) {
    document.getElementById('loginPanel').style.display  = panel === 'login'  ? '' : 'none'
    document.getElementById('signupPanel').style.display = panel === 'signup' ? '' : 'none'
    document.getElementById('liErr').textContent = ''
    document.getElementById('suErr').textContent = ''
  }

  // ── SIGN UP ────────────────────────────────
  // POST /auth/signup
  // Body: { email, name, password }
  // Response: { message: "User created", uid: "..." }
  async function signup() {
    const name  = document.getElementById('suName').value.trim()
    const email = document.getElementById('suEmail').value.trim()
    const pass  = document.getElementById('suPass').value
    const errEl = document.getElementById('suErr')
    const btn   = document.getElementById('suBtn')

    errEl.textContent = ''
    if (!name || !email || !pass) { errEl.textContent = 'Please fill all fields'; return }
    if (pass.length < 8)          { errEl.textContent = 'Password needs 8+ characters'; return }

    btn.textContent = 'Creating…'; btn.disabled = true
    try {
      await http('/auth/signup', {
        method: 'POST',
        body: JSON.stringify({ email, name, password: pass })
      })
      // Auto-fill login form and switch
      document.getElementById('liEmail').value = email
      document.getElementById('liPass').value  = pass
      switchPanel('login')
      UI.toast('Account created! Sign in now.')
    } catch (e) {
      errEl.textContent = e.message
    } finally {
      btn.textContent = 'Create account'; btn.disabled = false
    }
  }

  // ── SIGN IN ────────────────────────────────
  // POST /auth/signin
  // Body: { email, password }
  // Response: { access_token, token_type, uid, email, name }
  async function signin() {
    const email = document.getElementById('liEmail').value.trim()
    const pass  = document.getElementById('liPass').value
    const errEl = document.getElementById('liErr')
    const btn   = document.getElementById('liBtn')

    errEl.textContent = ''
    if (!email || !pass) { errEl.textContent = 'Please fill all fields'; return }

    btn.textContent = 'Signing in…'; btn.disabled = true
    try {
      const data = await http('/auth/signin', {
        method: 'POST',
        body: JSON.stringify({ email, password: pass })
      })

      // Store token and user info from your exact response shape
      localStorage.setItem('wai_token', data.access_token)
      localStorage.setItem('wai_user', JSON.stringify({
        uid:   data.uid,
        email: data.email,
        name:  data.name,
      }))

      closeModal()
      updateNav()
      UI.toast(`Welcome back, ${data.name.split(' ')[0]}!`)

      // Reload images + fetch download history
      Images.load()
      Downloads.loadMine()

    } catch (e) {
      errEl.textContent = e.message
    } finally {
      btn.textContent = 'Sign in'; btn.disabled = false
    }
  }

  // ── LOGOUT ─────────────────────────────────
  function logout() {
    localStorage.removeItem('wai_token')
    localStorage.removeItem('wai_user')
    Downloads.clearMine()
    updateNav()
    UI.toast('Signed out')
    Images.load()
  }

  // ── NAV UPDATE ─────────────────────────────
  function updateNav() {
    const me = getUser()
    const el = document.getElementById('navRight')

    if (me) {
      const initials = me.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
      el.innerHTML = `
        <button class="btn btn-accent btn-sm" onclick="Upload.open()">
          + Upload
        </button>
        <div class="user-chip" onclick="Auth.toggleDropdown()" style="position:relative">
          <div class="ava">${initials}</div>
          <span class="uname">${me.name}</span>
        </div>
        <div id="userDropdown" style="
          display:none;position:absolute;top:54px;right:28px;
          background:var(--surface);border:1px solid var(--border);
          border-radius:12px;min-width:180px;z-index:200;
          box-shadow:0 8px 32px rgba(0,0,0,.4);overflow:hidden">
          <div style="padding:12px 16px;border-bottom:1px solid var(--border)">
            <div style="font-size:13px;font-weight:500;color:var(--text)">${me.name}</div>
            <div style="font-size:11px;color:var(--muted);margin-top:2px">${me.email}</div>
          </div>
          <div onclick="Downloads.openPage();Auth.toggleDropdown()" style="
            padding:11px 16px;font-size:13px;cursor:pointer;
            display:flex;align-items:center;gap:10px;
            border-bottom:1px solid var(--border);transition:background .15s"
            onmouseover="this.style.background='var(--surface2)'"
            onmouseout="this.style.background=''">
            <span style="font-size:15px">↓</span> My downloads
          </div>
          <div onclick="Auth.logout()" style="
            padding:11px 16px;font-size:13px;cursor:pointer;
            display:flex;align-items:center;gap:10px;
            color:var(--danger);transition:background .15s"
            onmouseover="this.style.background='var(--surface2)'"
            onmouseout="this.style.background=''">
            <span style="font-size:15px">→</span> Sign out
          </div>
        </div>`
    } else {
      el.innerHTML = `
        <button class="btn btn-ghost btn-sm" onclick="Auth.openModal('login')">Sign in</button>
        <button class="btn btn-accent btn-sm" onclick="Auth.openModal('signup')">Join free</button>`
    }
  }

  // ── DROPDOWN ───────────────────────────────
  function toggleDropdown() {
    const dd = document.getElementById('userDropdown')
    if (!dd) return
    const isOpen = dd.style.display === 'block'
    dd.style.display = isOpen ? 'none' : 'block'
    // Close when clicking outside
    if (!isOpen) {
      setTimeout(() => {
        document.addEventListener('click', function handler(e) {
          if (!dd.contains(e.target)) {
            dd.style.display = 'none'
            document.removeEventListener('click', handler)
          }
        })
      }, 0)
    }
  }

  // ── HELPERS ────────────────────────────────
  function getUser() {
    return JSON.parse(localStorage.getItem('wai_user') || 'null')
  }

  function getToken() {
    return localStorage.getItem('wai_token')
  }

  function isLoggedIn() {
    return !!getToken()
  }

  // Expose public API
  return { openModal, closeModal, switchPanel, signup, signin, logout, updateNav, getUser, getToken, isLoggedIn, toggleDropdown }
})()

// Expose modal helpers globally (called from HTML onclick)
function openModal(panel)   { Auth.openModal(panel) }
function closeModal()       { Auth.closeModal() }
function switchPanel(panel) { Auth.switchPanel(panel) }
function doLogin()          { Auth.signin() }
function doSignup()         { Auth.signup() }
function bgClose(e)         { if (e.target === e.currentTarget) e.currentTarget.classList.remove('open') }