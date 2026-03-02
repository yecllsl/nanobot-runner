# Python+Rust (PyO3绑定) 项目规范文档
## 1. 文档概述
### 1.1 设计哲学
遵循“合适的工具做合适的事”核心原则，结合Python的易用性/生态优势与Rust的性能/内存安全优势：
- **Rust层**：负责网络通信、数据解析、高性能计算等性能/安全关键型操作；
- **Python层**：提供用户面向的API，支撑系统配置、生态集成（如数据科学/AI工具链）；
- **PyO3桥接层**：以最小开销实现Rust功能向Python的暴露，消除跨语言交互的性能损耗与内存安全风险。

### 1.2 核心目标
- 性能：Rust核心保障纳秒级时间精度、高吞吐量的能力；
- 安全：禁用unsafe代码、严格内存契约，避免跨语言交互的内存泄漏/野指针；
- 易用性：Python层提供直观API，类型存根保障IDE提示与静态类型检查；
- 一致性：跨平台（Linux/macOS/Windows）兼容。

## 2. 项目架构规范
### 2.1 代码分层
| 层级         | 职责                                                                 | 技术栈                  |
|--------------|----------------------------------------------------------------------|-------------------------|
| Rust核心层   | 性能关键逻辑（网络、解析、引擎、计算）、数据模型、内存安全保障   | Rust + Cargo            |
| PyO3绑定层   | 统一管理Rust到Python的绑定，暴露核心功能，处理跨语言类型/错误转换    | PyO3 + maturin          |
| Python门面层 | 用户API、策略封装、配置解析、生态集成，纯Python逻辑                  | Python 3.12+ + Ruff     |

### 2.2 目录结构
```
project-root/
├── crates/                  # Rust核心子包（按功能拆分）
│   ├── pyo3/                # 集中管理所有PyO3绑定（临时统一层）
│   ├── [crate-name]/        # 业务子包（如analysis/backtest/cli）
│   │   ├── benches/         # Rust基准测试（criterion/iai）
│   │   ├── src/             # 核心逻辑
│   │   └── Cargo.toml       # 子包依赖+feature配置
├── python/                  # PyO3绑定的Python v2包（自包含）
│   ├── project-name/     # Python门面包
│   │   ├── _libnautilus.so  # 编译后的Rust扩展（maturin生成）
│   │   ├── *.pyi            # 自动生成的类型存根
│   │   └── __init__.py      # 重导出Rust扩展功能
│   ├── pyproject.toml       # maturin构建配置
│   └── generate_stubs.py    # 生成.pyi脚本（pyo3-stub-gen）
├── .cargo/                  # Rust编译配置
└── .github/                 # CI/CD（跨平台构建/测试）
```

### 2.3 功能划分准则
- 仅将“非性能关键、用户交互、生态集成”逻辑放在Python层；
- 核心耗时逻辑放在Rust层；
- 跨语言交互仅通过PyO3完成，禁止直接使用C FFI（除非特殊场景并遵循FFI内存契约）。

## 3. PyO3绑定开发规范
### 3.1 绑定层设计
- 集中管理：所有PyO3绑定统一放在`crates/pyo3/'，保障绑定逻辑收敛；
- 功能隔离：通过Cargo feature flags控制绑定开关（如`python`/`extension-module`），非绑定场景不编译相关代码。

### 3.2 Feature Flags 规范
| Feature          | 用途                                                                 |
|------------------|----------------------------------------------------------------------|
| `python`         | 启用PyO3绑定能力，依赖`pyo3` crate                                  |
| `extension-module` | 编译为Python扩展模块（maturin自动启用），依赖`python` feature       |
| `high-precision` | 启用128位数值类型（u128/i128），需兼容不同编译器的类型定义          |
| `defi`/`postgres` | 业务特性开关，仅在启用时编译对应绑定逻辑                             |

### 3.3 类型处理规范
1. **类型存根**：
   - 必须使用`pyo3-stub-gen`生成`.pyi`类型存根，保障IDE自动补全和`mypy`检查；
   - 存根生成脚本（`generate_stubs.py`）需纳入版本管理，修改Rust绑定后必须重新生成。
2. **跨语言类型映射**：
   - 128位类型：参考`cbindgen.toml`，兼容MSVC（降级为u64/i64）和GCC（__uint128_t）；
   - 枚举类型：导出Python时使用`ScreamingSnakeCase`命名规范；
   - 自定义类型：为核心结构体（如`InstrumentId`/`Bar`）定义清晰的C/Python兼容别名。
3. **错误处理**：
   - Rust错误（`anyhow::Error`/自定义错误）必须通过PyO3转换为Python异常，禁止吞异常；

### 3.4 内存安全规范
- 严格遵循`FFI Memory Contract`文档，明确跨语言内存所有权（如Rust管理的内存禁止Python侧释放）；
- 禁用`unsafe`代码（`#![deny(unsafe_code)]`），特殊场景需经严格评审并标注文档；
- PyO3对象生命周期管理：避免Python侧持有已释放的Rust对象引用。

## 4. 编码规范
### 4.1 Rust编码规范
1. **格式与Lint**：
   - 强制使用`rustfmt`格式化代码，配置遵循`rustfmt.toml`（`group_imports = "StdExternalCrate"`）；
   - 启用严格Lint规则：`deny(clippy::missing_errors_doc)`/`deny(missing_debug_implementations)`等；
   - 禁止非标准风格（`#![deny(nonstandard_style)]`）、broken intra-doc链接（`#![deny(rustdoc::broken_intra_doc_links)]`）。
2. **测试规范**：
   - 测试函数命名需体现“测试场景”，而非“断言内容”；
   - 优先使用`rstest`做参数化测试，避免重复代码；
   - 断言分组：先完成所有执行步骤，再批量断言（避免act-assert-act反模式）。

### 4.2 Python编码规范
1. **类型注解**：
   - 所有函数/方法必须包含完整类型注解（参数+返回值）；
   - 可选类型使用PEP 604语法（`Instrument | None`），禁止`Optional[Instrument]`；
   - 泛型组件使用`TypeVar`定义可复用类型参数。
2. **代码检查与风格**：
   - 使用`Ruff`做代码lint，规则配置在顶层`pyproject.toml`；
   - 文档字符串遵循NumPy规范，使用**命令式语气**（如“Return a cached client.”）；

## 5. 构建与编译规范
### 5.1 构建工具
- Rust编译：使用`cargo`（配合`rustup`管理工具链）；
- Python扩展编译：使用`maturin`（`maturin develop`开发构建，`uv build --wheel`打包）；
- 依赖管理：Python依赖用`uv`锁定（`uv.lock`），Rust依赖用`Cargo.lock`锁定。

### 5.2 跨平台编译配置
| 平台                | 关键配置                                                                 |
|---------------------|--------------------------------------------------------------------------|
| Linux (x86_64/ARM64) | RUSTFLAGS添加`-C link-arg=-Wl,--gc-sections`等，设置`PYO3_PYTHON`指定Python版本 |
| macOS (ARM64)       | RUSTFLAGS添加`-C link-arg=-undefined -C link-arg=dynamic_lookup`         |
| Windows (x86_64)    | RUSTFLAGS添加`-C target-feature=+crt-static`                             |

### 5.3 CI/CD规范
- 统一使用GitHub Actions构建，复用`common-wheel-build`动作；
- 构建产物：支持Linux/x86_64、macOS/ARM64、Windows/x86_64的Python wheel；
- 构建前检查：`cargo clippy`、`ruff check`、`mypy`类型检查。

## 6. 测试与调试规范
### 6.1 测试分层
| 测试类型       | 职责                                                                 |
|----------------|----------------------------------------------------------------------|
| 单元测试       | 覆盖核心功能/边缘场景，Rust用`cargo nextest`，Python用`pytest`       |
| 集成测试       | 验证模块间协同，基础设施测试需关联`crates/infrastructure/TESTS.md`   |
| 性能测试       | 每个Rust crate的`benches/`目录，用`criterion`（基准）/`iai`（微基准） |
| 内存泄漏测试   | 专项检查跨语言内存管理，避免泄漏                                     |

### 6.2 混合调试（Python+Rust）
1. 环境准备：安装VS Code扩展（Rust Analyzer、CodeLLDB、Python、Jupyter）；
2. 断点设置：Python/Rust代码分别设置断点；
3. 调试配置：使用`Debug Jupyter + Rust (Mixed)`配置，支持Notebook混合调试；
4. 示例验证：通过`debug_mixed_jupyter.ipynb`验证调试流程。

## 7. 文档规范
### 7.1 通用风格
- 语言：主动语态、现在时（计划功能用未来时），避免冗余词汇（如“basically”/“just”）；
- 格式：行长度控制在100-120字符，列表保持平行语法结构；
- 代码引用：行内代码用反引号，多行用代码块，引用代码时使用`file_path::function_name`（避免行号）。

### 7.2 API文档
- 必须清晰描述参数/返回值类型、副作用、使用示例；
- Python API参考用Sphinx自动生成，区分`Latest`（稳定版）/`Nightly`（开发版）；
- 废弃API：明确标注弃用原因和替代方案。

### 7.3 版本注释规范
- 发布说明（`RELEASES.md`）分`Internal Improvements`/`Documentation Updates`等章节；
- 依赖升级需标注版本号（如“Upgraded pyo3 to v0.26.0”）；
- 文档变更需说明具体改进（如“Added rate limit tables with official docs links”）。

## 8. 安全与性能规范
### 8.1 安全规范
- 禁用`unsafe`代码，特殊场景需评审并标注文档；
- 依赖安全：`cargo-deny`检查Rust依赖漏洞，`uv`锁定Python依赖版本；
- 代码扫描：CodeQL检测安全问题，禁止硬编码密钥/敏感信息。

### 8.2 性能规范
- Rust层：使用`ahash`等高效哈希库，避免不必要的内存拷贝；
- PyO3交互：最小化跨语言调用次数，批量传输数据；
- 基准测试：核心模块每次迭代需对比性能，保障无性能退化。

## 9. 贡献与发布规范
### 9.1 贡献流程
- 新功能/集成：先提交RFC issue评审，再编写代码；
- PR要求：小而聚焦，遵循`CONTRIBUTING.md`，关联相关Issue；
- PR检查项：文档符合风格、测试覆盖、编码规范、安全检查通过。
