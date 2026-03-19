// ─────────────────────────────────────────────
// IMAGES MODULE
//
// Home page (not logged in) → GET /images/
// Home page (logged in)     → GET /recommend/{user_id}  (personalised, ONE call)
// Topic / Search filter     → GET /images/?topic=&search=
// Card click                → GET /images/{image_id}    (full details + Kafka view on BE)
// ─────────────────────────────────────────────

const Images = (() => {

  let activeTopic  = ''
  let activeSearch = ''

  // ── LOAD ──────────────────────────────────
  async function load() {
    const grid = document.getElementById('grid')
    UI.renderSkeletons(grid)

    // Topic filter or search → always browse (not personalised)
    if (activeTopic || activeSearch) {
      hideBanner()
      await loadBrowse(grid)
      return
    }

    // Logged in + no filter → personalised recommendations
    const me = Auth.getUser()
    if (me) {
      await loadRecommendations(grid, me)
    } else {
      hideBanner()
      await loadBrowse(grid)
    }
  }

  // ── RECOMMENDATIONS ───────────────────────
  // Shows "Recommended for you" section first, then "All images" below
  async function loadRecommendations(grid, me) {
    try {
      // Fetch both in parallel
      const [recResult, allImages] = await Promise.all([
        http(`/recommend/${me.uid}?limit=10`),
        http(`/images/${qs({ skip: 0, limit: CONFIG.DEFAULT_LIMIT })}`),
      ])

      showBanner(recResult.strategy, recResult.cluster_id)

      const recImages = recResult.images || []
      const recIds    = new Set(recImages.map(img => String(img.id)))
      const restImages = (allImages || []).filter(img => !recIds.has(String(img.id)))

      // Clear grid — render two separate sections
      grid.innerHTML = ''

      // ── Section 1: Recommended ──
      if (recImages.length) {
        const recSection = document.createElement('div')
        recSection.style.cssText = 'width:100%;margin-bottom:32px'
        recSection.innerHTML = `
          <div style="display:flex;align-items:center;gap:10px;
                      padding:0 0 16px;margin-bottom:4px;
                      border-bottom:1px solid var(--border)">
            <span style="color:var(--accent);font-size:20px">✦</span>
            <span style="font-family:var(--font-d);font-size:20px;color:var(--text)">
              Recommended for you
            </span>
            <span style="background:rgba(200,241,53,.1);color:var(--accent);
                         padding:3px 12px;border-radius:100px;font-size:11px;font-weight:500">
              AI · ${recResult.strategy}
            </span>
          </div>
          <div class="masonry-inner">
            ${recImages.map((img, i) => buildCard(img, i)).join('')}
          </div>`
        grid.appendChild(recSection)
      }

      // ── Section 2: All images ──
      if (restImages.length) {
        const allSection = document.createElement('div')
        allSection.style.cssText = 'width:100%'
        allSection.innerHTML = `
          <div style="padding:0 0 16px;margin-bottom:4px;
                      border-bottom:1px solid var(--border)">
            <span style="font-family:var(--font-d);font-size:20px;color:var(--text)">
              All images
            </span>
          </div>
          <div class="masonry-inner">
            ${restImages.map((img, i) => buildCard(img, recImages.length + i)).join('')}
          </div>`
        grid.appendChild(allSection)
      }

    } catch (e) {
      console.error('[Recommend] Failed:', e.message)
      hideBanner()
      await loadBrowse(grid)
    }
  }

  // ── BROWSE ────────────────────────────────
  async function loadBrowse(grid) {
    try {
      const params = { skip: 0, limit: CONFIG.DEFAULT_LIMIT }
      if (activeTopic)  params.topic  = activeTopic
      if (activeSearch) params.search = activeSearch

      const images = await http('/images/' + qs(params))

      if (!images || !images.length) {
        grid.innerHTML = `
          <div class="empty">
            <div style="font-size:40px">🖼</div>
            <h3>No images found</h3>
            <p>Try a different topic or search</p>
          </div>`
        return
      }

      grid.innerHTML = `
        <div class="masonry-inner">
          ${images.map((img, i) => buildCard(img, i)).join('')}
        </div>`

    } catch (e) {
      grid.innerHTML = `
        <div class="empty">
          <div style="font-size:40px">⚠️</div>
          <h3>Could not load images</h3>
          <p style="color:var(--muted)">${e.message}</p>
        </div>`
    }
  }

  // ── RECOMMENDATION BANNER ─────────────────
  function showBanner(strategy, clusterId) {
    let el = document.getElementById('recBanner')
    if (!el) {
      el = document.createElement('div')
      el.id = 'recBanner'
      el.style.cssText = `
        margin: 0 28px 16px;
        padding: 10px 16px;
        background: var(--surface);
        border: 1px solid var(--border);
        border-left: 3px solid var(--accent);
        border-radius: 10px;
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 13px;
        color: var(--muted);`
      document.querySelector('main').before(el)
    }

    const labels = {
      cold_start:    'Showing popular images — interact more for personalised picks',
      hybrid:        `Personalised for you — cluster #${clusterId}`,
      collaborative: `Based on users like you — cluster #${clusterId}`,
    }

    el.style.display = 'flex'
    el.innerHTML = `
      <span style="color:var(--accent);font-size:16px">✦</span>
      <span>${labels[strategy] || 'Recommended for you'}</span>
      <span style="margin-left:auto;background:rgba(200,241,53,.1);
                   color:var(--accent);padding:2px 10px;
                   border-radius:100px;font-size:11px;font-weight:500">
        AI · ${strategy}
      </span>`
  }

  function hideBanner() {
    const el = document.getElementById('recBanner')
    if (el) el.style.display = 'none'
  }

  // ── RESOLVE IMAGE URL ─────────────────────
  // Handles ibb.co and imgur page URLs → direct image URLs
  function resolveUrl(url) {
    if (!url || url === 'string' || !url.startsWith('http')) return null

    // ibb.co page URL → direct image
    // https://ibb.co/278JvqMy → https://i.ibb.co/278JvqMy.jpg
    if (url.includes('ibb.co/') && !url.includes('i.ibb.co')) {
      const code = url.split('ibb.co/')[1].split('/')[0].split('?')[0]
      return `https://i.ibb.co/${code}.jpg`
    }

    // imgur page URL → direct image
    if (url.includes('imgur.com/') && !url.includes('i.imgur.com')) {
      const code = url.split('imgur.com/')[1].split('/')[0].split('?')[0]
      return `https://i.imgur.com/${code}.jpg`
    }

    return url
  }

  // ── BUILD CARD ────────────────────────────
  function buildCard(img, i) {
    const liked      = Likes.has(img.id)
    const downloaded = Downloads.hasMine(img.id)
    const src        = resolveUrl(img.s3url) || `https://picsum.photos/seed/${img.id}/400/300`
    const tags       = (img.hashtags || []).slice(0, 3).map(t => `<span class="htag">#${t}</span>`).join('')
    const ts         = img.timestamp ? new Date(img.timestamp).toLocaleDateString() : ''
    const score      = img.score ? `<span style="color:var(--accent);font-size:10px">✦ ${(img.score * 100).toFixed(0)}% match</span>` : ''
    const encoded    = encodeURIComponent(JSON.stringify({ id: img.id, s3url: img.s3url, name: img.name, topic: img.topic, hashtags: img.hashtags, timestamp: img.timestamp }))

    return `
      <div class="card" style="animation-delay:${i * 0.04}s"
           onclick="Images.openDetail('${encoded}')">
        <img src="${src}" alt="${img.name}"
             style="width:100%;display:block;object-fit:cover"
             loading="lazy"
             onerror="this.src='https://picsum.photos/seed/${img.id}x/400/300'"/>
        <div class="overlay"></div>
        <div class="card-actions">
          <div>
            <div class="card-title">${img.name}</div>
            <span class="card-tag">${img.topic}</span>
          </div>
          <div class="act-btns">
            <button class="icon-btn like-btn ${liked ? 'liked' : ''}"
              onclick="Likes.toggle(event, ${img.id})" title="Like">♥</button>
            <button class="icon-btn dl-btn"
              onclick="Downloads.download(event, ${img.id})" title="Download">↓</button>
          </div>
        </div>
        ${tags ? `<div class="card-hashtags">${tags}</div>` : ''}
        <div class="card-meta">
          <span>📅 ${ts}</span>
          ${score}
          ${downloaded ? '<span style="color:var(--accent)">✓ Downloaded</span>' : ''}
        </div>
      </div>`
  }

  // ── DETAIL MODAL ──────────────────────────
  // GET /images/{image_id} — full details + triggers Kafka view event on BE
  async function openDetail(encoded) {
    let img
    try {
      img = JSON.parse(decodeURIComponent(encoded))
    } catch { return }

    // Show modal immediately with card data (fast)
    showDetail(img)

    // Then fetch fresh full data from BE (triggers Kafka view event)
    try {
      const fresh = await http(`/images/${img.id}`)
      showDetail(fresh)   // update modal with fresh data
    } catch (_) {}
  }

  function showDetail(img) {
    const src = resolveUrl(img.s3url) || `https://picsum.photos/seed/${img.id}/700/420`
    const ts  = img.timestamp ? new Date(img.timestamp).toLocaleString() : ''

    const detailImg = document.getElementById('detailImg')
    detailImg.src           = src
    detailImg.style.display = 'block'
    detailImg.onerror       = () => { detailImg.src = `https://picsum.photos/seed/${img.id}x/700/420` }

    document.getElementById('detailTitle').textContent  = img.name
    document.getElementById('detailMeta').innerHTML     =
      `<span>📁 ${img.topic}</span><span>📅 ${ts}</span><span>🔑 ID: ${img.id}</span>`
    document.getElementById('detailHashtags').innerHTML =
      (img.hashtags || []).map(t => `<span class="detail-htag">#${t}</span>`).join('')
    document.getElementById('detailDlBtn').onclick      =
      () => Downloads.download(null, img.id)

    document.getElementById('detailModal').classList.add('open')
  }

  // ── RENDER ────────────────────────────────
  function render(grid, images) {
    if (!images.length) {
      grid.innerHTML = `
        <div class="empty">
          <div style="font-size:40px">🖼</div>
          <h3>No images found</h3>
          <p>Try a different topic or search</p>
        </div>`
      return
    }
    grid.innerHTML = images.map((img, i) => buildCard(img, i)).join('')
  }

  // ── FILTER SETTERS ────────────────────────
  function setTopic(topic) {
    activeTopic  = topic
    activeSearch = ''
    document.getElementById('searchInput').value = ''
    load()
  }

  function setSearch(query) {
    activeSearch = query
    load()
  }

  return { load, render, openDetail, showDetail, setTopic, setSearch }
})()