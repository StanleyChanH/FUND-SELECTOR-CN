# 基金量化分析平台

基于Streamlit的交互式公募基金量化分析平台，提供全面的基金分析功能和可视化展示。

> **v2.0 已发布**：数据层全面重构——**自定义 SQL 数据源**（SQLite / PostgreSQL / MySQL / ClickHouse / DuckDB）、
> **本地数据落地**（Parquet 缓存 + DuckDB 离线查询），Tushare 退化为「数据下载通道之一」。
> 详见下方 [🔗 自定义数据源（v2.0）](#-自定义数据源v20) 章节，实现讨论见 [#1](https://github.com/StanleyChanH/FUND-SELECTOR-CN/issues/1)。

## 功能特性

### 📊 核心功能
- **基金概览**: 基本资料、基金经理、规模与分红信息
- **业绩分析**: 区间累计收益率、年化收益率、波动率、最大回撤、夏普比率、卡玛比率
- **技术分析**: 移动平均线、RSI、布林带、MACD、KDJ等10+种技术指标
- **投资解读**: 基于技术指标的专业投资建议和风险评估
- **风险分析**: 滚动波动率、相对强弱指数分析
- **基准对比**: 支持沪深300、中证500、上证50、创业板指等基准对比
- **年度收益**: 历年年度收益率对比分析

### 🎨 可视化特性
- **交互式图表**: 基于Plotly的动态图表
- **响应式设计**: 适配不同屏幕尺寸
- **实时更新**: 参数调整后即时重新计算和显示
- **多维度展示**: 表格、图表、指标卡片多种展示方式

## 技术栈

- **前端**: Streamlit
- **后端**: Python 3.12+
- **数据处理**: Pandas, NumPy
- **可视化**: Plotly
- **数据源**: DataProvider 统一抽象（Tushare / 自定义 SQL 数据库 / 本地 Parquet 缓存）
- **技术指标**: pandas-ta (专业库，提供150+技术指标)

## 安装使用

### 环境要求
- Python 3.12+
- uv (推荐的Python包管理器)
- Tushare Pro Token (需要注册Tushare Pro账户)

**核心依赖**: pandas-ta (专业技术指标库，已集成安装)

### 安装步骤

1. 克隆项目
```bash
git clone https://github.com/StanleyChanH/FUND-SELECTOR-CN.git
cd FUND-SELECTOR-CN
```

2. 运行应用（多种启动方式）

#### 🚀 一键启动（推荐）
```bash
chmod +x start.sh  # 添加执行权限（仅第一次需要）
./start.sh
```

#### 🛠 手动启动
```bash
# 创建虚拟环境并安装依赖
uv venv
uv sync

# 运行应用
uv run streamlit run app.py
```

#### 📦 使用启动脚本
```bash
uv run run.py
```

应用将在浏览器中打开，默认地址为 `http://localhost:48501`

### 🔧 一键启动脚本功能

项目包含 `start.sh` 一键启动脚本，自动处理以下任务：

- **环境检查**：验证uv包管理器是否已安装
- **虚拟环境创建**：自动创建和管理.venv虚拟环境
- **依赖同步**：运行`uv sync`安装所有项目依赖
- **应用启动**：启动Streamlit应用并自动打开浏览器

> 💡 **提示**：首次运行会自动安装依赖，后续启动会更快。

### 配置说明

1. **获取Tushare Pro Token**
   - 访问 [Tushare官网](https://tushare.pro/)
   - 注册账户并获取API Token
   - 在应用侧边栏中输入Token

2. **基金代码格式**
   - 沪市基金：`510300.SH`
   - 深市基金：`159919.SZ`
   - 格式：`基金代码.交易所标识`

## 项目结构

```
fund-selector-cn/
├── app.py                 # 主应用入口
├── run.py                 # 启动脚本
├── start.sh               # 🚀 一键启动脚本
├── config.example.yaml    # v2.0 数据源配置模板（复制为 config.yaml 使用）
├── pyproject.toml         # 项目配置和依赖
├── README.md             # 项目说明文档
├── LICENSE               # MIT开源许可证
├── tests/                # 单元测试（缓存 / SQL 数据源 / 读取链路 / 同步）
└── src/                  # 源代码目录
    ├── __init__.py       # 包初始化文件
    ├── config.py         # v2.0 配置加载（YAML/JSON + 环境变量）
    ├── cache.py          # v2.0 Parquet 本地数据落地
    ├── datasource.py     # v2.0 DataSource 统一门面（SQL→缓存→远端）
    ├── sync.py           # v2.0 数据落地 CLI（python -m src.sync）
    ├── data_loader.py    # 数据加载模块（兼容 v1 签名）
    ├── indicators.py     # 技术指标计算模块 (使用pandas-ta)
    ├── visualization.py  # 数据可视化模块
    └── providers/        # v2.0 DataProvider 抽象层
        ├── base.py       # 规范数据集结构 + 基类
        ├── tushare_provider.py  # Tushare 适配器（下载通道）
        └── sql_provider.py      # 自定义 SQL 数据源适配器
```

## 使用指南

### 基本操作

1. **设置参数**: 在左侧控制面板中输入Tushare Token和基金代码
2. **选择时间范围**: 设置分析的时间区间（默认为过去3年）
3. **选择基准**: 选择用于对比的基准指数
4. **调整技术指标**: 设置移动平均线周期、RSI周期等参数
5. **选择高级指标**: 选择要显示的高级技术指标

### 分析模块

1. **基金概览**: 查看基金基本信息、基金经理、规模变化和分红记录
2. **净值走势**: 查看基金净值走势、移动平均线、布林带、金叉死叉信号
3. **风险分析**: 查看滚动波动率和RSI指标
4. **技术指标投资解读**: 基于10种技术指标的综合投资建议和风险评估
5. **高级技术指标**: 查看MACD、KDJ、CCI等高级技术指标详细图表
6. **年度收益**: 对比基金与基准的年度收益率

## 技术指标说明

### 基础指标
- **移动平均线 (MA)**: 短期和长期移动平均线
- **相对强弱指数 (RSI)**: 衡量价格变动的速度和变化幅度

### 高级指标
- **布林带 (BOLL)**: 价格通道指标
- **MACD**: 指数平滑异同移动平均线
- **KDJ**: 随机指标
- **CCI**: 顺势指标
- **DMI**: 动向指标
- **BBI**: 多空指标
- **TRIX**: 三重指数平滑移动平均线
- **ATR**: 真实波动率
- **OBV**: 能量潮
- **MFI**: 资金流量指标

### 投资解读功能
- **综合信号**: 基于多指标的综合判断（偏多/偏空/中性）
- **风险评估**: 根据波动性和技术指标评估风险等级
- **信号统计**: 看涨vs看跌指标数量对比
- **投资建议**: 提供基于技术指标的一句话投资建议
- **详细分析**: 每个技术指标的具体数值和解读

## 注意事项

1. **数据限制**: Tushare Pro API有调用频率限制，请合理使用
2. **数据准确性**: 数据来源于Tushare，仅供参考，不构成投资建议
3. **Token安全**: 请妥善保管您的Tushare Token，不要在公共场合泄露
4. **网络要求**: 需要稳定的网络连接以获取实时数据

## 常见问题

### Q: 无法获取基金数据？
A: 请检查：
- Tushare Token是否正确
- 基金代码格式是否正确
- 网络连接是否正常
- 是否有足够的API调用次数

### Q: 技术指标显示异常？
A: 可能原因：
- 数据量不足，无法计算某些指标
- 基金代码错误或数据缺失
- 时间范围设置过短

### Q: 图表加载缓慢？
A: 建议：
- 缩短时间范围
- 减少选择的技术指标数量
- 检查网络连接速度

## 🔗 自定义数据源（v2.0）

v2.0 把数据层重构为「**自定义 SQL 数据源 + 本地数据落地 + Tushare 下载通道**」三层架构：

```
读取链路:  自建 SQL 库（实时真源，命中即返回）
           → 本地 Parquet 缓存（覆盖区间则零网络）
           → Tushare（仅补缺失区间，拉回后自动落地）
```

### 快速上手

1. 复制配置模板并编辑：

   ```bash
   cp config.example.yaml config.yaml
   ```

2. 把 `datasource.provider` 改为 `sql`，填入你的数据库 DSN 与各数据集查询：

   ```yaml
   datasource:
     provider: sql
     dsn: postgresql+psycopg2://user:pass@host:5432/funds   # 任意 SQLAlchemy DSN
     datasets:
       fund_nav:
         query: >-
           SELECT fund_code, nav_date, net_value
           FROM my_nav_table
           WHERE fund_code = :code
             AND nav_date BETWEEN :start_date AND :end_date
           ORDER BY nav_date
         column_map: {fund_code: ts_code, net_value: unit_nav}   # 把你的列名映射到规范列
   ```

3. 启动应用，侧边栏「数据源」选择 **自定义 SQL 数据源** 即可；Tushare Token 不再是必填项。

### 支持的数据库（任选其一）

| 数据库 | DSN 示例 | 安装额外依赖 |
|---|---|---|
| SQLite | `sqlite:///data/funds.db` | 无（标准库） |
| PostgreSQL | `postgresql+psycopg2://user:pass@host:5432/db` | `pip install fund-selector-cn[postgresql]` |
| MySQL | `mysql+pymysql://user:pass@host:3306/db` | `pip install fund-selector-cn[mysql]` |
| ClickHouse | `clickhouse+native://host/db` | `pip install fund-selector-cn[clickhouse]` |
| DuckDB | `duckdb:///data/funds.duckdb` | `pip install fund-selector-cn[duckdb]` |

### 查询绑定参数

每条查询可用的绑定参数（按需选用，不用的可以不写）：

| 参数 | 格式 | 说明 |
|---|---|---|
| `:code` | `510300.SH` | 基金/指数代码 |
| `:start_date` / `:end_date` | `20240102` | 紧凑日期（含端点） |
| `:start_date_iso` / `:end_date_iso` | `2024-01-02` | ISO 日期，适配 DATE / ISO 字符串列 |

返回列必须覆盖对应数据集的必选列（列名不同时用 `column_map` 重命名）：

| 数据集 | 必选列 | 可选列 |
|---|---|---|
| `fund_nav` | ts_code, nav_date, unit_nav | adj_nav |
| `fund_basic` | ts_code, name | management, found_date, benchmark... |
| `fund_manager` | ts_code, name | ann_date, begin_date, end_date, edu... |
| `fund_share` | ts_code, trade_date, fd_share | fund_type |
| `fund_div` | ts_code, ex_date | ann_date, dividend, base_share |
| `index_daily` | ts_code, trade_date, close | open, high, low, pct_chg... |

### 本地数据落地与离线分析

所有从 Tushare 下载的数据自动以 Parquet 落地到缓存目录（默认 `.fund_cache/`，可在配置中修改），
重复分析不再请求网络；界面侧边栏可随时开关。

批量预下载（无 UI）：

```bash
python -m src.sync --codes 510300.SH,000300.SH --start 20200101 --end 20261124
```

落地后可用 DuckDB 直接对 Parquet 做离线 SQL 分析（可选依赖）：

```sql
SELECT nav_date, unit_nav
FROM read_parquet(".fund_cache/fund_nav/*.parquet")
WHERE ts_code = '510300.SH'
ORDER BY nav_date;
```

代码中同样可用：`DataSource.query_local("SELECT ... FROM read_parquet(...)")`。

### 兼容性

- v1 的 `initialize_tushare(token)` / `load_fund_data(pro, ...)` 等调用方式**完全兼容**，
  旧脚本无需修改；传入的 tushare pro 对象会被自动包装为 Provider。
- 所有适配器均有单元测试覆盖（`uv run pytest`，19 个用例，无网络依赖）。


## 路线图

- **v2.0 · 自定义 SQL 数据源与数据本地落地** ✅ 已完成（2026-11，[里程碑 1](https://github.com/StanleyChanH/FUND-SELECTOR-CN/milestone/1)）
  - [x] 抽象统一 DataProvider 接口，内置 SQLite / PostgreSQL / MySQL / ClickHouse 适配
  - [x] 数据本地落地：Parquet 缓存 + DuckDB 查询
  - [x] Tushare 迁移为默认 Provider，仅承担数据下载通道
- 需求与进度见 [Issues](https://github.com/StanleyChanH/FUND-SELECTOR-CN/issues)

## 贡献指南

欢迎提交Issue和Pull Request来改进这个项目！

## 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 免责声明

本应用提供的数据和分析结果仅供参考，不构成任何投资建议。投资有风险，入市需谨慎。

### 特别声明
- **技术指标投资解读**功能基于历史数据和技术分析方法，仅供参考
- 投资建议不保证准确性，请结合基本面分析和风险评估
- 过往业绩不代表未来表现，投资决策需谨慎