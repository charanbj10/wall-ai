// ─────────────────────────────────────────────
// DOWNLOADS MODULE
//
// Your API endpoints used:
//   POST /downloads/?image_id=<id>   (Bearer token required)
//   GET  /downloads/me               (Bearer token required)
//
// Response shape:
//   { imageid, uid, timestamp, id }
// ─────────────────────────────────────────────

const Downloads = (() => {

  // In-memory set of image IDs the current user has downloaded
  let myIds = new Set()

  // ── LOAD MY DOWNLOADS ─────────────────────
  // GET /downloads/me
  // Called once after login to populate badges on cards
  async function loadMine() {
    if (!Auth.isLoggedIn()) return
    try {
      const data = await http('/downloads/me')
      myIds = new Set((data || []).map(d => d.imageid))
    } catch (_) { /* silently fail */ }
  }

  function clearMine() {
    myIds.clear()
  }

  function hasMine(imageId) {
    return myIds.has(imageId)
  }

  // ── DOWNLOAD ──────────────────────────────
  // POST /downloads/?image_id=<id>
  // Requires: Bearer token in Authorization header
  // Response: { imageid, uid, timestamp, id }
  async function download(e, imageId) {
    if (e) e.stopPropagation()

    if (!Auth.isLoggedIn()) {
      Auth.openModal('login')
      UI.toast('Sign in to download wallpapers')
      return
    }

    UI.toast('Recording download…')

    try {
      // Your exact endpoint — image_id as query param
      const data = await http(`/downloads/${qs({ imageid: imageId })}`, {
        method: 'POST'
      })

      // data.imageid is the image id from your response
      myIds.add(data.imageid)
      UI.toast('Download recorded ✓')

      // Trigger actual browser file download using s3url
      await triggerBrowserDownload(imageId)

      // Refresh grid to show "✓ Downloaded" badge
      Images.load()

    } catch (err) {
      UI.toast('Error: ' + err.message)
    }
  }

  // Fetch image to get s3url and trigger browser download
  async function triggerBrowserDownload(imageId) {
    try {
      const img = await http(`/images/${imageId}`)
      if (img.s3url && img.s3url !== 'string') {
        const a = document.createElement('a')
        a.href     = img.s3url
        a.download = `wallai_${img.name || imageId}.jpg`
        a.target   = '_blank'
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
      }
    } catch (_) { /* s3url not available in dev — that's fine */ }
  }

  // ── MY DOWNLOADS PAGE ─────────────────────
  // Opens a modal showing all downloaded wallpapers
  // Calls GET /downloads/me → then fetches each image details
  async function openPage() {
    if (!Auth.isLoggedIn()) {
      Auth.openModal('login'); return
    }

    // Show modal with loading state
    const modal = document.getElementById('downloadsModal')
    const body  = document.getElementById('downloadsBody')
    modal.classList.add('open')
    body.innerHTML = `<div style="text-align:center;padding:40px;color:var(--muted)">
      Loading your downloads…</div>`

    try {
      // GET /downloads/me → [{ imageid, uid, timestamp, id }]
      const downloads = await http('/downloads/me')

      if (!downloads || downloads.length === 0) {
        body.innerHTML = `
          <div style="text-align:center;padding:60px 20px;color:var(--muted)">
            <div style="font-size:40px;margin-bottom:12px">📭</div>
            <div style="font-size:16px;color:var(--text);font-weight:500;margin-bottom:6px">
              No downloads yet</div>
            <div style="font-size:13px">Browse wallpapers and hit ↓ to download</div>
          </div>`
        return
      }

      // Update in-memory set
      myIds = new Set(downloads.map(d => d.imageid))

      // Fetch full image details for each download
      const imageDetails = await Promise.allSettled(
        downloads.map(d => http(`/images/${d.imageid}`))
      )

      // Render grid of downloaded images
      body.innerHTML = `
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));
                    gap:10px;padding:4px">
          ${downloads.map((dl, i) => {
            const res = imageDetails[i]
            const img = res.status === 'fulfilled' ? res.value : null
            const src = img && img.s3url && img.s3url !== 'string'
              ? img.s3url
              : `https://picsum.photos/seed/${dl.imageid}/280/200`
            const name = img ? img.name : `Image ${dl.imageid}`
            const ts   = new Date(dl.timestamp).toLocaleDateString()
            return `
              <div style="border-radius:10px;overflow:hidden;
                          background:var(--surface2);border:1px solid var(--border);
                          cursor:pointer;transition:transform .15s"
                   onmouseover="this.style.transform='translateY(-3px)'"
                   onmouseout="this.style.transform=''"
                   onclick="Downloads.redownload('${dl.imageid}','${img ? img.name : ''}','${img ? img.s3url : ''}')">
                <img src="${src}" alt="${name}"
                     style="width:100%;height:110px;object-fit:cover;display:block"/>
                <div style="padding:8px 10px">
                  <div style="font-size:12px;font-weight:500;
                              white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
                    ${name}</div>
                  <div style="font-size:10px;color:var(--muted);margin-top:2px">
                    ${ts}</div>
                </div>
              </div>`
          }).join('')}
        </div>
        <div style="text-align:center;margin-top:16px;font-size:12px;color:var(--muted)">
          ${downloads.length} wallpaper${downloads.length > 1 ? 's' : ''} downloaded
        </div>`

    } catch (e) {
      body.innerHTML = `<div style="text-align:center;padding:40px;color:var(--danger)">
        Error: ${e.message}</div>`
    }
  }

  // Re-download a previously downloaded wallpaper
  function redownload(imageId, name, s3url) {
    if (s3url && s3url !== 'string') {
      const a = document.createElement('a')
      a.href = s3url; a.download = `wallai_${name || imageId}.jpg`; a.target = '_blank'
      document.body.appendChild(a); a.click(); document.body.removeChild(a)
      UI.toast('Re-downloading…')
    } else {
      UI.toast('S3 URL not available')
    }
  }

  return { loadMine, clearMine, hasMine, download, openPage, redownload }
})()