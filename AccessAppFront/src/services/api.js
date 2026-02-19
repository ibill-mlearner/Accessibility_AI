import axios from 'axios'

// this is just a default API base with axios
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || ''
  // Same-origin usage works with browser-default cookie behavior; cross-origin would need withCredentials: true.
})

export default api
