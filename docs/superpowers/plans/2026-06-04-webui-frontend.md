# v0.28.0 WebUI 前端数据可视化 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建独立 React SPA 前端项目，实现跑步数据可视化仪表盘、VDOT趋势、训练负荷、活动列表/详情、身体信号等5个核心页面

**Architecture:** 独立 React SPA 项目（`webui/`），通过 Vite proxy 开发模式转发 `/api` 到 FastAPI(8766)，生产模式部署在 FastAPI StaticFiles 同源。API 客户端统一 axios 实例 + token 认证，Recharts 图表渲染，TailwindCSS 样式，React Router 路由。与后端共享核心数据层保证数据一致性（ADR-019）。

**Tech Stack:** React 18 + TypeScript 5 + Vite 5 + Recharts 2 + React Router 6 + TailwindCSS 3 + axios + Vitest + @testing-library/react

---

## File Structure

| 文件 | 操作 | 职责 |
|------|------|------|
| `webui/package.json` | 创建 | 项目依赖与脚本 |
| `webui/vite.config.ts` | 创建 | Vite配置（proxy+构建） |
| `webui/tsconfig.json` | 创建 | TypeScript配置 |
| `webui/tsconfig.node.json` | 创建 | Node端TypeScript配置 |
| `webui/tailwind.config.js` | 创建 | TailwindCSS配置 |
| `webui/postcss.config.js` | 创建 | PostCSS配置 |
| `webui/index.html` | 创建 | SPA入口HTML |
| `webui/src/main.tsx` | 创建 | React入口 |
| `webui/src/App.tsx` | 创建 | 根组件（路由配置） |
| `webui/src/index.css` | 创建 | 全局样式（TailwindCSS指令） |
| `webui/src/vite-env.d.ts` | 创建 | Vite类型声明 |
| `webui/src/types/api.ts` | 创建 | TypeScript类型定义（与后端Schema对齐） |
| `webui/src/utils/format.ts` | 创建 | 格式化工具（配速/时长/距离） |
| `webui/src/utils/constants.ts` | 创建 | 常量定义 |
| `webui/src/api/client.ts` | 创建 | axios实例（baseURL+认证） |
| `webui/src/api/dashboard.ts` | 创建 | Dashboard API |
| `webui/src/api/vdot.ts` | 创建 | VDOT API |
| `webui/src/api/training-load.ts` | 创建 | 训练负荷API |
| `webui/src/api/activities.ts` | 创建 | 活动API |
| `webui/src/api/body-signals.ts` | 创建 | 身体信号API |
| `webui/src/hooks/useTimeRange.ts` | 创建 | 时间范围状态管理Hook |
| `webui/src/hooks/useApi.ts` | 创建 | API请求封装Hook |
| `webui/src/components/layout/AppLayout.tsx` | 创建 | 左侧导航+右侧内容区 |
| `webui/src/components/layout/Sidebar.tsx` | 创建 | 侧边导航栏 |
| `webui/src/components/layout/Header.tsx` | 创建 | 顶部栏 |
| `webui/src/components/cards/StatCard.tsx` | 创建 | 统计卡片（距离/时长/配速/心率） |
| `webui/src/components/cards/StatusCard.tsx` | 创建 | 状态卡片（疲劳/恢复） |
| `webui/src/components/cards/AlertCard.tsx` | 创建 | 预警卡片 |
| `webui/src/components/common/TimeRangeSelector.tsx` | 创建 | 时间范围筛选控件 |
| `webui/src/components/common/Pagination.tsx` | 创建 | 分页组件 |
| `webui/src/components/common/LoadingSpinner.tsx` | 创建 | 加载状态 |
| `webui/src/components/charts/VdotTrendChart.tsx` | 创建 | VDOT趋势折线图 |
| `webui/src/components/charts/TrainingLoadChart.tsx` | 创建 | ATL/CTL/TSB堆叠面积图 |
| `webui/src/components/charts/PaceChart.tsx` | 创建 | 配速曲线 |
| `webui/src/components/charts/HeartRateChart.tsx` | 创建 | 心率曲线 |
| `webui/src/pages/DashboardPage.tsx` | 创建 | 首页仪表盘 |
| `webui/src/pages/VdotPage.tsx` | 创建 | VDOT趋势页 |
| `webui/src/pages/TrainingLoadPage.tsx` | 创建 | 训练负荷页 |
| `webui/src/pages/ActivitiesPage.tsx` | 创建 | 活动列表页 |
| `webui/src/pages/ActivityDetailPage.tsx` | 创建 | 活动详情页 |
| `webui/src/pages/BodySignalsPage.tsx` | 创建 | 身体信号页 |
| `webui/src/__tests__/format.test.ts` | 创建 | 格式化工具测试 |
| `webui/src/__tests__/useTimeRange.test.ts` | 创建 | 时间范围Hook测试 |
| `webui/src/__tests__/StatCard.test.tsx` | 创建 | StatCard组件测试 |
| `webui/src/__tests__/Pagination.test.tsx` | 创建 | Pagination组件测试 |
| `webui/src/__tests__/DashboardPage.test.tsx` | 创建 | Dashboard页面测试 |
| `webui/src/__tests__/VdotPage.test.tsx` | 创建 | VDOT页面测试 |
| `webui/src/__tests__/TrainingLoadPage.test.tsx` | 创建 | 训练负荷页面测试 |
| `webui/src/__tests__/ActivitiesPage.test.tsx` | 创建 | 活动列表页面测试 |

---

## Task 1: 前端项目骨架

**Files:**
- Create: `webui/package.json`
- Create: `webui/vite.config.ts`
- Create: `webui/tsconfig.json`
- Create: `webui/tsconfig.node.json`
- Create: `webui/tailwind.config.js`
- Create: `webui/postcss.config.js`
- Create: `webui/index.html`
- Create: `webui/src/main.tsx`
- Create: `webui/src/App.tsx`
- Create: `webui/src/index.css`
- Create: `webui/src/vite-env.d.ts`

- [ ] **Step 1: 创建 webui 目录和 package.json**

```bash
mkdir -p webui/src webui/public
```

创建 `webui/package.json`：

```json
{
  "name": "nanobot-runner-webui",
  "private": true,
  "version": "0.28.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0"
  },
  "dependencies": {
    "axios": "^1.7.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.23.0",
    "recharts": "^2.12.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.4.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/user-event": "^14.5.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "autoprefixer": "^10.4.0",
    "jsdom": "^24.1.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.5.0",
    "vite": "^5.4.0",
    "vitest": "^2.0.0"
  }
}
```

- [ ] **Step 2: 创建 vite.config.ts**

创建 `webui/vite.config.ts`：

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8766',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
  },
});
```

- [ ] **Step 3: 创建 tsconfig.json**

创建 `webui/tsconfig.json`：

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

创建 `webui/tsconfig.node.json`：

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2023"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 4: 创建 TailwindCSS 配置**

创建 `webui/tailwind.config.js`：

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
      },
    },
  },
  plugins: [],
};
```

创建 `webui/postcss.config.js`：

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 5: 创建 index.html**

创建 `webui/index.html`：

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/x-icon" href="/favicon.ico" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Nanobot Runner</title>
  </head>
  <body class="bg-gray-50">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 6: 创建 src 入口文件**

创建 `webui/src/vite-env.d.ts`：

```typescript
/// <reference types="vite/client" />
```

创建 `webui/src/index.css`：

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto',
    'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans',
    'Helvetica Neue', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
```

创建 `webui/src/main.tsx`：

```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

创建 `webui/src/App.tsx`（初始版本，后续 Task 4 添加路由）：

```tsx
function App() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900">Nanobot Runner</h1>
        <p className="mt-2 text-gray-500">WebUI 数据可视化</p>
      </div>
    </div>
  );
}

export default App;
```

- [ ] **Step 7: 安装依赖并验证启动**

```bash
cd webui && npm install
```

Run: `cd webui && npx tsc --noEmit`
Expected: 无错误

Run: `cd webui && npm run build`
Expected: 构建成功，输出到 `webui/dist/`

- [ ] **Step 8: Commit**

```bash
git add webui/
git commit -m "feat(webui): scaffold React+TypeScript+Vite project with TailwindCSS"
```

---

## Task 2: TypeScript 类型定义 + 工具函数

**Files:**
- Create: `webui/src/types/api.ts`
- Create: `webui/src/utils/format.ts`
- Create: `webui/src/utils/constants.ts`
- Test: `webui/src/__tests__/format.test.ts`

- [ ] **Step 1: 编写格式化工具的失败测试**

创建 `webui/src/__tests__/format.test.ts`：

```typescript
import { describe, it, expect } from 'vitest';
import {
  formatPace,
  formatDuration,
  formatDistance,
  formatHeartRate,
  formatVdot,
  formatDateString,
} from '../utils/format';

describe('formatPace', () => {
  it('格式化配速为 M\'SS"/km', () => {
    // 5分30秒每公里 = 330秒
    expect(formatPace(330)).toBe('5\'30"/km');
  });

  it('整分配速', () => {
    expect(formatPace(300)).toBe('5\'00"/km');
  });

  it('零秒配速', () => {
    expect(formatPace(0)).toBe('0\'00"/km');
  });
});

describe('formatDuration', () => {
  it('格式化时长为 HH:MM:SS', () => {
    expect(formatDuration(5025)).toBe('01:23:45');
  });

  it('不足1小时', () => {
    expect(formatDuration(1865)).toBe('00:31:05');
  });

  it('零秒时长', () => {
    expect(formatDuration(0)).toBe('00:00:00');
  });
});

describe('formatDistance', () => {
  it('格式化距离为 km（保留2位小数）', () => {
    expect(formatDistance(10234)).toBe('10.23 km');
  });

  it('零距离', () => {
    expect(formatDistance(0)).toBe('0.00 km');
  });
});

describe('formatHeartRate', () => {
  it('格式化心率为 bpm', () => {
    expect(formatHeartRate(155)).toBe('155 bpm');
  });
});

describe('formatVdot', () => {
  it('格式化VDOT（保留1位小数）', () => {
    expect(formatVdot(45.23)).toBe('45.2');
  });
});

describe('formatDateString', () => {
  it('格式化日期字符串', () => {
    expect(formatDateString('2024-01-15')).toBe('2024-01-15');
  });
});
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd webui && npx vitest run src/__tests__/format.test.ts`
Expected: FAIL — `Cannot find module '../utils/format'`

- [ ] **Step 3: 创建类型定义**

创建 `webui/src/types/api.ts`：

```typescript
// ===== 通用 =====
export interface HealthResponse {
  status: string;
  version: string;
}

// ===== Dashboard =====
export interface TodayData {
  has_activity: boolean;
  distance_m: number;
  duration_s: number;
  pace_s_per_km: number;
  avg_hr: number | null;
  vdot: number | null;
  tss: number | null;
}

export interface WeeklyStats {
  total_distance_m: number;
  total_duration_s: number;
  total_tss: number;
  run_count: number;
}

export interface DashboardResponse {
  today: TodayData;
  weekly: WeeklyStats;
}

// ===== VDOT =====
export interface VdotTrendItem {
  date: string;
  vdot: number;
  distance_m: number;
  duration_s: number;
}

export interface VdotTrendResponse {
  items: VdotTrendItem[];
  days: number;
}

// ===== 训练负荷 =====
export interface TrainingLoadData {
  atl: number;
  ctl: number;
  tsb: number;
  fitness_status: string;
}

export interface TrainingLoadTrendItem {
  date: string;
  atl: number;
  ctl: number;
  tsb: number;
}

export interface TrainingLoadResponse {
  current: TrainingLoadData;
  days: number;
}

export interface TrainingLoadTrendResponse {
  items: TrainingLoadTrendItem[];
  days: number;
}

// ===== 活动 =====
export interface ActivityItem {
  id: string;
  date: string;
  distance_m: number;
  duration_s: number;
  pace_s_per_km: number;
  avg_hr: number | null;
  vdot: number | null;
  tss: number | null;
}

export interface ActivitiesResponse {
  items: ActivityItem[];
  total: number;
  page: number;
  size: number;
}

export interface ActivityDetailResponse {
  id: string;
  date: string;
  distance_m: number;
  duration_s: number;
  pace_s_per_km: number;
  avg_hr: number | null;
  max_hr: number | null;
  vdot: number | null;
  tss: number | null;
  calories: number | null;
  // 逐公里配速数据（用于配速曲线）
  splits: ActivitySplit[];
  // 逐分钟心率数据（用于心率曲线）
  hr_track: HrTrackPoint[];
}

export interface ActivitySplit {
  km: number;
  pace_s_per_km: number;
  avg_hr: number | null;
}

export interface HrTrackPoint {
  time_s: number;
  hr: number;
}

// ===== 身体信号 =====
export interface BodySignalsResponse {
  hrv_status: string;
  fatigue_status: string;
  recovery_status: string;
}

export interface HrvData {
  rmssd: number | null;
  sdnn: number | null;
  resting_hr: number | null;
  status: string;
  trend: HrvTrendItem[];
}

export interface HrvTrendItem {
  date: string;
  rmssd: number | null;
  resting_hr: number | null;
}

export interface HrvResponse {
  data: HrvData;
  days: number;
}

export interface FatigueData {
  score: number;
  status: string;
  recommendation: string;
}

export interface FatigueResponse {
  data: FatigueData;
}

export interface RecoveryData {
  status: string;
  recommendation: string;
  hours_since_last_run: number | null;
}

export interface RecoveryResponse {
  data: RecoveryData;
}
```

- [ ] **Step 4: 创建格式化工具函数**

创建 `webui/src/utils/format.ts`：

```typescript
/**
 * 格式化配速为 M'SS"/km
 * @param secondsPerKm 每公里秒数
 */
export function formatPace(secondsPerKm: number): string {
  const minutes = Math.floor(secondsPerKm / 60);
  const seconds = Math.floor(secondsPerKm % 60);
  return `${minutes}'${seconds.toString().padStart(2, '0')}"`;
}

/**
 * 格式化时长为 HH:MM:SS
 * @param totalSeconds 总秒数
 */
export function formatDuration(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = Math.floor(totalSeconds % 60);
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

/**
 * 格式化距离为 km（保留2位小数）
 * @param meters 米
 */
export function formatDistance(meters: number): string {
  const km = meters / 1000;
  return `${km.toFixed(2)} km`;
}

/**
 * 格式化心率为 bpm
 * @param hr 心率值
 */
export function formatHeartRate(hr: number): string {
  return `${hr} bpm`;
}

/**
 * 格式化VDOT（保留1位小数）
 * @param vdot VDOT值
 */
export function formatVdot(vdot: number): string {
  return vdot.toFixed(1);
}

/**
 * 格式化日期字符串
 * @param dateStr ISO日期字符串
 */
export function formatDateString(dateStr: string): string {
  return dateStr.split('T')[0];
}
```

- [ ] **Step 5: 创建常量定义**

创建 `webui/src/utils/constants.ts`：

```typescript
/** 时间范围选项 */
export const TIME_RANGE_OPTIONS = [
  { label: '7天', value: 7 },
  { label: '30天', value: 30 },
  { label: '90天', value: 90 },
  { label: '365天', value: 365 },
] as const;

/** 各页面默认时间范围（天） */
export const DEFAULT_TIME_RANGES: Record<string, number> = {
  dashboard: 7,
  vdot: 90,
  trainingLoad: 42,
  bodySignals: 7,
};

/** 疲劳状态阈值 */
export const FITNESS_STATUS = {
  FRESH: '新鲜',
  OPTIMAL: '最佳',
  FATIGUED: '疲劳',
  OVER_TRAINED: '过度训练',
} as const;

/** TSB疲劳状态判定 */
export function getFitnessStatus(tsb: number): string {
  if (tsb > 15) return FITNESS_STATUS.FRESH;
  if (tsb > 0) return FITNESS_STATUS.OPTIMAL;
  if (tsb > -30) return FITNESS_STATUS.FATIGUED;
  return FITNESS_STATUS.OVER_TRAINED;
}

/** TSB疲劳状态对应颜色 */
export function getFitnessStatusColor(status: string): string {
  switch (status) {
    case FITNESS_STATUS.FRESH: return 'text-green-600';
    case FITNESS_STATUS.OPTIMAL: return 'text-blue-600';
    case FITNESS_STATUS.FATIGUED: return 'text-yellow-600';
    case FITNESS_STATUS.OVER_TRAINED: return 'text-red-600';
    default: return 'text-gray-600';
  }
}

/** TSB疲劳状态对应背景色 */
export function getFitnessStatusBg(status: string): string {
  switch (status) {
    case FITNESS_STATUS.FRESH: return 'bg-green-50 border-green-200';
    case FITNESS_STATUS.OPTIMAL: return 'bg-blue-50 border-blue-200';
    case FITNESS_STATUS.FATIGUED: return 'bg-yellow-50 border-yellow-200';
    case FITNESS_STATUS.OVER_TRAINED: return 'bg-red-50 border-red-200';
    default: return 'bg-gray-50 border-gray-200';
  }
}

/** Agent对话链接 */
export const AGENT_CHAT_URL = 'http://127.0.0.1:8765';

/** API基础路径 */
export const API_BASE_URL = '/api/webui';
```

- [ ] **Step 6: 运行测试验证通过**

Run: `cd webui && npx vitest run src/__tests__/format.test.ts`
Expected: 全部 PASS

- [ ] **Step 7: Commit**

```bash
git add webui/src/types/ webui/src/utils/ webui/src/__tests__/
git commit -m "feat(webui): add TypeScript types, format utils, and constants"
```

---

## Task 3: API 客户端层

**Files:**
- Create: `webui/src/api/client.ts`
- Create: `webui/src/api/dashboard.ts`
- Create: `webui/src/api/vdot.ts`
- Create: `webui/src/api/training-load.ts`
- Create: `webui/src/api/activities.ts`
- Create: `webui/src/api/body-signals.ts`

- [ ] **Step 1: 创建 axios 实例（含认证）**

创建 `webui/src/api/client.ts`：

```typescript
import axios from 'axios';

/**
 * axios 实例
 * - baseURL: /api/webui（Vite proxy 转发到 FastAPI 8766）
 * - 认证: 自动从 localStorage 读取 token 附加到 Authorization Header
 */
const apiClient = axios.create({
  baseURL: '/api/webui',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器：自动附加 token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('nanobot_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器：401 时清除 token 并跳转登录
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('nanobot_token');
      // 触发全局认证状态更新（后续可扩展为跳转登录页）
      window.dispatchEvent(new CustomEvent('auth:unauthorized'));
    }
    return Promise.reject(error);
  },
);

export default apiClient;
```

- [ ] **Step 2: 创建 Dashboard API**

创建 `webui/src/api/dashboard.ts`：

```typescript
import apiClient from './client';
import type { DashboardResponse } from '../types/api';

/**
 * 获取仪表盘数据
 * @param days 天数（默认7）
 */
export async function getDashboard(days: number = 7): Promise<DashboardResponse> {
  const response = await apiClient.get<DashboardResponse>('/dashboard', {
    params: { days },
  });
  return response.data;
}
```

- [ ] **Step 3: 创建 VDOT API**

创建 `webui/src/api/vdot.ts`：

```typescript
import apiClient from './client';
import type { VdotTrendResponse } from '../types/api';

/**
 * 获取VDOT趋势数据
 * @param days 天数（默认90）
 */
export async function getVdotTrend(days: number = 90): Promise<VdotTrendResponse> {
  const response = await apiClient.get<VdotTrendResponse>('/vdot/trend', {
    params: { days },
  });
  return response.data;
}
```

- [ ] **Step 4: 创建训练负荷 API**

创建 `webui/src/api/training-load.ts`：

```typescript
import apiClient from './client';
import type { TrainingLoadResponse, TrainingLoadTrendResponse } from '../types/api';

/**
 * 获取当前训练负荷
 * @param days 天数（默认42）
 */
export async function getTrainingLoad(days: number = 42): Promise<TrainingLoadResponse> {
  const response = await apiClient.get<TrainingLoadResponse>('/training-load', {
    params: { days },
  });
  return response.data;
}

/**
 * 获取训练负荷趋势数据
 * @param days 天数（默认42）
 */
export async function getTrainingLoadTrend(days: number = 42): Promise<TrainingLoadTrendResponse> {
  const response = await apiClient.get<TrainingLoadTrendResponse>('/training-load/trend', {
    params: { days },
  });
  return response.data;
}
```

- [ ] **Step 5: 创建活动 API**

创建 `webui/src/api/activities.ts`：

```typescript
import apiClient from './client';
import type { ActivitiesResponse, ActivityDetailResponse } from '../types/api';

export interface ActivitiesParams {
  page?: number;
  size?: number;
  start_date?: string;
  end_date?: string;
  min_distance?: number;
}

/**
 * 获取活动列表
 * @param params 分页和筛选参数
 */
export async function getActivities(params: ActivitiesParams = {}): Promise<ActivitiesResponse> {
  const response = await apiClient.get<ActivitiesResponse>('/activities', {
    params: {
      page: params.page ?? 1,
      size: params.size ?? 20,
      ...params,
    },
  });
  return response.data;
}

/**
 * 获取活动详情
 * @param id 活动ID（SHA256哈希）
 */
export async function getActivityDetail(id: string): Promise<ActivityDetailResponse> {
  const response = await apiClient.get<ActivityDetailResponse>(`/activities/${id}`);
  return response.data;
}
```

- [ ] **Step 6: 创建身体信号 API**

创建 `webui/src/api/body-signals.ts`：

```typescript
import apiClient from './client';
import type { BodySignalsResponse, HrvResponse, FatigueResponse, RecoveryResponse } from '../types/api';

/**
 * 获取身体信号汇总
 * @param days 天数（默认7）
 */
export async function getBodySignals(days: number = 7): Promise<BodySignalsResponse> {
  const response = await apiClient.get<BodySignalsResponse>('/body-signals', {
    params: { days },
  });
  return response.data;
}

/**
 * 获取HRV数据
 * @param days 天数（默认30）
 */
export async function getHrv(days: number = 30): Promise<HrvResponse> {
  const response = await apiClient.get<HrvResponse>('/body-signals/hrv', {
    params: { days },
  });
  return response.data;
}

/**
 * 获取疲劳度数据
 */
export async function getFatigue(): Promise<FatigueResponse> {
  const response = await apiClient.get<FatigueResponse>('/body-signals/fatigue');
  return response.data;
}

/**
 * 获取恢复状态数据
 */
export async function getRecovery(): Promise<RecoveryResponse> {
  const response = await apiClient.get<RecoveryResponse>('/body-signals/recovery');
  return response.data;
}
```

- [ ] **Step 7: 验证 TypeScript 编译**

Run: `cd webui && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 8: Commit**

```bash
git add webui/src/api/
git commit -m "feat(webui): add API client layer with auth interceptor and all endpoints"
```

---

## Task 4: 布局与导航

**Files:**
- Create: `webui/src/components/layout/AppLayout.tsx`
- Create: `webui/src/components/layout/Sidebar.tsx`
- Create: `webui/src/components/layout/Header.tsx`
- Modify: `webui/src/App.tsx`

- [ ] **Step 1: 创建 Sidebar 组件**

创建 `webui/src/components/layout/Sidebar.tsx`：

```tsx
import { NavLink } from 'react-router-dom';

const navItems = [
  { path: '/', label: '仪表盘', icon: '📊' },
  { path: '/vdot', label: 'VDOT', icon: '📈' },
  { path: '/training-load', label: '负荷', icon: '💪' },
  { path: '/activities', label: '活动', icon: '🏃' },
  { path: '/body-signals', label: '身体', icon: '❤️' },
];

export default function Sidebar() {
  return (
    <aside className="w-16 lg:w-48 bg-white border-r border-gray-200 flex flex-col py-4 shrink-0">
      <nav className="flex-1 space-y-1 px-2">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-primary-50 text-primary-700'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`
            }
          >
            <span className="text-lg">{item.icon}</span>
            <span className="hidden lg:inline">{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
```

- [ ] **Step 2: 创建 Header 组件**

创建 `webui/src/components/layout/Header.tsx`：

```tsx
import { AGENT_CHAT_URL } from '../../utils/constants';

export default function Header() {
  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-4 lg:px-6 shrink-0">
      <h1 className="text-lg font-bold text-gray-900">Nanobot Runner</h1>
      <div className="flex items-center gap-4">
        <a
          href={AGENT_CHAT_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-primary-600 hover:text-primary-700 font-medium"
        >
          Agent对话 →
        </a>
      </div>
    </header>
  );
}
```

- [ ] **Step 3: 创建 AppLayout 组件**

创建 `webui/src/components/layout/AppLayout.tsx`：

```tsx
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';

export default function AppLayout() {
  return (
    <div className="h-screen flex flex-col">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto p-4 lg:p-6 bg-gray-50">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: 更新 App.tsx 添加路由配置**

修改 `webui/src/App.tsx`：

```tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import DashboardPage from './pages/DashboardPage';
import VdotPage from './pages/VdotPage';
import TrainingLoadPage from './pages/TrainingLoadPage';
import ActivitiesPage from './pages/ActivitiesPage';
import ActivityDetailPage from './pages/ActivityDetailPage';
import BodySignalsPage from './pages/BodySignalsPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/vdot" element={<VdotPage />} />
          <Route path="/training-load" element={<TrainingLoadPage />} />
          <Route path="/activities" element={<ActivitiesPage />} />
          <Route path="/activities/:id" element={<ActivityDetailPage />} />
          <Route path="/body-signals" element={<BodySignalsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
```

- [ ] **Step 5: 创建页面占位组件（确保路由可编译）**

创建 `webui/src/pages/DashboardPage.tsx`：

```tsx
export default function DashboardPage() {
  return <div>Dashboard</div>;
}
```

创建 `webui/src/pages/VdotPage.tsx`：

```tsx
export default function VdotPage() {
  return <div>VDOT</div>;
}
```

创建 `webui/src/pages/TrainingLoadPage.tsx`：

```tsx
export default function TrainingLoadPage() {
  return <div>Training Load</div>;
}
```

创建 `webui/src/pages/ActivitiesPage.tsx`：

```tsx
export default function ActivitiesPage() {
  return <div>Activities</div>;
}
```

创建 `webui/src/pages/ActivityDetailPage.tsx`：

```tsx
export default function ActivityDetailPage() {
  return <div>Activity Detail</div>;
}
```

创建 `webui/src/pages/BodySignalsPage.tsx`：

```tsx
export default function BodySignalsPage() {
  return <div>Body Signals</div>;
}
```

- [ ] **Step 6: 验证 TypeScript 编译和构建**

Run: `cd webui && npx tsc --noEmit`
Expected: 无错误

Run: `cd webui && npm run build`
Expected: 构建成功

- [ ] **Step 7: Commit**

```bash
git add webui/src/components/layout/ webui/src/App.tsx webui/src/pages/
git commit -m "feat(webui): add layout components (AppLayout/Sidebar/Header) and route config"
```

---

## Task 5: 共享组件

**Files:**
- Create: `webui/src/components/cards/StatCard.tsx`
- Create: `webui/src/components/cards/StatusCard.tsx`
- Create: `webui/src/components/cards/AlertCard.tsx`
- Create: `webui/src/components/common/LoadingSpinner.tsx`
- Create: `webui/src/components/common/Pagination.tsx`
- Create: `webui/src/components/common/TimeRangeSelector.tsx`
- Test: `webui/src/__tests__/StatCard.test.tsx`
- Test: `webui/src/__tests__/Pagination.test.tsx`

- [ ] **Step 1: 编写 StatCard 组件测试**

创建 `webui/src/__tests__/StatCard.test.tsx`：

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import StatCard from '../components/cards/StatCard';

describe('StatCard', () => {
  it('渲染标题和数值', () => {
    render(<StatCard title="距离" value="10.23 km" />);
    expect(screen.getByText('距离')).toBeInTheDocument();
    expect(screen.getByText('10.23 km')).toBeInTheDocument();
  });

  it('渲染可选副标题', () => {
    render(<StatCard title="配速" value="5'30&quot;/km" subtitle="平均" />);
    expect(screen.getByText('平均')).toBeInTheDocument();
  });

  it('无副标题时不渲染副标题区域', () => {
    const { container } = render(<StatCard title="心率" value="155 bpm" />);
    const subtitleEl = container.querySelector('.text-xs.text-gray-400');
    expect(subtitleEl).toBeNull();
  });
});
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd webui && npx vitest run src/__tests__/StatCard.test.tsx`
Expected: FAIL — `Cannot find module '../components/cards/StatCard'`

- [ ] **Step 3: 创建 StatCard 组件**

创建 `webui/src/components/cards/StatCard.tsx`：

```tsx
interface StatCardProps {
  title: string;
  value: string;
  subtitle?: string;
}

export default function StatCard({ title, value, subtitle }: StatCardProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 lg:p-5">
      <p className="text-sm text-gray-500 font-medium">{title}</p>
      <p className="mt-1 text-2xl font-bold text-gray-900">{value}</p>
      {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
    </div>
  );
}
```

- [ ] **Step 4: 创建 StatusCard 组件**

创建 `webui/src/components/cards/StatusCard.tsx`：

```tsx
interface StatusCardProps {
  title: string;
  status: string;
  description: string;
  statusColor?: string;
}

export default function StatusCard({ title, status, description, statusColor = 'text-gray-900' }: StatusCardProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 lg:p-5">
      <p className="text-sm text-gray-500 font-medium">{title}</p>
      <p className={`mt-1 text-xl font-bold ${statusColor}`}>{status}</p>
      <p className="text-sm text-gray-500 mt-1">{description}</p>
    </div>
  );
}
```

- [ ] **Step 5: 创建 AlertCard 组件**

创建 `webui/src/components/cards/AlertCard.tsx`：

```tsx
interface AlertCardProps {
  level: 'warning' | 'danger' | 'info';
  title: string;
  message: string;
}

const levelStyles: Record<string, string> = {
  warning: 'bg-yellow-50 border-yellow-300 text-yellow-800',
  danger: 'bg-red-50 border-red-300 text-red-800',
  info: 'bg-blue-50 border-blue-300 text-blue-800',
};

const levelIcons: Record<string, string> = {
  warning: '⚠️',
  danger: '🚨',
  info: 'ℹ️',
};

export default function AlertCard({ level, title, message }: AlertCardProps) {
  return (
    <div className={`rounded-xl border p-4 ${levelStyles[level]}`}>
      <div className="flex items-start gap-2">
        <span className="text-lg">{levelIcons[level]}</span>
        <div>
          <p className="font-semibold">{title}</p>
          <p className="text-sm mt-0.5 opacity-90">{message}</p>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 6: 创建 LoadingSpinner 组件**

创建 `webui/src/components/common/LoadingSpinner.tsx`：

```tsx
export default function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="w-8 h-8 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
    </div>
  );
}
```

- [ ] **Step 7: 编写 Pagination 组件测试**

创建 `webui/src/__tests__/Pagination.test.tsx`：

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Pagination from '../components/common/Pagination';

describe('Pagination', () => {
  it('渲染页码信息', () => {
    render(<Pagination page={1} size={20} total={100} onPageChange={vi.fn()} />);
    expect(screen.getByText(/第 1 页/)).toBeInTheDocument();
    expect(screen.getByText(/共 5 页/)).toBeInTheDocument();
  });

  it('第一页时上一页按钮禁用', () => {
    render(<Pagination page={1} size={20} total={100} onPageChange={vi.fn()} />);
    const prevBtn = screen.getByText('上一页');
    expect(prevBtn).toBeDisabled();
  });

  it('点击下一页触发回调', () => {
    const onPageChange = vi.fn();
    render(<Pagination page={1} size={20} total={100} onPageChange={onPageChange} />);
    const nextBtn = screen.getByText('下一页');
    fireEvent.click(nextBtn);
    expect(onPageChange).toHaveBeenCalledWith(2);
  });

  it('最后一页时下一页按钮禁用', () => {
    render(<Pagination page={5} size={20} total={100} onPageChange={vi.fn()} />);
    const nextBtn = screen.getByText('下一页');
    expect(nextBtn).toBeDisabled();
  });
});
```

- [ ] **Step 8: 运行测试验证失败**

Run: `cd webui && npx vitest run src/__tests__/Pagination.test.tsx`
Expected: FAIL — `Cannot find module '../components/common/Pagination'`

- [ ] **Step 9: 创建 Pagination 组件**

创建 `webui/src/components/common/Pagination.tsx`：

```tsx
interface PaginationProps {
  page: number;
  size: number;
  total: number;
  onPageChange: (page: number) => void;
}

export default function Pagination({ page, size, total, onPageChange }: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / size));

  return (
    <div className="flex items-center justify-between py-3">
      <p className="text-sm text-gray-500">
        第 {page} 页，共 {totalPages} 页（{total} 条记录）
      </p>
      <div className="flex gap-2">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
        >
          上一页
        </button>
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
        >
          下一页
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 10: 创建 TimeRangeSelector 组件**

创建 `webui/src/components/common/TimeRangeSelector.tsx`：

```tsx
import { TIME_RANGE_OPTIONS } from '../../utils/constants';

interface TimeRangeSelectorProps {
  value: number;
  onChange: (days: number) => void;
}

export default function TimeRangeSelector({ value, onChange }: TimeRangeSelectorProps) {
  return (
    <div className="flex gap-1">
      {TIME_RANGE_OPTIONS.map((option) => (
        <button
          key={option.value}
          onClick={() => onChange(option.value)}
          className={`px-3 py-1.5 text-sm rounded-lg font-medium transition-colors ${
            value === option.value
              ? 'bg-primary-600 text-white'
              : 'bg-white text-gray-600 border border-gray-300 hover:bg-gray-50'
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 11: 运行全部测试验证通过**

Run: `cd webui && npx vitest run`
Expected: 全部 PASS

- [ ] **Step 12: Commit**

```bash
git add webui/src/components/ webui/src/__tests__/
git commit -m "feat(webui): add shared components (StatCard/StatusCard/AlertCard/Pagination/TimeRangeSelector/LoadingSpinner)"
```

---

## Task 6: 自定义 Hooks

**Files:**
- Create: `webui/src/hooks/useTimeRange.ts`
- Create: `webui/src/hooks/useApi.ts`
- Test: `webui/src/__tests__/useTimeRange.test.ts`

- [ ] **Step 1: 编写 useTimeRange Hook 测试**

创建 `webui/src/__tests__/useTimeRange.test.ts`：

```typescript
import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useTimeRange } from '../hooks/useTimeRange';

describe('useTimeRange', () => {
  it('默认值为传入的初始值', () => {
    const { result } = renderHook(() => useTimeRange(90));
    expect(result.current.days).toBe(90);
  });

  it('setDays 更新天数', () => {
    const { result } = renderHook(() => useTimeRange(90));
    act(() => {
      result.current.setDays(30);
    });
    expect(result.current.days).toBe(30);
  });
});
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd webui && npx vitest run src/__tests__/useTimeRange.test.ts`
Expected: FAIL — `Cannot find module '../hooks/useTimeRange'`

- [ ] **Step 3: 创建 useTimeRange Hook**

创建 `webui/src/hooks/useTimeRange.ts`：

```typescript
import { useState, useCallback } from 'react';

/**
 * 时间范围状态管理 Hook
 * @param defaultDays 默认天数
 */
export function useTimeRange(defaultDays: number) {
  const [days, setDays] = useState(defaultDays);

  const handleDaysChange = useCallback((newDays: number) => {
    setDays(newDays);
  }, []);

  return { days, setDays: handleDaysChange };
}
```

- [ ] **Step 4: 创建 useApi Hook**

创建 `webui/src/hooks/useApi.ts`：

```typescript
import { useState, useCallback } from 'react';

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

/**
 * 通用 API 请求 Hook
 * @param apiFn API 调用函数
 */
export function useApi<T, A extends unknown[]>(apiFn: (...args: A) => Promise<T>) {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: false,
    error: null,
  });

  const execute = useCallback(
    async (...args: A) => {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      try {
        const data = await apiFn(...args);
        setState({ data, loading: false, error: null });
        return data;
      } catch (err) {
        const message = err instanceof Error ? err.message : '请求失败';
        setState((prev) => ({ ...prev, loading: false, error: message }));
        return null;
      }
    },
    [apiFn],
  );

  return { ...state, execute };
}
```

- [ ] **Step 5: 运行测试验证通过**

Run: `cd webui && npx vitest run src/__tests__/useTimeRange.test.ts`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add webui/src/hooks/ webui/src/__tests__/useTimeRange.test.ts
git commit -m "feat(webui): add useTimeRange and useApi custom hooks"
```

---

## Task 7: Dashboard 页面

**Files:**
- Modify: `webui/src/pages/DashboardPage.tsx`
- Test: `webui/src/__tests__/DashboardPage.test.tsx`

- [ ] **Step 1: 编写 Dashboard 页面测试**

创建 `webui/src/__tests__/DashboardPage.test.tsx`：

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import DashboardPage from '../pages/DashboardPage';

// Mock API
vi.mock('../api/dashboard', () => ({
  getDashboard: vi.fn().mockResolvedValue({
    today: {
      has_activity: true,
      distance_m: 10234,
      duration_s: 3300,
      pace_s_per_km: 323,
      avg_hr: 155,
      vdot: 45.2,
      tss: 85,
    },
    weekly: {
      total_distance_m: 42000,
      total_duration_s: 12600,
      total_tss: 350,
      run_count: 4,
    },
  }),
}));

function renderWithRouter(ui: React.ReactElement) {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
}

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('渲染页面标题', () => {
    renderWithRouter(<DashboardPage />);
    expect(screen.getByText('今日概览')).toBeInTheDocument();
  });

  it('有跑步活动时展示统计卡片', async () => {
    renderWithRouter(<DashboardPage />);
    // 等待数据加载
    const distanceCard = await screen.findByText(/10\.23 km/);
    expect(distanceCard).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd webui && npx vitest run src/__tests__/DashboardPage.test.tsx`
Expected: FAIL — DashboardPage 当前是占位组件

- [ ] **Step 3: 实现 Dashboard 页面**

修改 `webui/src/pages/DashboardPage.tsx`：

```tsx
import { useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { useTimeRange } from '../hooks/useTimeRange';
import { getDashboard } from '../api/dashboard';
import { DEFAULT_TIME_RANGES } from '../utils/constants';
import { formatPace, formatDuration, formatDistance, formatHeartRate, formatVdot } from '../utils/format';
import StatCard from '../components/cards/StatCard';
import LoadingSpinner from '../components/common/LoadingSpinner';
import TimeRangeSelector from '../components/common/TimeRangeSelector';
import type { DashboardResponse } from '../types/api';

export default function DashboardPage() {
  const { days, setDays } = useTimeRange(DEFAULT_TIME_RANGES.dashboard);
  const { data, loading, execute } = useApi<DashboardResponse, [number]>(getDashboard);

  useEffect(() => {
    execute(days);
  }, [days, execute]);

  return (
    <div className="space-y-6">
      {/* 页面标题 + 时间范围 */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900">今日概览</h2>
        <TimeRangeSelector value={days} onChange={setDays} />
      </div>

      {loading && <LoadingSpinner />}

      {data && (
        <>
          {/* 今日数据 */}
          <section>
            <h3 className="text-sm font-medium text-gray-500 mb-3">今日</h3>
            {data.today.has_activity ? (
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <StatCard title="距离" value={formatDistance(data.today.distance_m)} />
                <StatCard title="时长" value={formatDuration(data.today.duration_s)} />
                <StatCard title="配速" value={formatPace(data.today.pace_s_per_km)} />
                <StatCard title="心率" value={data.today.avg_hr ? formatHeartRate(data.today.avg_hr) : '--'} />
              </div>
            ) : (
              <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
                <p className="text-gray-400 text-lg">🛌 休息日</p>
                <p className="text-gray-400 text-sm mt-1">今天没有跑步记录</p>
              </div>
            )}
          </section>

          {/* 本周统计 */}
          <section>
            <h3 className="text-sm font-medium text-gray-500 mb-3">本周统计</h3>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <StatCard title="总距离" value={formatDistance(data.weekly.total_distance_m)} />
              <StatCard title="总时长" value={formatDuration(data.weekly.total_duration_s)} />
              <StatCard title="总TSS" value={data.weekly.total_tss.toFixed(0)} />
              <StatCard title="跑步次数" value={`${data.weekly.run_count} 次`} />
            </div>
          </section>

          {/* 快捷入口 */}
          <section>
            <h3 className="text-sm font-medium text-gray-500 mb-3">快捷入口</h3>
            <div className="grid grid-cols-3 gap-3">
              <a
                href="/vdot"
                className="bg-white rounded-xl border border-gray-200 p-4 text-center hover:border-primary-300 transition-colors"
              >
                <p className="text-2xl">📈</p>
                <p className="text-sm font-medium text-gray-700 mt-1">VDOT趋势</p>
              </a>
              <a
                href="/training-load"
                className="bg-white rounded-xl border border-gray-200 p-4 text-center hover:border-primary-300 transition-colors"
              >
                <p className="text-2xl">💪</p>
                <p className="text-sm font-medium text-gray-700 mt-1">训练负荷</p>
              </a>
              <a
                href="/activities"
                className="bg-white rounded-xl border border-gray-200 p-4 text-center hover:border-primary-300 transition-colors"
              >
                <p className="text-2xl">🏃</p>
                <p className="text-sm font-medium text-gray-700 mt-1">活动记录</p>
              </a>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd webui && npx vitest run src/__tests__/DashboardPage.test.tsx`
Expected: PASS

- [ ] **Step 5: 验证 TypeScript 编译**

Run: `cd webui && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 6: Commit**

```bash
git add webui/src/pages/DashboardPage.tsx webui/src/__tests__/DashboardPage.test.tsx
git commit -m "feat(webui): implement DashboardPage with today overview, weekly stats, and quick links"
```

---

## Task 8: VDOT 趋势页面

**Files:**
- Create: `webui/src/components/charts/VdotTrendChart.tsx`
- Modify: `webui/src/pages/VdotPage.tsx`
- Test: `webui/src/__tests__/VdotPage.test.tsx`

- [ ] **Step 1: 创建 VdotTrendChart 组件**

创建 `webui/src/components/charts/VdotTrendChart.tsx`：

```tsx
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import type { VdotTrendItem } from '../../types/api';

interface VdotTrendChartProps {
  data: VdotTrendItem[];
}

export default function VdotTrendChart({ data }: VdotTrendChartProps) {
  if (data.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
        暂无VDOT数据
      </div>
    );
  }

  // 计算平均值用于参考线
  const avgVdot = data.reduce((sum, item) => sum + item.vdot, 0) / data.length;

  const chartData = data.map((item) => ({
    date: item.date.slice(5), // MM-DD
    vdot: item.vdot,
    fullDate: item.date,
  }));

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#9ca3af" />
          <YAxis
            domain={['dataMin - 1', 'dataMax + 1']}
            tick={{ fontSize: 12 }}
            stroke="#9ca3af"
          />
          <Tooltip
            formatter={(value: number) => [value.toFixed(1), 'VDOT']}
            labelFormatter={(label: string) => {
              const item = chartData.find((d) => d.date === label);
              return item?.fullDate || label;
            }}
          />
          <ReferenceLine
            y={avgVdot}
            stroke="#9ca3af"
            strokeDasharray="5 5"
            label={{ value: `均值 ${avgVdot.toFixed(1)}`, position: 'insideTopRight', fontSize: 11, fill: '#9ca3af' }}
          />
          <Line
            type="monotone"
            dataKey="vdot"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={{ r: 3, fill: '#3b82f6' }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 2: 编写 VDOT 页面测试**

创建 `webui/src/__tests__/VdotPage.test.tsx`：

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import VdotPage from '../pages/VdotPage';

vi.mock('../api/vdot', () => ({
  getVdotTrend: vi.fn().mockResolvedValue({
    items: [
      { date: '2024-01-01', vdot: 44.0, distance_m: 10000, duration_s: 3000 },
      { date: '2024-01-15', vdot: 45.2, distance_m: 10000, duration_s: 2900 },
      { date: '2024-02-01', vdot: 46.1, distance_m: 12000, duration_s: 3600 },
    ],
    days: 90,
  }),
}));

function renderWithRouter(ui: React.ReactElement) {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
}

describe('VdotPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('渲染页面标题', () => {
    renderWithRouter(<VdotPage />);
    expect(screen.getByText('VDOT 趋势')).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: 实现 VDOT 页面**

修改 `webui/src/pages/VdotPage.tsx`：

```tsx
import { useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { useTimeRange } from '../hooks/useTimeRange';
import { getVdotTrend } from '../api/vdot';
import { DEFAULT_TIME_RANGES } from '../utils/constants';
import LoadingSpinner from '../components/common/LoadingSpinner';
import TimeRangeSelector from '../components/common/TimeRangeSelector';
import VdotTrendChart from '../components/charts/VdotTrendChart';
import type { VdotTrendResponse } from '../types/api';

export default function VdotPage() {
  const { days, setDays } = useTimeRange(DEFAULT_TIME_RANGES.vdot);
  const { data, loading, execute } = useApi<VdotTrendResponse, [number]>(getVdotTrend);

  useEffect(() => {
    execute(days);
  }, [days, execute]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900">VDOT 趋势</h2>
        <TimeRangeSelector value={days} onChange={setDays} />
      </div>

      {loading && <LoadingSpinner />}

      {data && (
        <>
          {/* VDOT趋势图 */}
          <VdotTrendChart data={data.items} />

          {/* 数据摘要 */}
          {data.items.length > 0 && (
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
                <p className="text-sm text-gray-500">最新VDOT</p>
                <p className="text-2xl font-bold text-primary-600">
                  {data.items[data.items.length - 1].vdot.toFixed(1)}
                </p>
              </div>
              <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
                <p className="text-sm text-gray-500">最高VDOT</p>
                <p className="text-2xl font-bold text-green-600">
                  {Math.max(...data.items.map((i) => i.vdot)).toFixed(1)}
                </p>
              </div>
              <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
                <p className="text-sm text-gray-500">数据点</p>
                <p className="text-2xl font-bold text-gray-900">{data.items.length}</p>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd webui && npx vitest run src/__tests__/VdotPage.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add webui/src/components/charts/VdotTrendChart.tsx webui/src/pages/VdotPage.tsx webui/src/__tests__/VdotPage.test.tsx
git commit -m "feat(webui): implement VdotPage with trend chart and summary cards"
```

---

## Task 9: 训练负荷页面

**Files:**
- Create: `webui/src/components/charts/TrainingLoadChart.tsx`
- Modify: `webui/src/pages/TrainingLoadPage.tsx`
- Test: `webui/src/__tests__/TrainingLoadPage.test.tsx`

- [ ] **Step 1: 创建 TrainingLoadChart 组件**

创建 `webui/src/components/charts/TrainingLoadChart.tsx`：

```tsx
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
} from 'recharts';
import type { TrainingLoadTrendItem } from '../../types/api';

interface TrainingLoadChartProps {
  data: TrainingLoadTrendItem[];
}

export default function TrainingLoadChart({ data }: TrainingLoadChartProps) {
  if (data.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
        暂无训练负荷数据
      </div>
    );
  }

  const chartData = data.map((item) => ({
    date: item.date.slice(5),
    atl: Number(item.atl.toFixed(1)),
    ctl: Number(item.ctl.toFixed(1)),
    tsb: Number(item.tsb.toFixed(1)),
    fullDate: item.date,
  }));

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <ResponsiveContainer width="100%" height={320}>
        <AreaChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#9ca3af" />
          <YAxis tick={{ fontSize: 12 }} stroke="#9ca3af" />
          <Tooltip
            formatter={(value: number, name: string) => {
              const labels: Record<string, string> = { atl: 'ATL', ctl: 'CTL', tsb: 'TSB' };
              return [value.toFixed(1), labels[name] || name];
            }}
          />
          <Legend formatter={(value: string) => {
            const labels: Record<string, string> = { atl: 'ATL (急性)', ctl: 'CTL (慢性)', tsb: 'TSB (平衡)' };
            return labels[value] || value;
          }} />
          <ReferenceLine y={0} stroke="#d1d5db" />
          <Area type="monotone" dataKey="atl" stroke="#f97316" fill="#fed7aa" fillOpacity={0.5} strokeWidth={2} />
          <Area type="monotone" dataKey="ctl" stroke="#3b82f6" fill="#bfdbfe" fillOpacity={0.5} strokeWidth={2} />
          <Area type="monotone" dataKey="tsb" stroke="#10b981" fill="#a7f3d0" fillOpacity={0.3} strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 2: 编写训练负荷页面测试**

创建 `webui/src/__tests__/TrainingLoadPage.test.tsx`：

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import TrainingLoadPage from '../pages/TrainingLoadPage';

vi.mock('../api/training-load', () => ({
  getTrainingLoad: vi.fn().mockResolvedValue({
    current: { atl: 55, ctl: 65, tsb: 10, fitness_status: '最佳' },
    days: 42,
  }),
  getTrainingLoadTrend: vi.fn().mockResolvedValue({
    items: [
      { date: '2024-01-01', atl: 50, ctl: 60, tsb: 10 },
      { date: '2024-01-15', atl: 55, ctl: 65, tsb: 10 },
    ],
    days: 42,
  }),
}));

function renderWithRouter(ui: React.ReactElement) {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
}

describe('TrainingLoadPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('渲染页面标题', () => {
    renderWithRouter(<TrainingLoadPage />);
    expect(screen.getByText('训练负荷')).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: 实现训练负荷页面**

修改 `webui/src/pages/TrainingLoadPage.tsx`：

```tsx
import { useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { useTimeRange } from '../hooks/useTimeRange';
import { getTrainingLoad, getTrainingLoadTrend } from '../api/training-load';
import { DEFAULT_TIME_RANGES, getFitnessStatus, getFitnessStatusColor, getFitnessStatusBg } from '../utils/constants';
import LoadingSpinner from '../components/common/LoadingSpinner';
import TimeRangeSelector from '../components/common/TimeRangeSelector';
import TrainingLoadChart from '../components/charts/TrainingLoadChart';
import StatusCard from '../components/cards/StatusCard';
import AlertCard from '../components/cards/AlertCard';
import type { TrainingLoadResponse, TrainingLoadTrendResponse } from '../types/api';

export default function TrainingLoadPage() {
  const { days, setDays } = useTimeRange(DEFAULT_TIME_RANGES.trainingLoad);
  const { data: loadData, loading: loadLoading, execute: executeLoad } = useApi<TrainingLoadResponse, [number]>(getTrainingLoad);
  const { data: trendData, loading: trendLoading, execute: executeTrend } = useApi<TrainingLoadTrendResponse, [number]>(getTrainingLoadTrend);

  useEffect(() => {
    executeLoad(days);
    executeTrend(days);
  }, [days, executeLoad, executeTrend]);

  const loading = loadLoading || trendLoading;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900">训练负荷</h2>
        <TimeRangeSelector value={days} onChange={setDays} />
      </div>

      {loading && <LoadingSpinner />}

      {loadData && (
        <>
          {/* 当前状态 */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <div className={`rounded-xl border p-4 ${getFitnessStatusBg(loadData.current.fitness_status)}`}>
              <p className="text-sm text-gray-500 font-medium">疲劳状态</p>
              <p className={`mt-1 text-xl font-bold ${getFitnessStatusColor(loadData.current.fitness_status)}`}>
                {loadData.current.fitness_status}
              </p>
            </div>
            <StatusCard title="ATL (急性)" status={loadData.current.atl.toFixed(1)} description="7天训练负荷" />
            <StatusCard title="CTL (慢性)" status={loadData.current.ctl.toFixed(1)} description="42天体能基础" />
            <StatusCard title="TSB (平衡)" status={loadData.current.tsb.toFixed(1)} description="CTL - ATL" />
          </div>

          {/* 过度训练预警 */}
          {loadData.current.tsb < -30 && (
            <AlertCard
              level="danger"
              title="过度训练预警"
              message={`TSB = ${loadData.current.tsb.toFixed(1)}，训练负荷过高，建议减少训练量或增加休息日`}
            />
          )}
        </>
      )}

      {/* 趋势图 */}
      {trendData && <TrainingLoadChart data={trendData.items} />}
    </div>
  );
}
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd webui && npx vitest run src/__tests__/TrainingLoadPage.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add webui/src/components/charts/TrainingLoadChart.tsx webui/src/pages/TrainingLoadPage.tsx webui/src/__tests__/TrainingLoadPage.test.tsx
git commit -m "feat(webui): implement TrainingLoadPage with ATL/CTL/TSB chart and fatigue alerts"
```

---

## Task 10: 活动列表页面

**Files:**
- Modify: `webui/src/pages/ActivitiesPage.tsx`
- Test: `webui/src/__tests__/ActivitiesPage.test.tsx`

- [ ] **Step 1: 编写活动列表页面测试**

创建 `webui/src/__tests__/ActivitiesPage.test.tsx`：

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import ActivitiesPage from '../pages/ActivitiesPage';

vi.mock('../api/activities', () => ({
  getActivities: vi.fn().mockResolvedValue({
    items: [
      { id: 'abc123', date: '2024-01-15', distance_m: 10000, duration_s: 3300, pace_s_per_km: 330, avg_hr: 155, vdot: 45.2, tss: 85 },
      { id: 'def456', date: '2024-01-14', distance_m: 5000, duration_s: 1800, pace_s_per_km: 360, avg_hr: 145, vdot: 42.0, tss: 40 },
    ],
    total: 2,
    page: 1,
    size: 20,
  }),
}));

function renderWithRouter(ui: React.ReactElement) {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
}

describe('ActivitiesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('渲染页面标题', () => {
    renderWithRouter(<ActivitiesPage />);
    expect(screen.getByText('活动记录')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd webui && npx vitest run src/__tests__/ActivitiesPage.test.tsx`
Expected: FAIL — ActivitiesPage 当前是占位组件

- [ ] **Step 3: 实现活动列表页面**

修改 `webui/src/pages/ActivitiesPage.tsx`：

```tsx
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { getActivities } from '../api/activities';
import type { ActivitiesParams } from '../api/activities';
import { formatPace, formatDuration, formatDistance, formatDateString } from '../utils/format';
import LoadingSpinner from '../components/common/LoadingSpinner';
import Pagination from '../components/common/Pagination';
import type { ActivitiesResponse } from '../types/api';

export default function ActivitiesPage() {
  const [page, setPage] = useState(1);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const { data, loading, execute } = useApi<ActivitiesResponse, [ActivitiesParams]>(getActivities);

  useEffect(() => {
    const params: ActivitiesParams = { page, size: 20 };
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    execute(params);
  }, [page, startDate, endDate, execute]);

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
  };

  const handleFilterReset = () => {
    setStartDate('');
    setEndDate('');
    setPage(1);
  };

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900">活动记录</h2>

      {/* 筛选器 */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 flex flex-wrap items-end gap-3">
        <div>
          <label className="block text-xs text-gray-500 mb-1">开始日期</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => { setStartDate(e.target.value); setPage(1); }}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">结束日期</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => { setEndDate(e.target.value); setPage(1); }}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
        <button
          onClick={handleFilterReset}
          className="px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          重置
        </button>
      </div>

      {loading && <LoadingSpinner />}

      {data && (
        <>
          {/* 活动列表 */}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">日期</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-500">距离</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-500">时长</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-500">配速</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-500">心率</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.items.map((activity) => (
                  <tr key={activity.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <Link to={`/activities/${activity.id}`} className="text-primary-600 hover:underline font-medium">
                        {formatDateString(activity.date)}
                      </Link>
                    </td>
                    <td className="text-right px-4 py-3 text-gray-700">{formatDistance(activity.distance_m)}</td>
                    <td className="text-right px-4 py-3 text-gray-700">{formatDuration(activity.duration_s)}</td>
                    <td className="text-right px-4 py-3 text-gray-700">{formatPace(activity.pace_s_per_km)}</td>
                    <td className="text-right px-4 py-3 text-gray-700">
                      {activity.avg_hr ? `${activity.avg_hr} bpm` : '--'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 分页 */}
          {data.total > 0 && (
            <Pagination page={data.page} size={data.size} total={data.total} onPageChange={handlePageChange} />
          )}
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd webui && npx vitest run src/__tests__/ActivitiesPage.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add webui/src/pages/ActivitiesPage.tsx webui/src/__tests__/ActivitiesPage.test.tsx
git commit -m "feat(webui): implement ActivitiesPage with filter, table, and pagination"
```

---

## Task 11: 活动详情页面

**Files:**
- Create: `webui/src/components/charts/PaceChart.tsx`
- Create: `webui/src/components/charts/HeartRateChart.tsx`
- Modify: `webui/src/pages/ActivityDetailPage.tsx`

- [ ] **Step 1: 创建 PaceChart 组件**

创建 `webui/src/components/charts/PaceChart.tsx`：

```tsx
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { ActivitySplit } from '../../types/api';
import { formatPace } from '../../utils/format';

interface PaceChartProps {
  splits: ActivitySplit[];
}

export default function PaceChart({ splits }: PaceChartProps) {
  if (splits.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
        暂无配速数据
      </div>
    );
  }

  const chartData = splits.map((split) => ({
    km: `${split.km}`,
    pace: split.pace_s_per_km,
    paceLabel: formatPace(split.pace_s_per_km),
  }));

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <h4 className="text-sm font-medium text-gray-500 mb-3">配速曲线</h4>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="km" tick={{ fontSize: 12 }} stroke="#9ca3af" label={{ value: 'km', position: 'insideBottomRight', offset: -5, fontSize: 11 }} />
          <YAxis
            domain={['dataMin - 10', 'dataMax + 10']}
            tick={{ fontSize: 12 }}
            stroke="#9ca3af"
            tickFormatter={(value: number) => formatPace(value)}
          />
          <Tooltip formatter={(value: number) => [formatPace(value), '配速']} />
          <Bar dataKey="pace" fill="#3b82f6" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 2: 创建 HeartRateChart 组件**

创建 `webui/src/components/charts/HeartRateChart.tsx`：

```tsx
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { HrTrackPoint } from '../../types/api';

interface HeartRateChartProps {
  data: HrTrackPoint[];
}

export default function HeartRateChart({ data }: HeartRateChartProps) {
  if (data.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
        暂无心率数据
      </div>
    );
  }

  // 降采样：最多显示200个点
  const sampled = data.length > 200
    ? data.filter((_, i) => i % Math.ceil(data.length / 200) === 0)
    : data;

  const chartData = sampled.map((point) => ({
    time: `${Math.floor(point.time_s / 60)}'${(point.time_s % 60).toString().padStart(2, '0')}"`,
    hr: point.hr,
  }));

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <h4 className="text-sm font-medium text-gray-500 mb-3">心率曲线</h4>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="time" tick={{ fontSize: 10 }} stroke="#9ca3af" interval="preserveStartEnd" />
          <YAxis domain={['dataMin - 5', 'dataMax + 5']} tick={{ fontSize: 12 }} stroke="#9ca3af" />
          <Tooltip formatter={(value: number) => [`${value} bpm`, '心率']} />
          <Line type="monotone" dataKey="hr" stroke="#ef4444" strokeWidth={1.5} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 3: 实现活动详情页面**

修改 `webui/src/pages/ActivityDetailPage.tsx`：

```tsx
import { useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { getActivityDetail } from '../api/activities';
import { formatPace, formatDuration, formatDistance, formatHeartRate, formatVdot, formatDateString } from '../utils/format';
import StatCard from '../components/cards/StatCard';
import LoadingSpinner from '../components/common/LoadingSpinner';
import PaceChart from '../components/charts/PaceChart';
import HeartRateChart from '../components/charts/HeartRateChart';
import type { ActivityDetailResponse } from '../types/api';

export default function ActivityDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data, loading, execute } = useApi<ActivityDetailResponse, [string]>(getActivityDetail);

  useEffect(() => {
    if (id) {
      execute(id);
    }
  }, [id, execute]);

  if (loading) return <LoadingSpinner />;

  if (!data) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-400">未找到活动数据</p>
        <Link to="/activities" className="text-primary-600 hover:underline mt-2 inline-block">
          返回活动列表
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 返回按钮 + 日期 */}
      <div className="flex items-center gap-3">
        <Link to="/activities" className="text-primary-600 hover:underline text-sm">
          ← 返回列表
        </Link>
        <h2 className="text-xl font-bold text-gray-900">{formatDateString(data.date)}</h2>
      </div>

      {/* 基础数据 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard title="距离" value={formatDistance(data.distance_m)} />
        <StatCard title="时长" value={formatDuration(data.duration_s)} />
        <StatCard title="配速" value={formatPace(data.pace_s_per_km)} />
        <StatCard title="心率" value={data.avg_hr ? formatHeartRate(data.avg_hr) : '--'} />
      </div>

      {/* 详细数据 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard title="VDOT" value={data.vdot ? formatVdot(data.vdot) : '--'} />
        <StatCard title="TSS" value={data.tss ? data.tss.toFixed(0) : '--'} />
        <StatCard title="最大心率" value={data.max_hr ? formatHeartRate(data.max_hr) : '--'} />
        <StatCard title="卡路里" value={data.calories ? `${data.calories} kcal` : '--'} />
      </div>

      {/* 配速曲线 */}
      <PaceChart splits={data.splits} />

      {/* 心率曲线 */}
      <HeartRateChart data={data.hr_track} />
    </div>
  );
}
```

- [ ] **Step 4: 验证 TypeScript 编译**

Run: `cd webui && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 5: Commit**

```bash
git add webui/src/components/charts/PaceChart.tsx webui/src/components/charts/HeartRateChart.tsx webui/src/pages/ActivityDetailPage.tsx
git commit -m "feat(webui): implement ActivityDetailPage with pace/heart rate charts"
```

---

## Task 12: 身体信号页面

**Files:**
- Modify: `webui/src/pages/BodySignalsPage.tsx`

- [ ] **Step 1: 实现身体信号页面**

修改 `webui/src/pages/BodySignalsPage.tsx`：

```tsx
import { useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { useTimeRange } from '../hooks/useTimeRange';
import { getHrv, getFatigue, getRecovery } from '../api/body-signals';
import { DEFAULT_TIME_RANGES } from '../utils/constants';
import LoadingSpinner from '../components/common/LoadingSpinner';
import TimeRangeSelector from '../components/common/TimeRangeSelector';
import StatusCard from '../components/cards/StatusCard';
import type { HrvResponse, FatigueResponse, RecoveryResponse } from '../types/api';

export default function BodySignalsPage() {
  const { days, setDays } = useTimeRange(DEFAULT_TIME_RANGES.bodySignals);
  const { data: hrvData, loading: hrvLoading, execute: executeHrv } = useApi<HrvResponse, [number]>(getHrv);
  const { data: fatigueData, loading: fatigueLoading, execute: executeFatigue } = useApi<FatigueResponse, []>(getFatigue);
  const { data: recoveryData, loading: recoveryLoading, execute: executeRecovery } = useApi<RecoveryResponse, []>(getRecovery);

  useEffect(() => {
    executeHrv(days);
    executeFatigue();
    executeRecovery();
  }, [days, executeHrv, executeFatigue, executeRecovery]);

  const loading = hrvLoading || fatigueLoading || recoveryLoading;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900">身体信号</h2>
        <TimeRangeSelector value={days} onChange={setDays} />
      </div>

      {loading && <LoadingSpinner />}

      {/* HRV 状态 */}
      {hrvData && (
        <section>
          <h3 className="text-sm font-medium text-gray-500 mb-3">HRV 状态</h3>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <StatusCard
              title="RMSSD"
              status={hrvData.data.rmssd ? hrvData.data.rmssd.toFixed(1) + ' ms' : '--'}
              description="心率变异主要指标"
            />
            <StatusCard
              title="SDNN"
              status={hrvData.data.sdnn ? hrvData.data.sdnn.toFixed(1) + ' ms' : '--'}
              description="心率变异综合指标"
            />
            <StatusCard
              title="静息心率"
              status={hrvData.data.resting_hr ? `${hrvData.data.resting_hr} bpm` : '--'}
              description="晨起静息心率"
            />
            <StatusCard
              title="HRV状态"
              status={hrvData.data.status}
              description={`近${hrvData.data.trend.length}天趋势`}
            />
          </div>
        </section>
      )}

      {/* 疲劳度 */}
      {fatigueData && (
        <section>
          <h3 className="text-sm font-medium text-gray-500 mb-3">疲劳度</h3>
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm text-gray-500">疲劳评分</span>
              <span className="text-2xl font-bold text-gray-900">{fatigueData.data.score.toFixed(0)}</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all ${
                  fatigueData.data.score < 30 ? 'bg-green-500' :
                  fatigueData.data.score < 60 ? 'bg-yellow-500' :
                  'bg-red-500'
                }`}
                style={{ width: `${Math.min(fatigueData.data.score, 100)}%` }}
              />
            </div>
            <div className="mt-3 flex items-center justify-between">
              <span className={`text-sm font-medium ${
                fatigueData.data.status === '低疲劳' ? 'text-green-600' :
                fatigueData.data.status === '中等疲劳' ? 'text-yellow-600' :
                'text-red-600'
              }`}>
                {fatigueData.data.status}
              </span>
              <span className="text-xs text-gray-400">{fatigueData.data.recommendation}</span>
            </div>
          </div>
        </section>
      )}

      {/* 恢复状态 */}
      {recoveryData && (
        <section>
          <h3 className="text-sm font-medium text-gray-500 mb-3">恢复状态</h3>
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center gap-3 mb-2">
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                recoveryData.data.status === '充分恢复' ? 'bg-green-100 text-green-800' :
                recoveryData.data.status === '部分恢复' ? 'bg-yellow-100 text-yellow-800' :
                'bg-red-100 text-red-800'
              }`}>
                {recoveryData.data.status}
              </span>
              {recoveryData.data.hours_since_last_run !== null && (
                <span className="text-xs text-gray-400">
                  距上次跑步 {recoveryData.data.hours_since_last_run.toFixed(0)} 小时
                </span>
              )}
            </div>
            <p className="text-sm text-gray-600">{recoveryData.data.recommendation}</p>
          </div>
        </section>
      )}
    </div>
  );
}
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `cd webui && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 3: Commit**

```bash
git add webui/src/pages/BodySignalsPage.tsx
git commit -m "feat(webui): implement BodySignalsPage with HRV, fatigue, and recovery cards"
```

---

## Task 13: 全量验证与构建

**Files:** 无新增修改

- [ ] **Step 1: 运行全部测试**

Run: `cd webui && npx vitest run`
Expected: 全部 PASS

- [ ] **Step 2: 运行 TypeScript 编译检查**

Run: `cd webui && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 3: 运行生产构建**

Run: `cd webui && npm run build`
Expected: 构建成功，输出到 `webui/dist/`

- [ ] **Step 4: 验证构建产物**

Run: `ls webui/dist/index.html`
Expected: 文件存在

Run: `ls webui/dist/assets/`
Expected: 包含 JS 和 CSS 文件

- [ ] **Step 5: 最终 Commit（如有 lint 修复）**

```bash
git add -A
git commit -m "chore(webui): final verification - all tests pass, build succeeds"
```

---

## Self-Review Checklist

### 1. Spec Coverage

| 需求 | 任务 | 覆盖 |
|------|------|------|
| REQ-D-17 今日概览卡片 | Task 7 (DashboardPage) | ✅ |
| REQ-D-18 本周统计卡片 | Task 7 (DashboardPage) | ✅ |
| REQ-D-19 快捷入口 | Task 7 (DashboardPage) | ✅ |
| REQ-D-20 VDOT历史趋势图 | Task 8 (VdotPage + VdotTrendChart) | ✅ |
| REQ-D-21 预测区间 | Task 8 (VdotTrendChart ReferenceLine) | ✅ P1 |
| REQ-D-22 关键节点标注 | Task 8 (VdotTrendChart dot) | ✅ P2 |
| REQ-D-23 ATL/CTL/TSB趋势图 | Task 9 (TrainingLoadChart) | ✅ |
| REQ-D-24 疲劳状态指示 | Task 9 (TrainingLoadPage) | ✅ |
| REQ-D-25 趋势预警 | Task 9 (AlertCard TSB<-30) | ✅ |
| REQ-D-26 跑步记录列表 | Task 10 (ActivitiesPage) | ✅ |
| REQ-D-27 筛选器 | Task 10 (日期筛选) | ✅ |
| REQ-D-28 分页加载 | Task 10 (Pagination) | ✅ |
| REQ-D-29 单次跑步详细数据 | Task 11 (ActivityDetailPage) | ✅ |
| REQ-D-30 配速/心率曲线 | Task 11 (PaceChart + HeartRateChart) | ✅ |
| REQ-D-31 数据标签 | Task 11 (ActivityDetailPage) | ✅ P2 |
| REQ-D-32 HRV状态卡片 | Task 12 (BodySignalsPage) | ✅ |
| REQ-D-33 疲劳度卡片 | Task 12 (BodySignalsPage) | ✅ |
| REQ-D-34 恢复状态卡片 | Task 12 (BodySignalsPage) | ✅ |
| REQ-D-35 时间范围筛选控件 | Task 5 (TimeRangeSelector) + Task 6 (useTimeRange) | ✅ |
| REQ-D-36 图表数据一致性 | Task 3 (API层薄封装) + ADR-019 | ✅ |

### 2. Placeholder Scan

- ✅ 无 TBD/TODO/占位符
- ✅ 所有代码步骤包含实际代码
- ✅ 所有测试步骤包含实际测试代码
- ✅ 所有命令步骤包含实际命令和预期输出
- ✅ 无 "类似 Task N" 的引用

### 3. Type Consistency

- ✅ `DashboardResponse` — Task 2 定义，Task 3/7 使用
- ✅ `VdotTrendResponse` — Task 2 定义，Task 3/8 使用
- ✅ `TrainingLoadResponse` / `TrainingLoadTrendResponse` — Task 2 定义，Task 3/9 使用
- ✅ `ActivitiesResponse` / `ActivityDetailResponse` — Task 2 定义，Task 3/10/11 使用
- ✅ `HrvResponse` / `FatigueResponse` / `RecoveryResponse` — Task 2 定义，Task 3/12 使用
- ✅ `formatPace` / `formatDuration` / `formatDistance` — Task 2 定义，Task 7-11 使用
- ✅ `useTimeRange` — Task 6 定义，Task 7-9/12 使用
- ✅ `useApi` — Task 6 定义，Task 7-12 使用
- ✅ `DEFAULT_TIME_RANGES` — Task 2 定义，Task 7-9/12 使用
- ✅ `getFitnessStatus` / `getFitnessStatusColor` / `getFitnessStatusBg` — Task 2 定义，Task 9 使用
