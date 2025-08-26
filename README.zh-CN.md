# FRC 赛事积分分析器

[English](README.md) | [中文（简体）](README.zh-CN.md)

用于分析 FRC（FIRST 机器人竞赛）赛事并计算 2025+ 赛季的区域积分。支持整季区域池计算，提供命令行与 Python API，内置本地缓存与实时进度显示。

## 功能特性

- 赛事分析：队伍、排名、联盟、比赛、奖项
- 2025+ 区域积分：排位、联盟选择、淘汰晋级、奖项、新秀加分
- 区域池：每周自动晋级与席位分配（2025）；每站前 3（2026，可回填）
- 缓存：自动将 FRC Events API 响应以 JSON 缓存到 `data/`
- 进度：CLI 在长时间抓取时显示进度与剩余时间
- Statbotics EPA：可选的分站期望得分（EPA）查询
- 命令行与编程接口：表格与 JSON 输出

## 环境要求

- Python 3.10+
- FRC Events API 访问凭据（`AUTH_USERNAME`, `AUTH_TOKEN`）
- 首次运行需要网络（之后多为本地缓存）

## 安装

```bash
git clone <repository-url>
cd frc-event-calculator
pip install -e .
```

## 配置

在项目根目录创建 `.env` 文件：

```
AUTH_USERNAME=your_username
AUTH_TOKEN=your_api_token
```

API 凭据申请：官方 FRC Events API 文档 https://frc-api.firstinspires.org/

## 命令行用法

首次运行会较慢（缓存预热），命令行会显示实时进度与剩余时间。

```bash
# 分析单个赛事
frc-calculator analyze-event 2024 AZVA

# 计算队伍的区域积分
frc-calculator calculate-points 2024 AZVA 1234 --verbose
frc-calculator calculate-points 2024 AZVA 1234 --json

# 查看区域池榜单
frc-calculator regional-pool 2025 --week 6 --top 50
frc-calculator regional-pool 2026 --week 3 --use-season 2026
```

说明：
- `regional-pool` 会先计算本赛季赛事数量（较快），随后构建每个赛事（较慢，显示进度条）。数据会缓存到 `data/`，再次运行更快。

## Streamlit 可视化面板（V2）

提供更便捷的图形化界面与更友好的进度展示。

安装：

```bash
pip install -e .
pip install -r requirements.txt  # 确保安装 streamlit
```

运行：

```bash
streamlit run src/frc_calculator/ui/streamlit_app.py
```

说明：
- 在左侧侧边栏输入 FRC Events API 凭据（仅用于本地请求）；亦可通过 `.env` 设置 `AUTH_USERNAME` 与 `AUTH_TOKEN`。
- 点击“Validate credentials”快速校验用户名/令牌。
- 赛事选择下拉框来自 FRC 列表，显示“赛事名 年份 [代码]”（如“Arizona Valley Regional 2024 [AZVA]”），也可手动输入代码。
- 区域池构建首次运行会较慢；面板会显示进度条、实时状态（已构建数量与最新赛事代码）以及近期构建的赛事列表，后续运行因缓存而更快。
- 若无凭据，仅可使用 `data/` 下已有的本地缓存；界面会明确提示。

## 编程接口

```python
from frc_calculator.models.event import Event
from frc_calculator.services.season import Season

# 单一赛事
event = Event(2024, "AZVA")
team = event.get_team_from_number(1234)
points = team.regional_points_2025()
print(points)

# 区域池
season = Season(2025, useSeason=2025)
pool_w6 = season.regional_pool_2025(weekNumber=6)
print(list(pool_w6.items())[:5])
```

## 缓存与数据

- 缓存文件保存在 `data/`（自动创建），格式与 FRC Events API 响应一致。
- 再次运行将优先使用缓存，如缺字段再按需请求。
- 若需强制刷新，可删除 `data/` 目录。

## 项目结构

```
src/frc_calculator/
  cli/app.py                  # CLI commands
  config/constants.py         # Season constants (2025/2026)
  data/frc_events.py          # FRC Events API + caching
  data/statbotics.py          # Statbotics EPA client
  models/{event,team,alliance,match}.py
  services/season.py          # Season builder + regional pool
  utils/{io_utils,math_utils}.py
```

## 开发

```bash
pip install -e .
pip install -r requirements.txt

# Run tests (note: uses live network unless you provide cached data)
python Test.py
```

提示：
- CLI 会显示进度；编程接口默认静默，如需可传入进度回调。
- 当前测试依赖在线 API（或本地缓存）。如需可重复测试，建议先将响应缓存到 `data/`。

## 许可

Add your license here.

## 支持

- 在仓库中提交 Issue（请附带复现步骤与日志）
- 首次运行需确认 `.env` 配置正确且网络可用

## 版本记录

### v2.0.0（重构）
- 新增 Streamlit 仪表盘（下拉选择赛事 + 手动覆盖）
- 支持凭据校验，错误更清晰；API 客户端更健壮并带超时
- 区域池构建进度反馈增强（状态 + 最近赛事列表）
- 更新文档（README、README.zh-CN、CLAUDE.md）

### v1.0.0
- 重构为模块化包，提供 CLI 与实时进度
- 保持原有计算逻辑，并迁移到 `src/frc_calculator`
- 自动创建本地缓存目录，体验更佳
