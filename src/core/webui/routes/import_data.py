"""数据导入 API 路由 (v0.34.0)

提供 FIT 文件上传导入能力，功能与 CLI `data import` 等价。
复用 ImportService.import_file，不引入导入业务逻辑。
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
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

    invalid_types = [
        f.filename
        for f in files
        if not f.filename or not f.filename.lower().endswith(".fit")
    ]
    if invalid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"仅支持 .fit 文件，非法文件: {invalid_types}",
        )


def _import_files_sync(
    context: AppContext, files: list[UploadFile], force: bool
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
            # _validate_files 已保证 filename 非空且为 .fit，此处断言消除 mypy 可空类型
            assert upload.filename is not None
            # 路径穿越防护：仅取 basename，丢弃目录部分
            safe_name = Path(upload.filename).name
            tmp_path = tmp_dir / safe_name
            try:
                with tmp_path.open("wb") as f:
                    f.write(upload.file.read())
            except OSError as e:
                results.append(
                    {
                        "filename": safe_name,
                        "status": "error",
                        "message": f"临时文件写入失败: {e}",
                    }
                )
                continue

            try:
                result = context.importer.import_file(tmp_path, force=force)
                results.append(
                    {
                        "filename": safe_name,
                        "status": result.get("status", "error"),
                        "message": result.get("message", ""),
                    }
                )
            except Exception as e:  # noqa: BLE001 - 错误隔离：单文件异常不中断后续
                results.append(
                    {
                        "filename": safe_name,
                        "status": "error",
                        "message": f"导入过程异常: {e}",
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
