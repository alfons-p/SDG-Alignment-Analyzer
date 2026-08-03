import axios from 'axios'
import { isBatchActive } from '../lib/batch'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:9000',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Never hard-navigate to /login while a bulk batch is running — that
      // unloads the page and silently kills the batch. Log it instead and let
      // the driver's per-file catch mark the request failed and carry on.
      if (isBatchActive()) {
        const token = localStorage.getItem('token')
        fetch(`${api.defaults.baseURL}/api/analysis/client-log`, {
          method: 'POST',
          keepalive: true,
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            message: `AUTH 401 during batch on ${error.config?.url ?? '?'} — /login redirect suppressed`,
            level: 'warning',
          }),
        }).catch(() => {})
      } else {
        localStorage.removeItem('token')
        if (window.location.pathname !== '/access') {
          window.location.href = '/access'
        }
      }
    }
    return Promise.reject(error)
  },
)

export default api
