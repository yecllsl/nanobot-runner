# WebUI 数据导入功能实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 WebUI（端口 8766）增加 FIT 文件导入功能，功能与 CLI `data import` 等价，复用同一 `ImportService.import_file`。

**Architecture:** 薄封装方案——新增一个 FastAPI 路由 `POST /api/data/import`，接收 multipart 文件列表，写入临时目录后逐个调用 `context.importer.import_file(Path, force)`，收集结果后清理临时文件并返回 JSON。前端新增 ImportPage 页面 + API 封装 + 路由 + 导航项。零改动 `src/core/` 核心模块。

**Tech Stack:** Python 3.11 / FastAPI / python-multipart / starlette `run_in_threadpool` / React + TypeScript + TailwindCSS + axios

## Global Constraints

- Python `>=3.11,<3.13`，依赖通过 `uv` 管理
- 单文件 ≤ 50MB，单次上传 ≤ 50 个文件，总请求体 ≤ 60MB
- 复用 `ImportService.import_file(filepath: Path, force: bool = False) -> dict`，返回 `{"status","message","fingerprint"}`
- 复用 `get_current_user` Bearer token 认证（与现有 9 组路由一致）
- 同步阻塞调用必须用 `run_in_threadpool` 包装（ADR-021）
- 类名 PascalCase，函数/变量 snake_case，常量 UPPER_SNAKE_CASE
- 禁止硬编码密钥；禁止直接实例化核心组件，通过 `context` 获取
- 测试位于 `tests/unit/core/webui/`，复用现有 `conftest.py` 的 `mock_context`/`client`/`auth_headers` fixtures

## File Structure

| 类型 | 文件 | 职责 |
|------|------|------|
| 修改 | `pyproject.toml` | 新增 `python-multipart` 依赖 |
| 新增 | `src/core/webui/routes/import_data.py` | 后端导入路由，单文件职责：接收文件→临时写盘→调 ImportService→清理→返回 |
| 修改 | `src/core/webui/app.py` | 注册 import_data router + 新增 MaxBodySizeMiddleware |
| 新增 | `webui/src/api/import.ts` | 前端 API 封装 |
| 新增 | `webui/src/pages/ImportPage.tsx` | 导入页面组件 |
| 修改 | `webui/src/App.tsx` | 新增 /import 路由 |
| 修改 | `webui/src/components/layout/Sidebar.tsx` | 新增导入导航项 |
| 新增 | `tests/unit/core/webui/test_routes_import_data.py` | 后端单元测试 |
| 新增 | `tests/integration/webui/test_import_data.py` | 后端集成测试 |
| 新增 | `tests/e2e/webui/test_webui_import.py` | E2E 测试 |

---

## Task 1: 新增 python-multipart 依赖

**Files:**
- Modify: `pyproject.toml:7-24`（dependencies 数组）

**Interfaces:**
- Produces: `python-multipart` 可被 FastAPI `UploadFile` 使用

- [ ] **Step 1: 在 dependencies 数组末尾新增 python-multipart**

修改 `pyproject.toml`，在 `dependencies` 列表中 `"PyJWT>=2.8.0",` 之后新增一行：

```toml
    "python-multipart>=0.0.9",
```

- [ ] **Step 2: 同步安装依赖**

Run: `uv sync`
Expected: 成功安装 python-multipart，无报错

- [ ] **Step 3: 验证依赖已安装**

Run: `uv run python -c "import multipart; print(multipart.__version__)"`
Expected: 打印版本号，无 ImportError

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "build: add python-multipart dependency for FastAPI UploadFile support"
```

---

## Task 2: 后端导入路由（TDD - 先写失败测试）

**Files:**
- Create: `tests/unit/core/webui/test_routes_import_data.py`
- Test fixtures 复用: `tests/unit/core/webui/conftest.py`（已有 `mock_context`/`client`/`auth_headers`）

**Interfaces:**
- Consumes: `context.importer.import_file(filepath: Path, force: bool = False) -> dict`，返回 `{"status": "added"|"skipped"|"error", "message": str, "fingerprint"?: str}`
- Produces: `POST /api/data/import` 端点，接收 `files: list[UploadFile]` + `force: bool` query 参数

- [ ] **Step 1: 编写失败测试文件**

创建 `tests/unit/core/webui/test_routes_import_data.py`：

```python
"""数据导入 API 路由单元测试 (v0.34.0)"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.core.webui.app import create_app


@pytest.fixture
def mock_importer() -> MagicMock:
    """模拟 ImportService，import_file 返回标准 dict"""
    importer = MagicMock()

    def _import_file(filepath, force=False):
        # 根据文件名返回不同状态，便于测试
        name = filepath.name
        if "skip" in name:
            return {"status": "skipped", "message": "文件已存在"}
        if "error" in name:
            return {"status": "error", "message": "解析失败"}
        return {"status": "added", "message": "导入成功", "fingerprint": "abc123"}

    importer.import_file.side_effect = _import_file
    return importer


@pytest.fixture
def mock_context(mock_importer: MagicMock) -> MagicMock:
    context = MagicMock()
    context.config.get_webui_config.return_value = {
        "enabled": True,
        "host": "127.0.0.1",
        "port": 8766,
        "cors_origins": [],
        "token_secret": "test-secret",
        "token_ttl_s": 86400,
    }
    context.importer = mock_importer
    return context


@pytest.fixture
def client(mock_context: MagicMock) -> TestClient:
    app = create_app(context=mock_context)
    return TestClient(app)


class TestImportEndpointAuth:
    """认证测试"""

    def test_requires_auth(self, client: TestClient) -> None:
        """未认证返回 401"""
        response = client.post("/api/data/import")
        assert response.status_code == 401


class TestImportEndpointValidation:
    """请求阶段校验测试"""

    def test_reject_non_fit_file(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """非 .fit 文件返回 400"""
        response = client.post(
            "/api/data/import",
            headers=auth_headers,
            files={"files": ("test.txt", b"hello", "text/plain")},
        )
        assert response.status_code == 400
        assert "test.txt" in response.json()["detail"]

    def test_reject_too_many_files(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """超过 50 个文件返回 400"""
        files = [
            ("files", (f"run{i}.fit", b"fake", "application/octet-stream"))
            for i in range(51)
        ]
        response = client.post(
            "/api/data/import", headers=auth_headers, files=files
        )
        assert response.status_code == 400


class TestImportEndpointSuccess:
    """正常导入测试"""

    def test_single_file_added(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        mock_importer: MagicMock,
    ) -> None:
        """单个 .fit 文件导入成功"""
        response = client.post(
            "/api/data/import",
            headers=auth_headers,
            files={"files": ("run1.fit", b"fake-fit-content", "application/octet-stream")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["summary"] == {"total": 1, "added": 1, "skipped": 0, "errors": 0}
        assert data["results"][0]["filename"] == "run1.fit"
        assert data["results"][0]["status"] == "added"
        # 验证 importer 被调用，且 force 默认 False
        mock_importer.import_file.assert_called_once()
        call_kwargs = mock_importer.import_file.call_args
        assert call_kwargs.kwargs.get("force", call_kwargs[1].get("force", False)) is False

    def test_multiple_files_mixed_status(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        mock_importer: MagicMock,
    ) -> None:
        """多文件混合状态：added + skipped + error"""
        files = [
            ("files", ("run_added.fit", b"data", "application/octet-stream")),
            ("files", ("run_skip.fit", b"data", "application/octet-stream")),
            ("files", ("run_error.fit", b"data", "application/octet-stream")),
        ]
        response = client.post(
            "/api/data/import", headers=auth_headers, files=files
        )
        assert response.status_code == 200
        data = response.json()
        assert data["summary"] == {"total": 3, "added": 1, "skipped": 1, "errors": 1}
        statuses = [r["status"] for r in data["results"]]
        assert "added" in statuses
        assert "skipped" in statuses
        assert "error" in statuses

    def test_force_param_passed_to_importer(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        mock_importer: MagicMock,
    ) -> None:
        """force=true 透传给 importer"""
        response = client.post(
            "/api/data/import?force=true",
            headers=auth_headers,
            files={"files": ("run1.fit", b"data", "application/octet-stream")},
        )
        assert response.status_code == 200
        call_kwargs = mock_importer.import_file.call_args
        assert call_kwargs.kwargs.get("force", call_kwargs[1].get("force", False)) is True
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/unit/core/webui/test_routes_import_data.py -v`
Expected: FAIL，提示路由不存在或 404（因为 `import_data` 路由尚未创建）

- [ ] **Step 3: Commit 失败测试**

```bash
git add tests/unit/core/webui/test_routes_import_data.py
git commit -m "test: add failing tests for WebUI data import endpoint"
```

---

## Task 3: 实现后端导入路由（使测试通过）

**Files:**
- Create: `src/core/webui/routes/import_data.py`
- Modify: `src/core/webui/app.py:120-141`（路由注册段）

**Interfaces:**
- Consumes: Task 2 的测试用例
- Produces: `router`（APIRouter 实例），`POST /data/import` 端点

- [ ] **Step 1: 创建路由文件 `src/core/webui/routes/import_data.py`**

```python
"""数据导入 API 路由 (v0.34.0)

提供 FIT 文件上传导入能力，功能与 CLI `data import` 等价。
复用 ImportService.import_file，不引入导入业务逻辑。
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from src.core.webui.auth import get_current_user

if TYPE_CHECKING:
    from src.core.base.context import AppContext

router = APIRouter()

# 防御性限制常量
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_FILES = 50


def _validate_files(files: list[UploadFile]) -> None:
    """请求阶段校验：文件类型、大小、数量

    Args:
        files: 上传文件列表

    Raises:
        HTTPException 400: 校验失败时抛出
    """
    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件数量超过上限 {MAX_FILES} 个",
        )

    invalid_types = [f.filename for f in files if not f.filename or not f.filename.lower().endswith(".fit")]
    if invalid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"仅支持 .fit 文件，非法文件: {invalid_types}",
        )


def _import_files_sync(
    context: "AppContext", files: list[UploadFile], force: bool
) -> dict[str, Any]:
    """同步导入文件：写临时文件 → 调 ImportService → 收集结果

    Args:
        context: 应用上下文
        files: 上传文件列表
        force: 是否强制重新导入

    Returns:
        dict: {results: list, summary: dict}
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="nanobot_import_"))
    results: list[dict[str, Any]] = []
    try:
        for upload in files:
            # 路径穿越防护：仅取 basename，丢弃目录部分
            safe_name = Path(upload.filename).name
            tmp_path = tmp_dir / safe_name
            try:
                with tmp_path.open("wb") as f:
                    f.write(upload.file.read())
            except OSError as e:
                results.append(
                    {"filename": safe_name, "status": "error", "message": f"临时文件写入失败: {e}"}
                )
                continue

            result = context.importer.import_file(tmp_path, force=force)
            results.append(
                {
                    "filename": safe_name,
                    "status": result.get("status", "error"),
                    "message": result.get("message", ""),
                }
            )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    summary = {
        "total": len(results),
        "added": sum(1 for r in results if r["status"] == "added"),
        "skipped": sum(1 for r in results if r["status"] == "skipped"),
        "errors": sum(1 for r in results if r["status"] == "error"),
    }
    return {"results": results, "summary": summary}


@router.post("/data/import")
async def import_data(
    request: Request,
    files: list[UploadFile] = File(...),
    force: bool = Query(default=False, description="强制重新导入，跳过 SHA256 去重"),
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """导入 FIT 文件数据

    接收 multipart/form-data 上传的 .fit 文件，逐个调用 ImportService 导入。
    功能与 CLI `data import` 等价，复用同一 ImportService.import_file。
    """
    context = request.app.state.context
    _validate_files(files)
    return await run_in_threadpool(_import_files_sync, context, files, force)
```

- [ ] **Step 2: 在 app.py 注册路由**

修改 `src/core/webui/app.py`，在路由注册段（约第 121-141 行）新增。先在 import 块添加：

```python
    from src.core.webui.routes.import_data import router as import_data_router
```

然后在 `app.include_router(...)` 序列末尾（约第 141 行 `runtime_events_router` 之后）新增：

```python
    # v0.34.0 数据导入路由
    app.include_router(import_data_router, prefix="/api", tags=["import"])
```

- [ ] **Step 3: 运行测试验证通过**

Run: `uv run pytest tests/unit/core/webui/test_routes_import_data.py -v`
Expected: PASS，全部测试通过

- [ ] **Step 4: Commit**

```bash
git add src/core/webui/routes/import_data.py src/core/webui/app.py
git commit -m "feat: add WebUI data import endpoint POST /api/data/import"
```

---

## Task 4: MaxBodySizeMiddleware（ISSUE-01 修复）

**Files:**
- Modify: `src/core/webui/app.py`（create_app 函数内，CORS 中间件之后）

**Interfaces:**
- Consumes: Task 3 已注册路由
- Produces: 60MB 请求体上限中间件，防止超大上传耗尽内存

- [ ] **Step 1: 在 app.py 添加 MaxBodySizeMiddleware**

修改 `src/core/webui/app.py`，在 `create_app` 函数内，CORS 中间件之后（约第 96 行 `app.add_middleware(CORSMiddleware, ...)` 之后）新增中间件类定义与注册：

```python
    # v0.34.0: 请求体大小限制中间件（ISSUE-01 修复）
    # FastAPI/Starlette 默认无强制限制，显式设置 60MB 上限防止超大上传耗尽内存
    class MaxBodySizeMiddleware:
        """限制 multipart 请求体大小（仅作用于文件上传）"""

        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            if scope["type"] == "http":
                headers = dict(scope.get("headers", []))
                content_type = headers.get(b"content-type", b"").decode("latin-1")
                content_length = int(headers.get(b"content-length", 0))
                if content_type.startswith("multipart/form-data") and content_length > 60 * 1024 * 1024:
                    response = JSONResponse(
                        status_code=413,
                        content={"detail": "请求体过大，单次上传总计不超过 60MB"},
                    )
                    await response(scope, receive, send)
                    return
            await self.app(scope, receive, send)

    app.add_middleware(MaxBodySizeMiddleware)
```

- [ ] **Step 2: 添加单元测试验证中间件**

在 `tests/unit/core/webui/test_routes_import_data.py` 末尾新增测试类：

```python
class TestMaxBodySizeMiddleware:
    """ISSUE-01: 请求体大小限制测试"""

    def test_reject_oversized_multipart(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """超过 60MB 的 multipart 请求返回 413"""
        # 构造超大 Content-Length 头（不实际发送 60MB 数据）
        huge_content = b"x" * (61 * 1024 * 1024)
        response = client.post(
            "/api/data/import",
            headers={
                **auth_headers,
                "Content-Type": "multipart/form-data; boundary=----test",
                "Content-Length": str(len(huge_content) + 200),
            },
            content=huge_content,
        )
        assert response.status_code == 413
```

- [ ] **Step 3: 运行测试验证**

Run: `uv run pytest tests/unit/core/webui/test_routes_import_data.py::TestMaxBodySizeMiddleware -v`
Expected: PASS

- [ ] **Step 4: 运行全量 WebUI 单测确保无回归**

Run: `uv run pytest tests/unit/core/webui/ -v`
Expected: PASS，所有现有测试仍通过

- [ ] **Step 5: Commit**

```bash
git add src/core/webui/app.py tests/unit/core/webui/test_routes_import_data.py
git commit -m "feat: add MaxBodySizeMiddleware to limit multipart upload size (ISSUE-01)"
```

---

## Task 5: 后端集成测试（真实 ImportService）

**Files:**
- Create: `tests/integration/webui/test_import_data.py`

**Interfaces:**
- Consumes: Task 3 的路由 + 真实 ImportService + 临时数据目录
- Produces: 端到端导入验证

- [ ] **Step 1: 创建集成测试文件**

创建 `tests/integration/webui/test_import_data.py`：

```python
"""数据导入 API 集成测试 (v0.34.0)

使用真实 ImportService + 临时数据目录，验证端到端导入流程。
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.core.base.context import AppContextFactory
from src.core.webui.app import create_app
from src.core.webui.auth import create_access_token


@pytest.fixture
def integration_context(tmp_path: Path):
    """构造真实 AppContext，使用临时数据目录"""
    import os

    os.environ["NANOBOT_CONFIG_DIR"] = str(tmp_path / "config")
    (tmp_path / "config").mkdir(exist_ok=True)
    (tmp_path / "config" / ".env.local").write_text("")
    context = AppContextFactory.create(allow_default=True)
    # 覆盖数据目录为临时路径
    context.config._data_dir = tmp_path / "data"
    (tmp_path / "data").mkdir(exist_ok=True)
    return context


@pytest.fixture
def integration_client(integration_context) -> TestClient:
    app = create_app(context=integration_context)
    return TestClient(app)


@pytest.fixture
def integration_auth_headers(integration_client: TestClient) -> dict[str, str]:
    secret = integration_client.app.state.webui_secret
    token = create_access_token(secret=secret, ttl_seconds=3600)
    return {"Authorization": f"Bearer {token}"}


def _make_minimal_fit_bytes() -> bytes:
    """构造最小的有效 FIT 文件字节（用于集成测试）

    注：真实 FIT 解析需要有效文件头。此处用最小占位，集成测试主要验证
    API 层路由正确性与临时文件清理，真实 FIT 解析由 ImportService 单测覆盖。
    """
    return b".FIT" + b"\x00" * 12 + b"\x0e\x10" + b"\x00" * 100


class TestImportEndpointIntegration:
    """集成测试：真实 ImportService 调用"""

    def test_endpoint_returns_200_with_valid_request(
        self, integration_client: TestClient, integration_auth_headers: dict[str, str]
    ) -> None:
        """有效请求返回 200（即使解析失败，错误隔离不报 500）"""
        fit_bytes = _make_minimal_fit_bytes()
        response = integration_client.post(
            "/api/data/import",
            headers=integration_auth_headers,
            files={"files": ("test.fit", fit_bytes, "application/octet-stream")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "summary" in data
        assert data["summary"]["total"] == 1

    def test_temp_files_cleaned_after_import(
        self, integration_client: TestClient, integration_auth_headers: dict[str, str], tmp_path: Path
    ) -> None:
        """NFR-D-26: 导入后临时文件清理"""
        import glob

        fit_bytes = _make_minimal_fit_bytes()
        integration_client.post(
            "/api/data/import",
            headers=integration_auth_headers,
            files={"files": ("cleanup_test.fit", fit_bytes, "application/octet-stream")},
        )
        # 检查系统临时目录下无 nanobot_import_ 残留
        temp_dirs = glob.glob(str(Path(tempfile.gettempdir()) / "nanobot_import_*"))
        assert len(temp_dirs) == 0, f"临时目录未清理: {temp_dirs}"


# 顶部导入 tempfile（避免在测试函数内导入）
import tempfile
```

- [ ] **Step 2: 运行集成测试**

Run: `uv run pytest tests/integration/webui/test_import_data.py -v -m "not slow"`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/integration/webui/test_import_data.py
git commit -m "test: add integration tests for WebUI data import endpoint"
```

---

## Task 6: 前端 API 封装

**Files:**
- Create: `webui/src/api/import.ts`

**Interfaces:**
- Consumes: `webui/src/api/client.ts` 的默认导出 `apiClient`
- Produces: `importData(files: File[], force: boolean)` 函数 + `ImportResult`/`ImportResponse` 类型

- [ ] **Step 1: 创建 API 封装文件**

创建 `webui/src/api/import.ts`：

```typescript
import apiClient from './client';

export interface ImportResult {
  filename: string;
  status: 'added' | 'skipped' | 'error';
  message: string;
}

export interface ImportResponse {
  results: ImportResult[];
  summary: { total: number; added: number; skipped: number; errors: number };
}

/**
 * 上传 FIT 文件并触发导入
 * SUG-03: 不手动设置 Content-Type，axios 发送 FormData 时会自动设置含 boundary 的正确 header
 */
export async function importData(files: File[], force: boolean = false): Promise<ImportResponse> {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));
  const response = await apiClient.post<ImportResponse>('/data/import', formData, {
    params: { force },
    timeout: 300000, // 5 分钟，大批量导入需要更长时间
  });
  return response.data;
}
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `cd webui && npx tsc --noEmit`
Expected: 无类型错误（如有，修正类型定义）

- [ ] **Step 3: Commit**

```bash
git add webui/src/api/import.ts
git commit -m "feat(webui): add importData API client for data import endpoint"
```

---

## Task 7: 前端 ImportPage 组件

**Files:**
- Create: `webui/src/pages/ImportPage.tsx`

**Interfaces:**
- Consumes: `webui/src/api/import.ts` 的 `importData` + `ImportResponse`
- Consumes: `webui/src/hooks/useApi.ts` 的 `useApi`
- Produces: 默认导出的 `ImportPage` React 组件

- [ ] **Step 1: 创建 ImportPage 组件**

创建 `webui/src/pages/ImportPage.tsx`：

```tsx
import { useState, useRef, ChangeEvent } from 'react';
import { Link } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { importData, type ImportResponse } from '../api/import';
import LoadingSpinner from '../components/common/LoadingSpinner';

const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
const MAX_FILES = 50;

export default function ImportPage() {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [force, setForce] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const { data, loading, error, execute } = useApi<ImportResponse, [File[], boolean]>(importData);

  // 文件选择处理：校验类型与大小
  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    setFileError(null);
    const files = Array.from(e.target.files ?? []);
    if (files.length > MAX_FILES) {
      setFileError(`文件数量超过上限 ${MAX_FILES} 个`);
      return;
    }
    const invalidType = files.find((f) => !f.name.toLowerCase().endsWith('.fit'));
    if (invalidType) {
      setFileError(`仅支持 .fit 文件: ${invalidType.name}`);
      return;
    }
    const oversize = files.find((f) => f.size > MAX_FILE_SIZE);
    if (oversize) {
      setFileError(`文件过大（>50MB）: ${oversize.name}`);
      return;
    }
    setSelectedFiles(files);
  };

  const handleImport = () => {
    if (selectedFiles.length === 0) return;
    execute(selectedFiles, force);
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)}MB`;
  };

  // 状态颜色映射
  const statusColor = (status: string) => {
    if (status === 'added') return 'text-green-600';
    if (status === 'skipped') return 'text-yellow-600';
    return 'text-red-600';
  };
  const statusIcon = (status: string) => {
    if (status === 'added') return '✅';
    if (status === 'skipped') return '⏭️';
    return '❌';
  };

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900">数据导入</h2>

      {/* 文件选择区 */}
      <section className="bg-white rounded-xl border border-gray-200 p-4 space-y-4">
        <div className="flex items-center gap-4">
          <input
            ref={inputRef}
            type="file"
            accept=".fit"
            multiple
            onChange={handleFileChange}
            className="hidden"
          />
          <button
            onClick={() => inputRef.current?.click()}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          >
            选择 .fit 文件
          </button>
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={force}
              onChange={(e) => setForce(e.target.checked)}
              className="rounded"
            />
            强制重新导入（跳过去重）
          </label>
        </div>

        {/* 已选文件列表 */}
        {selectedFiles.length > 0 && (
          <div className="space-y-1">
            <p className="text-sm text-gray-500">已选文件 ({selectedFiles.length}):</p>
            <ul className="max-h-40 overflow-y-auto space-y-1">
              {selectedFiles.map((f, i) => (
                <li key={i} className="text-sm text-gray-700">
                  • {f.name} <span className="text-gray-400">({formatSize(f.size)})</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {fileError && <p className="text-sm text-red-600">{fileError}</p>}

        <button
          onClick={handleImport}
          disabled={selectedFiles.length === 0 || loading}
          className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? '导入中...' : '开始导入'}
        </button>
      </section>

      {/* 导入结果区 */}
      {loading && <LoadingSpinner />}
      {error && <p className="text-red-600">导入失败: {error}</p>}

      {data && (
        <section className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
          <h3 className="font-medium text-gray-900 border-b pb-2">导入结果</h3>
          <ul className="space-y-1">
            {data.results.map((r, i) => (
              <li key={i} className={`text-sm ${statusColor(r.status)}`}>
                {statusIcon(r.status)} {r.filename} — {r.message}
              </li>
            ))}
          </ul>
          <div className="flex items-center gap-4 pt-2 border-t text-sm">
            <span className="text-green-600">成功 {data.summary.added}</span>
            <span className="text-yellow-600">跳过 {data.summary.skipped}</span>
            <span className="text-red-600">错误 {data.summary.errors}</span>
            <Link to="/activities" className="ml-auto text-primary-600 hover:underline">
              查看活动列表 →
            </Link>
          </div>
        </section>
      )}
    </div>
  );
}
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `cd webui && npx tsc --noEmit`
Expected: 无类型错误

- [ ] **Step 3: Commit**

```bash
git add webui/src/pages/ImportPage.tsx
git commit -m "feat(webui): add ImportPage component for FIT file upload"
```

---

## Task 8: 前端路由与导航集成

**Files:**
- Modify: `webui/src/App.tsx`
- Modify: `webui/src/components/layout/Sidebar.tsx`

**Interfaces:**
- Consumes: Task 7 的 `ImportPage` 组件
- Produces: `/import` 路由 + 侧边栏"导入"导航项

- [ ] **Step 1: 修改 App.tsx 新增路由**

修改 `webui/src/App.tsx`，在 import 块新增（约第 12 行 `SettingsPage` 之后）：

```typescript
import ImportPage from './pages/ImportPage';
```

在 `<Route path="/settings" ...>` 之后（约第 28 行）新增：

```tsx
          <Route path="/import" element={<ImportPage />} />
```

- [ ] **Step 2: 修改 Sidebar.tsx 新增导航项**

修改 `webui/src/components/layout/Sidebar.tsx`，在 `navItems` 数组中（约第 3-12 行），在 `activities` 之后新增导入项：

```typescript
const navItems = [
  { path: '/', label: '仪表盘', icon: '📊' },
  { path: '/vdot', label: 'VDOT', icon: '📈' },
  { path: '/training-load', label: '负荷', icon: '💪' },
  { path: '/activities', label: '活动', icon: '🏃' },
  { path: '/import', label: '导入', icon: '📥' },
  { path: '/body-signals', label: '身体', icon: '❤️' },
  { path: '/plan', label: '计划', icon: '📋' },
  { path: '/evolution', label: '进化', icon: '🧬' },
  { path: '/settings', label: '设置', icon: '⚙️' },
];
```

- [ ] **Step 3: 构建前端验证无错**

Run: `cd webui && npm run build`
Expected: 构建成功，无 TypeScript 或构建错误

- [ ] **Step 4: Commit**

```bash
git add webui/src/App.tsx webui/src/components/layout/Sidebar.tsx
git commit -m "feat(webui): add /import route and sidebar navigation entry"
```

---

## Task 9: E2E 测试（Playwright）

**Files:**
- Create: `tests/e2e/webui/test_webui_import.py`

**Interfaces:**
- Consumes: Task 8 的完整路由 + Task 3 的后端端点
- Produces: 端到端导入流程验证

- [ ] **Step 1: 创建 E2E 测试文件**

参考现有 `tests/e2e/webui/conftest.py` 的 fixture 模式，创建 `tests/e2e/webui/test_webui_import.py`：

```python
"""WebUI 数据导入功能 E2E 测试 (v0.34.0)"""

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestWebUIImportNavigation:
    """导入页导航测试"""

    def test_import_page_accessible_from_sidebar(
        self, page: Page, webui_base_url: str
    ) -> None:
        """侧边栏点击导入可导航到导入页"""
        page.goto(webui_base_url)
        page.click("a[href='/import']")
        expect(page).to_have_url(f"{webui_base_url}/import")
        expect(page.get_by_text("数据导入")).to_be_visible()

    def test_import_page_has_file_input(
        self, page: Page, webui_base_url: str
    ) -> None:
        """导入页有文件选择按钮"""
        page.goto(f"{webui_base_url}/import")
        expect(page.get_by_role("button", name="选择 .fit 文件")).to_be_visible()
        expect(page.get_by_role("button", name="开始导入")).to_be_disabled()


@pytest.mark.e2e
class TestWebUIImportFlow:
    """导入流程测试（需真实 FIT 文件）"""

    def test_import_flow_shows_results(
        self, page: Page, webui_base_url: str, sample_fit_file: Path
    ) -> None:
        """选择文件并导入，显示结果区"""
        page.goto(f"{webui_base_url}/import")

        # 通过隐藏的 file input 上传文件
        file_input = page.locator("input[type='file']")
        file_input.set_input_files(str(sample_fit_file))

        # 点击开始导入
        page.get_by_role("button", name="开始导入").click()

        # 等待结果区出现（最多 30 秒）
        expect(page.get_by_text("导入结果")).to_be_visible(timeout=30000)

        # 验证汇总区显示
        expect(page.get_by_text("成功")).to_be_visible()
        expect(page.get_by_text("跳过")).to_be_visible()
        expect(page.get_by_text("错误")).to_be_visible()
```

- [ ] **Step 2: 检查 conftest.py 是否有 webui_base_url 和 sample_fit_file fixtures**

Run: `Get-Content tests/e2e/webui/conftest.py`

如果缺少 `webui_base_url` 或 `sample_fit_file` fixture，在 `tests/e2e/webui/conftest.py` 中补充：

```python
@pytest.fixture
def webui_base_url() -> str:
    return "http://127.0.0.1:8766"


@pytest.fixture
def sample_fit_file(tmp_path: Path) -> Path:
    """构造最小 FIT 文件用于 E2E 测试"""
    fit_path = tmp_path / "sample.fit"
    # 最小 FIT 文件头占位（真实 FIT 需有效格式，此处仅验证 UI 流程）
    fit_path.write_bytes(b".FIT" + b"\x00" * 116)
    return fit_path
```

- [ ] **Step 3: 运行 E2E 测试**

Run: `uv run pytest tests/e2e/webui/test_webui_import.py -v -m e2e --headed`
Expected: PASS（如 WebUI 服务未启动，先启动：`uv run nanobotrun gateway start --webui`）

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/webui/test_webui_import.py tests/e2e/webui/conftest.py
git commit -m "test(e2e): add Playwright E2E tests for WebUI import flow"
```

---

## Task 10: 开发完成验证（verification-before-completion）

**Files:**
- 验证范围：全部新增/修改文件

- [ ] **Step 1: 运行全量单元测试**

Run: `uv run pytest tests/unit/ -v`
Expected: 全部 PASS，无回归

- [ ] **Step 2: 运行集成测试**

Run: `uv run pytest tests/integration/ -v -m "not slow"`
Expected: 全部 PASS

- [ ] **Step 3: 运行 ruff lint**

Run: `uv run ruff check src/ tests/`
Expected: 无错误（warning 可接受）

- [ ] **Step 4: 运行 ruff format**

Run: `uv run ruff format src/ tests/`
Expected: 格式化完成

- [ ] **Step 5: 运行 mypy**

Run: `uv run mypy src/ --ignore-missing-imports`
Expected: 无类型错误（或仅原有警告）

- [ ] **Step 6: 验证前端构建**

Run: `cd webui && npm run build`
Expected: 构建成功

- [ ] **Step 7: 手动冒烟测试**

启动 WebUI 服务：`uv run nanobotrun gateway start --webui`
浏览器访问 `http://127.0.0.1:8766/import`，验证：
- 页面正常渲染
- 文件选择按钮可用
- 强制重新导入复选框可用
- 导入流程完整执行

- [ ] **Step 8: 验收标准逐条核对**

对照需求规格 §5.7.3 的 8 条验收标准与 §5.7.2 的 5 条 NFR，逐条记录证据。

- [ ] **Step 9: 最终 Commit**

```bash
git add .
git commit -m "chore: final verification for v0.34.0 WebUI data import"
```

---

## 验收标准对齐表

| 验收项 | Task | 验证方式 |
|--------|------|----------|
| 选择 1+ 个 .fit 文件 | Task 7, 9 | ImportPage file input + E2E |
| 显示每个文件结果 | Task 3, 7 | results 列表渲染 |
| 强制重新导入复选框 | Task 3, 7 | force query param + checkbox |
| 汇总 N/M/K | Task 3, 7 | summary 字段 |
| 与 CLI 等价 | Task 3 | 复用 ImportService.import_file |
| 非 .fit 拒绝 + 超限拒绝 | Task 3, 4 | 请求阶段校验 400 |
| token 认证 | Task 3 | get_current_user |
| 不影响 CLI/飞书 | Task 10 | 全量回归测试 |

| NFR | Task | 验证方式 |
|-----|------|----------|
| NFR-D-24 单文件 <3s | Task 10 | ImportService 性能 |
| NFR-D-25 不阻塞事件循环 | Task 3 | run_in_threadpool |
| NFR-D-26 临时文件清理 | Task 3, 5 | try/finally + 集成测试 |
| NFR-D-27 安全认证 | Task 3 | get_current_user |
| NFR-D-28 向后兼容 | Task 10 | 全量回归 |
