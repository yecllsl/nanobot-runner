import axios from 'axios';

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 防止并发请求重复获取 token
let tokenPromise: Promise<string> | null = null;

/**
 * 获取并存储 token
 * 使用单例模式防止并发重复请求
 */
async function ensureToken(): Promise<string> {
  // 如果已有正在进行的获取请求，直接返回
  if (tokenPromise) {
    return tokenPromise;
  }

  tokenPromise = (async () => {
    try {
      // 使用完整 URL 避免循环依赖
      const response = await fetch('/api/auth/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        throw new Error(`获取 token 失败: ${response.status}`);
      }

      const data = await response.json();
      const token = data.access_token;

      // 存储到 localStorage
      localStorage.setItem('nanobot_token', token);
      console.log('[Auth] Token 已自动获取并存储');
      return token;
    } finally {
      // 清除 promise 引用，允许下次重新获取
      tokenPromise = null;
    }
  })();

  return tokenPromise;
}

// 使用 async 拦截器支持自动获取 token
apiClient.interceptors.request.use(
  async (config) => {
    // 跳过 auth/token 端点本身，避免循环
    if (config.url === '/auth/token' || config.url === 'auth/token') {
      return config;
    }

    let token = localStorage.getItem('nanobot_token');

    // 如果没有 token，自动获取
    if (!token) {
      console.log('[Auth] 未找到 token，尝试自动获取...');
      try {
        token = await ensureToken();
      } catch (error) {
        console.error('[Auth] 自动获取 token 失败:', error);
        // 继续发送请求，让服务器返回 401 由响应拦截器处理
      }
    }

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('nanobot_token');
      window.dispatchEvent(new CustomEvent('auth:unauthorized'));
    }
    return Promise.reject(error);
  },
);

export default apiClient;
