# Python+Rust（PyO3绑定）项目架构规范-代码分层详细说明
对「Rust核心层、PyO3绑定层、Python门面层」三层架构进行逐层级拆解，明确每一层的**核心职责、设计原则、技术栈、目录落地、开发规范、典型场景**，同时补充**层间交互规则**和**落地检查标准**，确保分层架构可落地、低耦合、高可维护。

所有分层均遵循**单向依赖原则**：`Python门面层 → PyO3绑定层 → Rust核心层`，禁止反向依赖、跨层直接调用，保障架构的清晰性和扩展性。

## 核心分层总纲
三层架构的设计本质是**“职责分离+工具适配”**，核心目标是让Rust专注性能与安全，Python专注易用性与生态，PyO3仅做“无业务逻辑的桥接”，最终实现：
1. 底层核心逻辑的**高性能、内存安全、跨平台**；
2. 上层用户接口的**Pythonic、易扩展、生态兼容**；
3. 跨语言交互的**低开销、无内存泄漏、类型一致**。

三层依赖关系与数据流向如下：
```
用户操作 → Python门面层（API调用/配置）→ PyO3绑定层（类型/错误转换）→ Rust核心层（实际执行）
                                          ↓（结果回传）
Rust核心层（执行结果）→ PyO3绑定层（类型反向转换）→ Python门面层（结果封装/返回）→ 用户感知
```

## 1. Rust核心层：项目的性能与安全基石
### 1.1 核心职责
作为整个项目的**底层执行引擎**，负责所有**性能关键、内存安全关键、业务核心**的逻辑实现，是项目的“算力核心”，**不感知Python层的存在**，可独立编译、测试、运行。
### 1.2 设计原则
1. **纯Rust实现**：无任何PyO3相关代码，无Python依赖，保证Rust层的独立性和可复用性；
2. **内存安全优先**：严格遵循Rust内存模型，禁用`unsafe`代码（项目中`#![deny(unsafe_code)]`），特殊场景需经评审并标注详细文档；
3. **模块化拆分**：按**业务域/功能域**拆分子crate，高内聚低耦合，单个crate仅负责单一核心功能；
4. **可测试性**：核心逻辑需完善单元测试/基准测试，支持独立`cargo test`/`cargo bench`；
5. **错误标准化**：使用统一的错误处理方案（如项目中的`anyhow::Error`/自定义错误枚举），避免裸panic，保证错误可追溯。
### 1.3 技术栈&核心工具
- 核心语言：Rust 1.70+（匹配PyO3最低兼容版本）；
- 构建工具：Cargo（依赖管理、编译、测试）；
- 异步框架：tokio（项目中用于高性能网络/异步执行）；
- 错误处理：anyhow（通用错误）、thiserror（自定义业务错误）；
- 代码检查：cargo clippy（严格lint）、rustfmt（代码格式化）；
- 性能测试：criterion（基准测试）、iai（微基准测试）。
### 1.4 目录落地
基于项目的`crates/`目录，按业务域拆分子crate，**所有PyO3相关代码均不进入此层**，典型结构：
```
project-root/
└── crates/                # Rust核心层根目录
    ├── model/             # 公共数据模型（如InstrumentId、Bar、Order），所有子crate的基础依赖
    ├── analysis/          # 高性能计算（指标计算、回测分析）
    ├── backtest/          # 回测引擎核心逻辑（事件驱动、订单匹配）
    ├── live/              # 实盘交易核心（网络适配器、交易所对接、订单执行）
    ├── cli/               # 命令行工具核心（如项目中的nautilus-cli）
    └── infrastructure/    # 基础设施（数据库、缓存、日志）
# 每个子crate的内部结构遵循Rust标准：src/（源码）、Cargo.toml（依赖/feature）、benches/（性能测试）、tests/（集成测试）
```
**crate拆分准则**：
- 通用能力抽为独立crate（如`model/`），供其他业务crate依赖；
- 业务相关crate仅依赖通用crate，避免循环依赖；
- 轻量feature开关：通过Cargo feature控制功能编译（如项目中的`defi`/`postgres`）。
### 1.5 开发核心规范
1. **代码约束**：遵循项目的Rust lint规则（`deny(missing_debug_implementations)`/`deny(clippy::missing_errors_doc)`等），保证代码可读性和健壮性；
2. **数据模型设计**：核心结构体/枚举需实现`Debug`/`Clone`/`Send`/`Sync`（异步场景必须），避免大对象拷贝，优先使用引用/智能指针（`Arc`/`Rc`）；
3. **无业务无关逻辑**：不处理Python的类型要求、配置格式等，仅关注Rust层的业务逻辑；
4. **函数设计**：参数/返回值使用Rust原生类型，复杂逻辑拆分为小函数，保证单一职责；
5. **独立运行**：所有核心功能可通过Rust二进制程序独立运行，不依赖Python层。
### 1.6 典型功能场景
项目中所有**性能/安全关键型操作**均归属于此层，以NautilusTrader为例：
- 纳秒级时间序列数据处理、K线生成；
- 订单匹配引擎、实盘订单报单/撤单逻辑；
- 高吞吐量网络通信（WebSocket/REST）、交易所数据解析；
- 数据库底层操作（PostgreSQL schema初始化、数据读写）；
- 高性能指标计算（MA/EMA/RSI等，避免Python的性能瓶颈）；
- 系统底层日志、监控、错误处理。

## 2. PyO3绑定层：跨语言的无业务桥接器
### 2.1 核心职责
作为**Rust核心层与Python门面层的唯一通信桥梁**，仅负责**跨语言类型转换、Rust功能暴露、错误透传、内存生命周期管理**，**不实现任何业务逻辑**，是三层架构中的“翻译官”。
### 2.2 设计原则
1. **最小桥接**：仅做“翻译”和“转发”，不添加任何业务逻辑（如数据过滤、计算、判断），避免成为性能瓶颈或维护难点；
2. **单一职责**：每个绑定代码仅对应Rust层的一个功能/类型，保证绑定逻辑的清晰性；
3. **内存安全**：严格遵循PyO3的内存模型，明确跨语言内存所有权（Rust管理的内存禁止Python侧释放，Python对象在Rust侧需通过PyO3的智能指针管理）；
4. **类型一致**：保证Rust类型与Python类型的映射一致性，避免类型歧义；
5. **错误透传**：将Rust层的错误无缝转换为Python原生异常，保证用户在Python层可捕获/处理所有错误。
### 2.3 技术栈&核心工具
- 核心库：PyO3（最新稳定版，如0.26+）、maturin（Python扩展编译/打包）；
- 类型工具：pyo3-stub-gen（生成Python类型存根`.pyi`）；
- 辅助工具：cbindgen（可选，跨平台类型兼容）。
### 2.4 目录落地
项目中**所有PyO3绑定代码集中管理**，避免散落在各个Rust子crate中，降低维护成本，典型结构：
```
project-root/
├── crates/
│   └── pyo3/            # PyO3绑定层根目录（独立crate），唯一依赖PyO3的Rust模块
│       ├── src/
│       │   ├── lib.rs   # 绑定入口，重导出各模块的绑定
│       │   ├── model/   # 对应crates/model/的类型绑定（结构体/枚举导出）
│       │   ├── analysis/ # 对应crates/analysis/的方法绑定（指标计算方法导出）
│       │   └── backtest/ # 对应crates/backtest/的引擎绑定（回测引擎类导出）
│       └── Cargo.toml   # 依赖PyO3+Rust核心层的各子crate（model/analysis/等）
└── python/
    ├── pyproject.toml   # maturin构建配置（指定绑定层crate、Python版本）
    └── generate_stubs.py # 自动生成Python类型存根的脚本
# 编译后生成Python扩展库：python/nautilus_trader/_libnautilus.so（Linux/macOS）/_libnautilus.pyd（Windows）
```
**绑定层设计准则**：
- 绑定层crate（`crates/pyo3/`）仅依赖PyO3和Rust核心层的子crate，无其他外部依赖；
- 按Rust核心层的crate结构，对应拆分绑定模块（如`model/`/`analysis/`），保证目录映射一致；
- 通过Cargo feature控制绑定范围（如`--features backtest`仅编译回测相关绑定）。
### 2.5 开发核心规范
#### 2.5.1 绑定代码规范
1. **集中导出**：所有Rust类型/方法均通过`crates/pyo3/src/lib.rs`统一重导出，Python层仅通过一个扩展库访问，避免多扩展库的混乱；
2. **类型映射规范**：
   - 基础类型：直接映射（Rust `i64`→Python `int`、`f64`→Python `float`、`String`→Python `str`）；
   - 集合类型：Rust `Vec<T>`→Python `list`、`HashMap<K,V>`→Python `dict`、`Option<T>`→Python `None/T`；
   - 自定义类型：Rust结构体/枚举通过`#[pyclass]`导出，字段需标注`#[pyo3(get, set)]`（按需）；
   - 复杂类型：优先转换为Python原生类型，避免暴露底层Rust智能指针（如`Arc`）给Python层；
3. **方法绑定规范**：
   - Rust函数通过`#[pyfunction]`导出，Rust类方法通过`#[pymethods]`导出；
   - 方法参数/返回值使用PyO3的`PyResult<T>`，保证错误可转换为Python异常；
   - 避免跨语言频繁调用：将批量操作封装为单个方法（如批量数据处理），减少PyO3的交互开销；
4. **枚举类型处理**：Rust枚举通过`#[pyclass]`+`#[pymethods]`导出，或转换为Python枚举（`enum.Enum`），保证Python层的易用性。

#### 2.5.2 错误转换规范
1. 统一将Rust层的错误（`anyhow::Error`/自定义`thiserror`枚举）转换为Python原生异常；
2. 按错误类型分类转换（如Rust的IO错误→Python `OSError`、业务错误→Python `ValueError`/自定义异常）；
3. 错误信息需包含原始Rust错误详情，保证可追溯；
4. 禁止吞掉Rust层的错误，所有错误必须透传至Python层。

#### 2.5.3 内存与生命周期规范
1. 使用PyO3的智能指针（`Py<T>`/`&PyAny`）管理Python对象在Rust侧的生命周期；
2. 导出的Rust对象在Python侧的生命周期由PyO3管理，避免Rust侧提前释放；
3. 大对象传输优先使用**零拷贝**（如Rust的`&[u8]`→Python的`bytes`），避免内存拷贝；
4. 禁止在Rust侧手动释放Python对象，禁止在Python侧手动释放Rust对象。

#### 2.5.4 类型存根规范
1. 绑定代码编译后，必须通过`pyo3-stub-gen`生成**完整的Python类型存根（.pyi）**；
2. 类型存根需与扩展库放在同一目录，保证Python IDE的自动补全和`mypy`静态类型检查；
3. 修改绑定代码后，必须重新生成类型存根，并纳入版本管理。

### 2.6 典型功能场景
绑定层仅做**无业务逻辑的桥接操作**，典型场景：
- 将Rust核心层的`InstrumentId`/`Bar`等自定义结构体导出为Python可实例化的类；
- 将Rust的`calculate_ema`高性能指标函数导出为Python可调用的函数；
- 将Rust的回测引擎`BacktestEngine`类导出为Python类，并绑定其`run()`/`add_strategy()`方法；
- 将Rust层的数据库操作（如`init_postgres_schema`）导出为Python函数；
- 将Rust的`TradingError`自定义错误转换为Python的`TradingException`异常；
- 将Rust的批量K线数据（`Vec<Bar>`）转换为Python的`list[Bar]`并返回。

## 3. Python门面层：用户面向的易用性接口
### 3.1 核心职责
作为**用户直接接触的顶层层**，基于PyO3绑定层暴露的Rust功能，封装成**Pythonic、易使用、高扩展**的API，同时负责**用户交互、生态集成、配置解析、上层逻辑封装**，**不实现任何高性能/底层逻辑**。
### 3.2 设计原则
1. **Pythonic优先**：遵循Python的PEP8规范、命名习惯（驼峰→蛇形）、API设计思路，让Python用户无学习成本；
2. **纯Python实现**：仅调用PyO3绑定层的扩展库，不编写任何Rust/PyO3代码，不直接操作底层扩展库的内部属性；
3. **类型友好**：全量类型注解，配合绑定层的类型存根，保证`mypy`静态类型检查通过，IDE自动补全；
4. **轻量封装**：仅做“薄封装”，避免过度封装导致性能损耗，核心逻辑仍由Rust层执行；
5. **生态兼容**：无缝对接Python主流生态（pandas/numpy/matplotlib/Scikit-learn），满足数据科学/量化交易的用户需求；
6. **易用性至上**：提供简洁的入口函数、丰富的文档、友好的错误提示，降低用户使用门槛。
### 3.3 技术栈&核心工具
- 核心语言：Python 3.12+，匹配PyO3兼容版本；
- 代码检查：Ruff（lint+格式化，替代pylint/black）、mypy（静态类型检查）；
- 依赖管理：uv（依赖锁定，生成`uv.lock`）；
- 测试工具：pytest（单元/集成测试）；
- 生态库：pandas（数据处理）、numpy（数值计算）、click（命令行）、pydantic（配置解析）。
### 3.4 目录落地
基于项目的`python/`目录，实现**自包含的Python包**，不依赖项目顶层的旧版代码，典型结构：
```
project-root/
└── python/                # Python门面层根目录，自包含的Python包工程
    ├── project-name/   # 主Python包，用户实际导入的包（import nautilus_trader）
    │   ├── __init__.py    # 包入口，重导出核心API（隐藏底层扩展库）
    │   ├── _libnautilus.so # PyO3编译后的Rust扩展库（不建议用户直接调用）
    │   ├── _libnautilus.pyi # 自动生成的类型存根
    │   ├── core/          # 核心API封装（回测/实盘引擎的Python薄封装）
    │   ├── strategies/    # 策略基类/模板（用户策略的父类）
    │   ├── config/        # 配置解析（pydantic封装，将Python配置转换为Rust可识别的参数）
    │   ├── data/          # 数据交互API（对接Rust层的数据源，返回pandas DataFrame）
    │   ├── indicators/    # 指标API封装（调用Rust的高性能指标，提供Python友好接口）
    │   └── utils/         # Python工具函数（日志、数据转换、生态适配）
    ├── pyproject.toml     # Python包配置（maturin构建+ruff/mypy配置+依赖声明）
    ├── examples/          # Python使用示例（策略/回测/实盘）
    └── tests/             # Python层的单元/集成测试
```
**Python包设计准则**：
- **隐藏底层细节**：用户仅导入`project-name`包的顶层API，不直接操作`_libnautilus.so`和`_libnautilus.pyi`；
- **按功能模块拆分**：如`strategies/`（策略）、`config/`（配置）、`indicators/`（指标），保证目录清晰；
- **自包含**：可独立打包为Python wheel。
### 3.5 开发核心规范
#### 3.5.1 代码与命名规范
1. 严格遵循PEP8规范，使用Ruff做自动化lint和格式化；
2. 命名规则：Python原生风格（蛇形命名`calculate_ema`、小写包名`nautilus_trader`、大驼峰类名`BacktestEngine`），与Rust层的命名做适配；
3. 纯Python实现：不编写Rust代码，不直接操作PyO3扩展库的内部属性/方法；
4. 函数/方法：所有参数和返回值必须添加**完整的类型注解**，使用PEP 604语法（`Instrument | None`而非`Optional[Instrument]`）。

#### 3.5.2 API封装规范
1. **薄封装原则**：Python层的方法仅做参数校验、配置转换、结果封装，核心逻辑调用PyO3绑定层的方法执行；
   示例：
   ```python
   # Python门面层的ema计算方法（仅封装，核心由Rust执行）
   def calculate_ema(prices: list[float], window: int) -> list[float]:
       # 仅做参数校验（Python层职责）
       if window < 2:
           raise ValueError("EMA window must be greater than 1")
       # 调用PyO3绑定层的Rust方法（核心逻辑由Rust执行）
       return _libnautilus.calculate_ema(prices, window)
   ```
2. **配置解析**：使用pydantic封装配置类（如`BacktestConfig`），将Python的配置对象转换为Rust层可识别的参数（如字典/基础类型）；
3. **结果适配**：将Rust层返回的结果转换为Python用户熟悉的类型（如将Rust的`Vec<Bar>`转换为pandas `DataFrame`）；
4. **入口简化**：提供简洁的顶层入口函数/类，避免用户多层嵌套调用（如`nautilus_trader.run_backtest()`直接启动回测）。

#### 3.5.3 生态集成规范
1. 无缝对接pandas/numpy：核心数据结构（K线/订单/持仓）支持转换为`pandas.DataFrame`/`numpy.ndarray`；
2. 兼容Python主流工具：支持matplotlib可视化、logging日志、pickle序列化（按需）；
3. 策略开发友好：提供抽象的策略基类（`BaseStrategy`），用户仅需重写`on_bar()`/`on_tick()`等方法，无需关注底层Rust逻辑。

#### 3.5.4 错误与日志规范
1. 捕获PyO3绑定层的异常，并做**友好的错误提示**（补充用户可理解的操作建议）；
2. 统一使用Python的`logging`模块做日志，日志级别与Rust层保持一致（DEBUG/INFO/WARN/ERROR）；
3. 自定义Python异常：按业务场景封装自定义异常（如`StrategyError`/`DataError`），继承自Python原生异常，方便用户捕获。

### 3.6 典型功能场景
Python门面层的功能均围绕**用户易用性和生态集成**，以NautilusTrader为例：
- 封装Rust回测引擎为Python的`BacktestEngine`类，提供`add_strategy()`/`add_data()`/`run()`等简洁方法；
- 提供策略基类`BaseStrategy`，用户通过继承重写方法快速开发量化策略；
- 实现配置解析（如从YAML/JSON文件加载配置，转换为Rust可识别的参数）；
- 将Rust层返回的K线数据转换为pandas `DataFrame`，方便用户做数据分析和可视化；
- 提供实盘交易的简洁入口（`LiveTrader`），封装Rust层的交易所对接逻辑；
- 集成Python的定时任务、告警机制，补充Rust层的生态能力；
- 提供丰富的示例代码（如EMA交叉策略、实盘对接Binance），降低用户入门成本。

## 4. 层间交互核心规则（重中之重）
三层架构的稳定性依赖于严格的**层间交互规则**，禁止任何跨层、反向依赖的操作，核心规则如下：
1. **单向依赖**：仅允许`Python门面层 → PyO3绑定层 → Rust核心层`，Rust核心层不依赖PyO3绑定层，PyO3绑定层不依赖Python门面层；
2. **唯一通信入口**：Python层与Rust层的通信**仅能通过PyO3绑定层**，禁止Python层直接调用Rust核心层的代码，禁止Rust层直接操作Python对象；
3. **数据传输原则**：
   - 最小化跨语言调用次数：将批量操作封装为单个绑定方法，避免循环中频繁调用PyO3方法（跨语言调用有固定开销）；
   - 优先使用原生/轻量类型：跨语言传输优先使用基础类型、集合类型，避免传输大对象、复杂对象；
   - 零拷贝优先：大二进制数据/字节流使用零拷贝方式传输（Rust `&[u8]`→Python `bytes`），避免内存拷贝；
4. **内存所有权约定**：
   - Rust层创建的对象，所有权归Rust层，Python层仅持有**引用**，禁止Python层手动释放；
   - Python层创建的对象，在Rust层需通过PyO3的`Py<T>`智能指针管理，遵循Rust的生命周期；
5. **错误透传全链路**：Rust层的错误→PyO3绑定层转换为Python异常→Python门面层捕获/封装/返回，保证全链路错误可追溯，无吞错误；
6. **版本兼容**：PyO3绑定层需保证与Rust核心层、Python门面层的版本兼容，修改Rust核心层的接口后，必须同步更新PyO3绑定层和Python门面层；
7. **无跨层业务逻辑**：业务逻辑仅能存在于Rust核心层或Python门面层（Python层仅做上层轻量逻辑），PyO3绑定层不允许存在任何业务逻辑。

## 5. 分层架构落地检查清单
为了验证三层架构的落地是否符合规范，可通过以下清单进行检查，确保每一层的职责不越界：
### Rust核心层检查
- [ ] 无任何PyO3相关代码和依赖；
- [ ] 可独立`cargo build`/`cargo test`/`cargo run`，不依赖Python；
- [ ] 按业务域拆分子crate，无循环依赖；
- [ ] 禁用`unsafe`代码，或特殊场景有评审和文档；
- [ ] 核心逻辑有完善的单元测试和性能测试。

### PyO3绑定层检查
- [ ] 仅做类型转换、功能暴露，无任何业务逻辑；
- [ ] 所有绑定代码集中管理，不散落于Rust核心层的子crate；
- [ ] 所有Rust错误均转换为Python异常，无吞错误；
- [ ] 编译后生成完整的Python类型存根（.pyi）；
- [ ] 跨语言传输使用轻量/零拷贝类型，最小化交互开销。

### Python门面层检查
- [ ] 纯Python实现，无Rust/PyO3代码；
- [ ] 全量类型注解，`mypy`检查通过；
- [ ] API设计Pythonic，遵循PEP8，隐藏底层扩展库细节；
- [ ] 仅做薄封装，核心逻辑调用PyO3绑定层；
- [ ] 无缝对接Python主流生态（pandas/numpy等）；
- [ ] 可独立打包为Python wheel，自包含无外部依赖。

### 层间交互检查
- [ ] 无反向依赖、跨层调用；
- [ ] Python与Rust的通信仅通过PyO3绑定层；
- [ ] 跨语言调用次数最小化，批量操作做封装；
- [ ] 内存所有权清晰，无内存泄漏风险；
- [ ] 错误透传全链路，Python层可捕获所有Rust层错误。