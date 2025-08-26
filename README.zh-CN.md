# FRC 赛事积分分析器

[English](README.md) | [中文（简体）](README.zh-CN.md)

用于分析 FRC（FIRST 机器人竞赛）赛事并计算 2025+ 赛季的区域积分。支持整季区域池计算，提供命令行与 Python API，内置本地缓存与实时进度显示。

## 功能特性

- 赛事分析：队伍、排名、联盟、比赛、奖项
- 2025+ 区域积分：排位、联盟选择、淘汰晋级、奖项、新秀加分
- 区域池：每周自动晋级与席位分配（2025）；每站前 3（2026，可回填）
- 缓存：自动将 FRC Events API 响应以 JSON 缓存到 `cache/`
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
- `regional-pool` 会先计算本赛季赛事数量（较快），随后构建每个赛事（较慢，显示进度条）。数据会缓存到 `cache/`，再次运行更快。

## Streamlit 可视化面板（v2.1.0）

现代化、用户友好的 Streamlit 面板，全新 UI/UX 设计，提供全面的 FRC 赛事分析工具。

安装：

```bash
pip install -e .
pip install -r requirements.txt  # 确保安装 streamlit
```

运行：

```bash
streamlit run src/frc_calculator/ui/streamlit_app.py
```

### 主要功能：
- **🔐 增强凭据设置**：从侧边栏移至主界面，支持内联验证、清晰错误提示和更好的安全指示器
- **🏆 赛事分析**：智能赛事选择（下拉菜单 + 手动覆盖）、改进的进度追踪、格式化数据表格与队伍信息
- **📊 积分计算器**：重新设计的界面，包含更好的输入验证、可视化积分细分和全面的队伍表现指标
- **🏁 区域池**：增强的赛季构建，详细进度追踪、资格状态指示器和摘要统计信息

### UI 改进：
- 采用表情符号图标的现代设计，更好的视觉层级结构
- 移动友好的表单，使用文本输入替代数字调节器
- 增强错误处理，可展开详情和上下文帮助
- 更好的数据可视化，包含列配置和状态指示器

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

- 缓存文件保存在 `cache/`（自动创建），格式与 FRC Events API 响应一致。
- 再次运行将优先使用缓存，如缺字段再按需请求。
- 若需强制刷新，可删除 `cache/` 目录。

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
- 当前测试依赖在线 API（或本地缓存）。如需可重复测试，建议先将响应缓存到 `cache/`。

## 许可

Add your license here.

## 支持

- 在仓库中提交 Issue（请附带复现步骤与日志）
- 首次运行需确认 `.env` 配置正确且网络可用

## 版本记录

### v2.1.0（UI/UX 全面改版）
- **🎨 完整 UI 重新设计**：现代化界面，表情符号图标，更好的视觉层级和间距
- **📱 移动友好表单**：使用文本输入替代数字调节器，提供更好的移动端体验
- **🔐 增强凭据管理**：从侧边栏移至主界面，支持内联验证和更清晰的错误消息
- **📊 更好的数据可视化**：增强表格格式、列配置、进度指示器和摘要统计信息
- **🚀 改进用户体验**：上下文帮助、可展开错误详情和可操作的指导消息

### v2.0.0（重构）
- 新增 Streamlit 仪表盘（下拉选择赛事 + 手动覆盖）
- 支持凭据校验，错误更清晰；API 客户端更健壮并带超时
- 区域池构建进度反馈增强（状态 + 最近赛事列表）
- 更新文档（README、README.zh-CN、CLAUDE.md）

### v1.0.0
- 重构为模块化包，提供 CLI 与实时进度
- 保持原有计算逻辑，并迁移到 `src/frc_calculator`
- 自动创建本地缓存目录，体验更佳
