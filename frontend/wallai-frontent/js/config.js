// ─────────────────────────────────────────────
// CONFIG
// Change BASE_URL to your server when deploying
// ─────────────────────────────────────────────
const CONFIG = {
  BASE_URL: 'http://localhost:8000',   // ← swap with EC2 IP on deploy
  DEFAULT_LIMIT: 40,
  SEARCH_DELAY_MS: 400,
  RECOMMEND_ENDPOINT: '/recommend',
}
