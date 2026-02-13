import axios from 'axios'

// Usage notes:
// - Default baseURL remains http://localhost:3001 for local compatibility.
// - In runtime environments, set VITE_API_BASE_URL to the active backend host/port
//   (for example http://localhost:5000) so /api/v1 resources resolve correctly.

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:3001'
})

export default api
