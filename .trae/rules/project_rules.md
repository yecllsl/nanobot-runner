---
alwaysApply: false
description: 开发Rust+ Python，PyO3统一实现绑定项目时使用此规则
---
## 1. 项目架构
分层设计：Rust（crates/，高性能核心）+ Python（python/，上层接口），PyO3（crates/pyo3/src/lib.rs）统一实现绑定。核心目录：src/（Rust模块）、python/（Python代码）、tests/（分rust/python测试）、docs/：（维护文档）；
scripts/：（辅助脚本）、pyproject.toml（maturin配置）。

## 2. 开发环境
Rust：rustup（≥1.70），启用rustfmt/clippy；Python：≥3.12，虚拟环境，安装maturin≥1.0、匹配版本的PyO3；依赖版本分别锁定在Cargo.toml、pyproject.toml。

## 3. 代码规范
Rust：遵循rustfmt/clippy，PyO3绑定函数用snake_case，错误封装为PyErr；Python：PEP8+类型注解，禁止直调Rust底层；通用：核心逻辑写文档字符串。

## 4. 构建流程
开发：`maturin develop`；发布：`maturin build --release`；验证跨平台（Linux/macOS/Windows）构建。

## 5. 测试与调试
测试：Rust用cargo test，Python用pytest，集成测试验证跨语言数据传递；调试：Rust用rust-gdb，Python用pdb，PyO3调试模式`maturin develop --debug`；性能：减少跨语言调用，Rust避免内存拷贝。

## 6. 版本控制
分支：main（稳定）、dev（开发），功能分支`feature/xxx`；提交：语义化（feat/fix/docs: 描述）；版本：语义化版本，同步Cargo/pyproject.toml版本。

## 7. 发布流程
测试通过，更新CHANGELOG；2. 打tag（vX.Y.Z），`maturin publish`；3. 验证wheel安装。

