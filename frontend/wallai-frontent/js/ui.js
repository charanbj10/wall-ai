// ─────────────────────────────────────────────
// UI MODULE
// Toast, skeletons, shared render helpers
// ─────────────────────────────────────────────

// ── TOAST ─────────────────────────────────────
let toastTimer
const UI = {
  toast(msg) {
    const el = document.getElementById('toast')
    el.textContent = msg
    el.classList.add('show')
    clearTimeout(toastTimer)
    toastTimer = setTimeout(() => el.classList.remove('show'), 2600)
  },

  renderSkeletons(grid) {
    const heights = [220, 280, 190, 310, 240, 180, 260, 200]
    grid.innerHTML = heights.map(h => `
      <div class="skel">
        <div class="skel-box" style="height:${h}px"></div>
        <div style="padding:10px 12px;display:flex;gap:8px">
          <div class="skel-box" style="height:11px;width:55%;border-radius:6px"></div>
          <div class="skel-box" style="height:11px;width:25%;border-radius:6px"></div>
        </div>
      </div>`).join('')
  }
}

// ── LIKES (local storage — no API endpoint in your spec) ──
const Likes = (() => {
  let ids = new Set(JSON.parse(localStorage.getItem('wai_likes') || '[]'))

  function has(imageId) { return ids.has(imageId) }

  function toggle(e, imageId) {
    e.stopPropagation()
    if (!Auth.isLoggedIn()) {
      Auth.openModal('login')
      UI.toast('Sign in to like wallpapers')
      return
    }
    const btn = e.currentTarget
    if (ids.has(imageId)) {
      ids.delete(imageId)
      btn.classList.remove('liked')
      UI.toast('Removed from likes')
    } else {
      ids.add(imageId)
      btn.classList.add('liked')
      UI.toast('Liked ♥')
    }
    localStorage.setItem('wai_likes', JSON.stringify([...ids]))
  }

  return { has, toggle }
})()
