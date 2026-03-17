# Checklist

## T009: CLI Report 命令完善

- [ ] 添加进度指示器（使用 rich.progress）
- [ ] 优化错误消息，添加恢复建议
- [ ] 添加颜色编码输出
- [ ] 单元测试覆盖率 ≥ 70%

## T010: 错误处理增强

- [ ] 创建自定义异常类（StorageError, ParseError, ConfigError）
- [ ] 在 decorators.py 中添加错误处理装饰器
- [ ] 更新现有代码使用新异常类
- [ ] 单元测试通过

## T011: 日志系统优化

- [ ] 配置 structlog 或标准 logging
- [ ] 添加 JSON 格式日志支持
- [ ] 配置日志级别和输出目标
- [ ] 替换现有 print 语句为 logger

## T012: Polars 查询优化

- [ ] 审查现有查询，识别优化点
- [ ] 将急切执行转换为 LazyFrame
- [ ] 优化聚合查询
- [ ] 添加查询性能测试

## T013: 文档编写

- [ ] 编写 API 参考文档
- [ ] 编写 CLI 用户指南
- [ ] 更新 README.md
- [ ] 编写架构概述文档

## 总体验收

- [ ] 所有单元测试通过 (`uv run pytest tests/unit/ -v`)
- [ ] 总体覆盖率 ≥ 85%
- [ ] 代码质量检查通过 (`uv run black src tests; uv run isort src tests; uv run mypy src`)
- [ ] 文档完整性检查通过
