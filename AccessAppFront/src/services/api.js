import axios from 'axios'

// Shared Axios instance: all frontend stores/composables import `api`, so setting `baseURL`
// here routes every relative `/api/v1/...` request to the configured backend host.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || ''
  // Same-origin usage works with browser-default cookie behavior; cross-origin would need withCredentials: true.
})

export default api
