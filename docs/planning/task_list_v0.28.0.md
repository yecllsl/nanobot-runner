# 任务清单 — v0.28.0 WebUI数据可视化

> **版本**: v1.0
> **创建日期**: 2026-06-04
> **架构依据**: 架构设计说明书 v19.0.0 §11
> **需求依据**: REQ_需求规格说明书 v14.0 §5.4
> **评审依据**: 架构评审报告-v0.28.0 v1.0

---

## 1. 任务总览

| 指标 | 数值 |
|------|------|
| 任务总数 | 22 |
| P0任务数 | 10 |
| P1任务数 | 9 |
| P2任务数 | 3 |
| 总工作量估算 | ~88小时 |

---

## 2. 依赖关系图

```
T01(项目骨架) ──→ T02(FastAPI应用工厂) ──→ T03(认证中间件)
                       │                        │
                       ├─→ T04(配置管理)         │
                       │                        ↓
                       ├─→ T05(Dashboard API) ←──┘
                       ├─→ T06(VDOT API)
                       ├─→ T07(训练负荷API)
                       ├─→ T08(活动列表API)
                       ├─→ T09(活动详情API)
                       └─→ T10(身体信号API)
                                │
                                ↓
T11(前端项目骨架) ──→ T12(布局与导航) ──→ T13(Dashboard页)
                                │          ├─→ T14(VDOT页)
                                │          ├─→ T15(训练负荷页)
                                │          ├─→ T16(活动列表页) ──→ T17(活动详情页)
                                │          └─→ T18(身体信号页)
                                │
                                ├─→ T19(共享组件)
                                └─→ T20(时间范围Hook)

T05~T10 + T13~T18 ──→ T21(Gateway集成)
T21 ──→ T22(端到端验证)
```

**关键路径**: T01 → T02 → T05 → T13 → T21 → T22

---

## 3. 任务列表

### 3.1 后端基础层

#### T01: 项目骨架与依赖配置
- **优先级**: P0
- **依赖**: 无
- **工作量**: 2h
- **描述**: 新增fastapi依赖到pyproject.toml，创建src/webui/模块目录结构（__init__.py, app.py, config.py, auth.py, routes/, schemas/, services/）
- **验收标准**:
  1. `uv run python -c "import fastapi"` 成功
  2. `src/webui/` 目录结构完整，所有__init__.py就位
  3. `uv run ruff check src/webui/` 无错误

#### T02: FastAPI应用工厂
- **优先级**: P0
- **依赖**: T01
- **工作量**: 4h
- **描述**: 实现`create_webui_app()`应用工厂，包含：认证中间件注册、API路由注册（prefix=/api/webui）、健康检查端点、SPA catch-all路由（I-01）、静态文件服务
- **验收标准**:
  1. `create_webui_app()` 返回FastAPI实例
  2. `/api/webui/health` 返回 `{"status": "ok", "version": "0.28.0"}`
  3. API路由注册顺序正确（API先于SPA catch-all）
  4. 非API路径回退到index.html（I-01）
  5. 单元测试覆盖应用工厂

#### T03: 认证中间件
- **优先级**: P0
- **依赖**: T02
- **工作量**: 4h
- **描述**: 实现`TokenAuthMiddleware`，共享nanobot-ai WebSocket服务的token验证机制。验证请求Header中的`Authorization: Bearer <token>`，token来源为nanobot-ai token_issue_path签发的短期令牌。白名单路径：`/api/webui/health`
- **验收标准**:
  1. 无token请求返回401
  2. 有效token请求正常通过
  3. `/api/webui/health` 不需要认证
  4. token验证逻辑与nanobot-ai WebSocket一致（使用PyJWT + shared secret）
  5. 单元测试覆盖认证通过/拒绝/白名单场景

#### T04: WebUI配置管理
- **优先级**: P0
- **依赖**: T01
- **工作量**: 3h
- **描述**: ConfigManager新增`get_webui_config()`方法，config.json新增`webui`配置节（enabled/host/port/cors_origins/token_secret/token_ttl_s），环境变量覆盖`NANOBOT_WEBUI_*`，更新config.example.json
- **验收标准**:
  1. `get_webui_config()` 返回WebUI配置字典
  2. 环境变量 `NANOBOT_WEBUI_ENABLED=true` 可覆盖配置文件
  3. config.example.json 包含webui配置节示例
  4. 默认值：enabled=false, host=127.0.0.1, port=8766
  5. 单元测试覆盖配置读取和环境变量覆盖

---

### 3.2 后端API层

#### T05: Dashboard API
- **优先级**: P0
- **依赖**: T02, T03
- **工作量**: 4h
- **描述**: 实现仪表盘API端点`/api/webui/dashboard`，服务层调用`AnalyticsEngine.get_running_summary()`+`SessionRepository.get_recent_sessions()`，Pydantic Schema定义`DashboardResponse`（今日数据+本周统计），使用`run_in_threadpool()`包装同步调用
- **需求映射**: REQ-D-17, REQ-D-18
- **验收标准**:
  1. `GET /api/webui/dashboard?days=7` 返回仪表盘数据
  2. 数据与CLI `data stats` 输出一致（误差<0.1%）
  3. 无跑步日返回休息状态
  4. `run_in_threadpool()` 包装同步调用
  5. 单元测试+集成测试

#### T06: VDOT趋势API
- **优先级**: P0
- **依赖**: T02, T03
- **工作量**: 3h
- **描述**: 实现VDOT趋势API端点`/api/webui/vdot/trend`，服务层调用`AnalyticsEngine.get_vdot_trend(days)`，Pydantic Schema定义`VdotTrendResponse`（items列表+days参数），`run_in_threadpool()`包装
- **需求映射**: REQ-D-20
- **验收标准**:
  1. `GET /api/webui/vdot/trend?days=90` 返回VDOT趋势数据
  2. 数据与CLI `analysis vdot` 输出一致
  3. VdotTrendItem包含date/vdot/distance/duration字段
  4. 单元测试

#### T07: 训练负荷API
- **优先级**: P0
- **依赖**: T02, T03
- **工作量**: 3h
- **描述**: 实现训练负荷API端点`/api/webui/training-load`和`/api/webui/training-load/trend`，服务层调用`AnalyticsEngine.get_training_load()`和`get_training_load_trend()`，Pydantic Schema定义`TrainingLoadResponse`和`TrainingLoadTrendResponse`
- **需求映射**: REQ-D-23, REQ-D-24
- **验收标准**:
  1. `GET /api/webui/training-load?days=42` 返回ATL/CTL/TSB数据
  2. `GET /api/webui/training-load/trend?days=42` 返回趋势数据
  3. 数据与CLI `analysis load` 输出一致
  4. 包含fitness_status字段（新鲜/最佳/疲劳/过度训练）
  5. 单元测试

#### T08: 活动列表API
- **优先级**: P0
- **依赖**: T02, T03
- **工作量**: 4h
- **描述**: 实现活动列表API端点`/api/webui/activities`，服务层调用`SessionRepository.get_sessions()`，支持分页（page/size）、时间范围筛选（start_date/end_date）、距离筛选（min_distance），Pydantic Schema定义`ActivitiesResponse`
- **需求映射**: REQ-D-26, REQ-D-27, REQ-D-28
- **验收标准**:
  1. `GET /api/webui/activities?page=1&size=20` 返回分页数据
  2. 支持`start_date`/`end_date`/`min_distance`筛选
  3. 默认每页20条，按时间倒序
  4. 响应包含total/page/size/items
  5. 单元测试

#### T09: 活动详情API
- **优先级**: P0
- **依赖**: T02, T03
- **工作量**: 3h
- **描述**: 实现活动详情API端点`/api/webui/activities/{id}`，id为SHA256哈希（I-02），服务层调用`SessionRepository`+`AnalyticsEngine`获取完整数据，Pydantic Schema定义`ActivityDetailResponse`
- **需求映射**: REQ-D-29
- **验收标准**:
  1. `GET /api/webui/activities/{sha256}` 返回活动详情
  2. 包含距离/时长/配速/心率/VDOT/TSS/卡路里
  3. 无效id返回404
  4. 单元测试

#### T10: 身体信号API
- **优先级**: P1
- **依赖**: T02, T03
- **工作量**: 5h
- **描述**: 实现身体信号API端点组：`/api/webui/body-signals`（汇总）、`/api/webui/body-signals/hrv`、`/api/webui/body-signals/fatigue`、`/api/webui/body-signals/recovery`，服务层分别调用`BodySignalEngine`/`HRVAnalyzer`/`FatigueAssessor`/`RecoveryMonitor`
- **需求映射**: REQ-D-32, REQ-D-33, REQ-D-34
- **验收标准**:
  1. 4个端点均返回正确数据
  2. HRV数据与CLI `analysis hrv` 输出一致
  3. 疲劳数据与CLI `analysis fatigue` 输出一致
  4. 恢复数据与CLI `analysis recovery` 输出一致
  5. 单元测试

---

### 3.3 前端基础层

#### T11: 前端项目骨架
- **优先级**: P0
- **依赖**: 无
- **工作量**: 3h
- **描述**: 创建webui/目录，初始化React+TypeScript+Vite项目，配置TailwindCSS、Recharts、React Router、axios依赖，配置vite.config.ts（含proxy转发/api到8766），配置tsconfig.json
- **验收标准**:
  1. `cd webui && npm run dev` 启动成功
  2. `npm run build` 构建成功，输出到dist/
  3. Vite proxy配置正确，`/api`请求转发到8766
  4. TypeScript编译无错误

#### T12: 布局与导航
- **优先级**: P0
- **依赖**: T11
- **工作量**: 4h
- **描述**: 实现AppLayout（左侧导航+右侧内容区）、Sidebar（仪表盘/VDOT/负荷/活动/身体信号导航项）、Header（品牌名+Agent对话链接），配置React Router路由（6个页面路由）
- **需求映射**: REQ-D-19（快捷入口）
- **验收标准**:
  1. 左侧导航栏显示5个导航项
  2. 点击导航项切换页面路由
  3. Header显示"Agent对话→"链接指向8765
  4. 响应式布局，移动端侧边栏可折叠
  5. 路由配置：/, /vdot, /training-load, /activities, /activities/:id, /body-signals

#### T19: 共享组件
- **优先级**: P0
- **依赖**: T11
- **工作量**: 4h
- **描述**: 实现共享组件库：StatCard（统计卡片：距离/时长/配速/心率）、StatusCard（状态卡片：疲劳/恢复）、AlertCard（预警卡片）、LoadingSpinner、Pagination，以及API客户端（axios实例+认证Header自动附加）
- **需求映射**: REQ-D-35（部分）
- **验收标准**:
  1. StatCard正确展示数值和单位
  2. Pagination组件支持page/size/total
  3. API客户端自动从localStorage读取token附加到Header
  4. LoadingSpinner在数据加载时显示

#### T20: 时间范围Hook
- **优先级**: P0
- **依赖**: T11
- **工作量**: 2h
- **描述**: 实现`useTimeRange` Hook管理全局时间范围状态（7/30/90/365天），实现`TimeRangeSelector`组件，所有图表共用
- **需求映射**: REQ-D-35
- **验收标准**:
  1. TimeRangeSelector显示7天/30天/90天/365天选项
  2. 切换时间范围触发关联图表重新加载
  3. 默认值根据页面不同（Dashboard=7天，VDOT=90天，负荷=42天）

---

### 3.4 前端页面层

#### T13: Dashboard页面
- **优先级**: P0
- **依赖**: T12, T19, T20
- **工作量**: 4h
- **描述**: 实现DashboardPage，包含今日概览卡片（距离/时长/配速/心率，无跑步日显示休息状态）、本周统计卡片（总距离/总时长/总TSS/跑步次数）、快捷入口（导入数据/查看报告/调整计划）
- **需求映射**: REQ-D-17, REQ-D-18, REQ-D-19
- **验收标准**:
  1. 今日有跑步时展示4个StatCard
  2. 今日无跑步时显示"休息日"状态
  3. 本周统计与CLI `data stats` 数据一致
  4. 快捷入口可点击跳转

#### T14: VDOT趋势页面
- **优先级**: P0
- **依赖**: T12, T19, T20
- **工作量**: 5h
- **描述**: 实现VdotPage，包含VdotTrendChart（Recharts折线图展示VDOT趋势），支持预测区间渲染（REQ-D-21，P1），关键节点标注（REQ-D-22，P2），时间范围筛选
- **需求映射**: REQ-D-20, REQ-D-21, REQ-D-22
- **验收标准**:
  1. 折线图正确展示VDOT趋势
  2. 数据与CLI `analysis vdot` 输出一致
  3. 时间范围切换正常工作
  4. P1: 预测区间渲染（半透明区域）
  5. P2: 关键节点标注（ReferenceDot）

#### T15: 训练负荷页面
- **优先级**: P0
- **依赖**: T12, T19, T20
- **工作量**: 5h
- **描述**: 实现TrainingLoadPage，包含TrainingLoadChart（ATL/CTL/TSB堆叠面积图）、疲劳状态指示（基于TSB值）、趋势预警（TSB<-30时AlertCard显示过度训练预警）
- **需求映射**: REQ-D-23, REQ-D-24, REQ-D-25
- **验收标准**:
  1. 堆叠面积图正确展示ATL/CTL/TSB
  2. 数据与CLI `analysis load` 输出一致
  3. TSB值映射到疲劳状态（新鲜>15/最佳0~15/疲劳-30~0/过度训练<-30）
  4. TSB<-30时显示预警AlertCard

#### T16: 活动列表页面
- **优先级**: P0
- **依赖**: T12, T19
- **工作量**: 4h
- **描述**: 实现ActivitiesPage，包含活动列表（日期/距离/时长/配速/心率）、筛选器（时间范围/距离）、分页加载（默认20条/页）
- **需求映射**: REQ-D-26, REQ-D-27, REQ-D-28
- **验收标准**:
  1. 列表正确展示跑步记录
  2. 筛选器功能正常
  3. 分页组件正常工作
  4. 点击记录跳转到活动详情页

#### T17: 活动详情页面
- **优先级**: P1
- **依赖**: T16
- **工作量**: 5h
- **描述**: 实现ActivityDetailPage，包含单次跑步完整数据（距离/时长/配速/心率/VDOT/TSS/卡路里）、配速曲线（PaceChart）、心率曲线（HeartRateChart）、数据标签（P2）
- **需求映射**: REQ-D-29, REQ-D-30, REQ-D-31
- **验收标准**:
  1. 完整数据展示正确
  2. 配速/心率曲线正确渲染
  3. 返回按钮可回到活动列表
  4. P2: 数据标签展示训练类型/强度

#### T18: 身体信号页面
- **优先级**: P1
- **依赖**: T12, T19, T20
- **工作量**: 4h
- **描述**: 实现BodySignalsPage，包含HRV状态卡片（RMSSD/SDNN/静息心率趋势）、疲劳度卡片（疲劳评分+恢复状态）、恢复状态卡片（恢复状态+建议）
- **需求映射**: REQ-D-32, REQ-D-33, REQ-D-34
- **验收标准**:
  1. HRV数据与CLI `analysis hrv` 输出一致
  2. 疲劳度与CLI `analysis fatigue` 输出一致
  3. 恢复状态与CLI `analysis recovery` 输出一致
  4. 时间范围筛选正常工作

---

### 3.5 集成与验证层

#### T21: Gateway集成启动
- **优先级**: P0
- **依赖**: T05~T10, T13~T18
- **工作量**: 4h
- **描述**: 修改gateway.py启动流程，使用`uvicorn.Server.serve()`启动FastAPI服务（C-01），与agent.run()+channels.start_all()并行运行。新增`--webui-port`选项。前端SPA部署在FastAPI(8766)同源（C-02）。修改pyproject.toml wheel targets包含webui/dist/
- **验收标准**:
  1. `gateway start --webui` 同时启动nanobot-ai(8765)+FastAPI(8766)
  2. 使用`uvicorn.Server.serve()`而非`uvicorn.run()`（C-01）
  3. FastAPI服务与agent.run()共享同一事件循环
  4. 前端SPA通过FastAPI StaticFiles在8766端口访问（C-02）
  5. `--webui-port`可自定义端口

#### T22: 端到端验证
- **优先级**: P0
- **依赖**: T21
- **工作量**: 4h
- **描述**: 端到端验证所有API端点和前端页面，验证数据一致性（REQ-D-36），验证非功能需求（NFR-D-17~23），验证认证机制
- **验收标准**:
  1. 所有10个API端点返回正确数据
  2. 图表数据与CLI命令输出数值一致（误差<0.1%）
  3. 认证机制正常工作
  4. 仪表盘首屏<2s
  5. API响应<500ms(P95)

---

## 4. 迭代计划

### 迭代1: 后端基础 + 前端骨架（~16h）

| 任务 | 工作量 | 并行度 |
|------|--------|--------|
| T01 项目骨架与依赖 | 2h | - |
| T02 FastAPI应用工厂 | 4h | T01后 |
| T04 WebUI配置管理 | 3h | 与T02并行 |
| T03 认证中间件 | 4h | T02后 |
| T11 前端项目骨架 | 3h | 与T01并行 |

### 迭代2: 后端API层（~22h）

| 任务 | 工作量 | 并行度 |
|------|--------|--------|
| T05 Dashboard API | 4h | T03后 |
| T06 VDOT趋势API | 3h | 与T05并行 |
| T07 训练负荷API | 3h | 与T05并行 |
| T08 活动列表API | 4h | 与T05并行 |
| T09 活动详情API | 3h | 与T05并行 |
| T10 身体信号API | 5h | 与T05并行 |

### 迭代3: 前端页面层（~28h）

| 任务 | 工作量 | 并行度 |
|------|--------|--------|
| T12 布局与导航 | 4h | T11后 |
| T19 共享组件 | 4h | 与T12并行 |
| T20 时间范围Hook | 2h | 与T12并行 |
| T13 Dashboard页面 | 4h | T12+T19+T20后 |
| T14 VDOT趋势页面 | 5h | 与T13并行 |
| T15 训练负荷页面 | 5h | 与T13并行 |
| T16 活动列表页面 | 4h | 与T13并行 |

### 迭代4: 页面完善 + 集成验证（~22h）

| 任务 | 工作量 | 并行度 |
|------|--------|--------|
| T17 活动详情页面 | 5h | - |
| T18 身体信号页面 | 4h | 与T17并行 |
| T21 Gateway集成启动 | 4h | T17+T18后 |
| T22 端到端验证 | 4h | T21后 |

---

## 5. 风险与缓解

| 风险 | 等级 | 缓解措施 |
|------|------|----------|
| `uvicorn.run()`与现有事件循环冲突 | 高 | C-01：强制使用`uvicorn.Server.serve()`，T21中重点验证 |
| 前端构建产物未包含在release包 | 中 | T21中修改pyproject.toml wheel targets |
| 核心模块方法签名与API Schema不匹配 | 中 | T05~T10中逐一验证数据类→Pydantic转换 |
| Recharts图表渲染性能 | 低 | 轻量声明式API，单用户场景数据量有限 |

---

## 6. 条件项追踪

| 编号 | 条件项 | 负责任务 | 状态 |
|------|--------|----------|------|
| C-01 | FastAPI启动必须使用`uvicorn.Server.serve()` | T21 | 待实施 |
| C-02 | 前端SPA必须部署在FastAPI(8766) | T21 | 待实施 |

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-06-04 | 初始版本：22项任务，4个迭代，~88小时 |
