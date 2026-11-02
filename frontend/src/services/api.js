import axios from 'axios';

// Dynamically resolve the backend host so the frontend works whether
// accessed via localhost or a LAN IP (e.g. 10.20.17.183).
const backendBase =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  `http://${window.location.hostname}:8000/api/v1`;

const api = axios.create({
  baseURL: backendBase,
  headers: {
    'Content-Type': 'application/json',
  },
});


api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token && token !== 'dummy_token') {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      const url = error.config ? error.config.url || '' : '';
      if (!url.includes('/auth/login') && !url.includes('/auth/register')) {
        localStorage.removeItem('token');
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

export default api;
export const fetchAnalytics = () => api.get('/interviews/analytics');
export const fetchAICoach = () => api.get('/interviews/coach');
export const fetchCoachSummary = () => api.get('/coach/summary');
export const fetchCoachRecommendations = () => api.get('/coach/recommendations');
export const fetchCoachTopics = () => api.get('/coach/topics');
export const fetchCoachWeakTopics = () => api.get('/coach/weak-topics');
export const fetchCoachStrongTopics = () => api.get('/coach/strong-topics');
export const generatePracticeQuestion = (topic) => api.post('/coach/practice-question', { topic });
export const askCoachChat = (message, history = []) => api.post('/coach/chat', { message, history });
export const extractResumeSkills = (formData) =>
  api.post('/interviews/extract-resume', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
