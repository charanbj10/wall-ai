// ─────────────────────────────────────────────
// APP BOOT
// Wires up all modules and starts the app
// ─────────────────────────────────────────────

// ── CATEGORY CHIPS ────────────────────────────
document.getElementById('cats').addEventListener('click', e => {
  const chip = e.target.closest('.chip')
  if (!chip) return
  document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'))
  chip.classList.add('active')
  Images.setTopic(chip.dataset.topic)
})

// ── SEARCH ────────────────────────────────────
// Debounced — hits GET /images/?search=<query>
let searchTimer
document.getElementById('searchInput').addEventListener('input', e => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    Images.setSearch(e.target.value.trim())
  }, CONFIG.SEARCH_DELAY_MS)
})

// ── BOOT ──────────────────────────────────────
Auth.updateNav()        // Restore nav from localStorage session
Images.load()           // Load initial wallpaper grid

if (Auth.isLoggedIn()) {
  Downloads.loadMine()  // Load download history for badges
}
