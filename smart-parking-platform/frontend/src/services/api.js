/**
 * API client for Smart Parking backend.
 */
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 → redirect to login
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

// ─── Auth ─────────────────────────────────────────────────────────────
export const authAPI = {
  login: (email, password) =>
    api.post('/auth/login', new URLSearchParams({ username: email, password }), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }),
  getMe: () => api.get('/auth/me'),
  getUsers: () => api.get('/auth/users'),
};

// ─── Zones ────────────────────────────────────────────────────────────
export const zonesAPI = {
  list: (activeOnly = true) => api.get('/zones/', { params: { active_only: activeOnly } }),
  get: (id) => api.get(`/zones/${id}`),
  getAvailability: () => api.get('/zones/availability'),
  create: (data) => api.post('/zones/', data),
  update: (id, data) => api.put(`/zones/${id}`, data),
  delete: (id) => api.delete(`/zones/${id}`),
};

// ─── Events ───────────────────────────────────────────────────────────
export const eventsAPI = {
  list: (params = {}) => api.get('/events/', { params }),
  create: (data) => api.post('/events/', data),
  detect: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/events/detect', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  detectAnnotated: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/events/detect/annotated', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

// ─── Analytics ────────────────────────────────────────────────────────
export const analyticsAPI = {
  getDashboard: () => api.get('/analytics/dashboard'),
  getZoneAnalytics: (zoneId, days = 7) =>
    api.get(`/analytics/zones/${zoneId}`, { params: { days } }),
  getOccupancyTrend: (zoneId, hours = 24) =>
    api.get('/analytics/occupancy-trend', { params: { zone_id: zoneId, hours } }),
  getForecast: (zoneId, horizon = 24) =>
    api.get('/analytics/forecast', { params: { zone_id: zoneId, horizon } }),
  getPeakHours: (zoneId, days = 7) =>
    api.get('/analytics/peak-hours', { params: { zone_id: zoneId, days } }),
  getArrivalRate: (zoneId, hours = 4) =>
    api.get('/analytics/arrival-rate', { params: { zone_id: zoneId, hours } }),
};

export default api;
