import axios from 'axios'

// Default to same-origin so Vite dev proxy (or deployed host) serves backend API calls
// without requiring json-server in normal development flow.
// Override with VITE_API_BASE_URL when targeting a different backend host.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || ''
})

export default api
