// frontend/src/services/api.js
import axios from 'axios';

const api = axios.create({
  baseURL: '/api/', // ← Важно: относительный путь!
});

export default api;