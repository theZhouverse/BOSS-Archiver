# BOSS-Archiver — BOSS 直聘职位检索与本地归档工具

个人求职辅助工具：按「城市 + 职位关键词」检索 BOSS 直聘（zhipin.com）公开职位列表，
自动翻页去重并抓取职位描述，输出一份可直接用 Excel 打开的 CSV，供求职者本人离线筛选、对比。

> 用途边界：仅限**个人求职浏览**。请遵守 BOSS 直聘《用户协议》与当地法律法规，
> 低频使用、不要批量/商业化抓取；抓取结果只作个人分析，不得再分发。
> 本项目**不包含**验证码自动绕过、账号轮换、代理/指纹伪装等反风控对抗能力。

## 特性

- **城市检索**：内置 40+ 常用城市码表，命令行直接指定（如 杭州 / 101210100）
- **职位检索**：--query 传关键词，自动填入搜索框触发搜索
- **可选人工微调**：抓取前暂停，可在浏览器里再手动调整薪资/学历等筛选条件（默认开启）
- 自动分页 + 按职位 ID 去重；并发为 0——详情页串行抓取并受节拍限制
- **职位描述默认不抓**（--detail 显式开启，单轮上限 --max-details 默认 10 次），避免高频开页触发平台风控
- **筛选自动化**：--job-type/--salary/--experience/--degree 直接传页面文本（如 --salary 10-20K），
  自动操作筛选面板（选项从页面实时发现，不依赖硬编码 code），无需人工介入
- 登录态复用：浏览器用户数据目录持久化（.runtime/browser_profile），扫码一次长期复用
- 风控护栏（保守档）：翻页间隔 4~6s、详情间隔 3~5s（含随机抖动）；页数上限 4；单轮详情上限 10；
  检测到验证码/安全校验/登录失效立即熔断退出并提示
- 输出 UTF-8-SIG CSV（Excel 直接打开不乱码），含职位链接列，方便手动回访

## 安装

Windows + Python 3.10+（本项目在 3.10 上验证；DrissionPage 4.1.1.4）：

    pip install -r requirements.txt

首次运行会在 .runtime/browser_profile 建立独立浏览器配置（可沿用 Chrome 安装，无需额外驱动）。

## 使用

    # 默认：只导职位列表（杭州 / Java开发 / 2 页，翻页间隔 4~6s）
    python -m boss_archiver --city 杭州 --query Java开发

    # 抓职位描述（显式开启；单轮最多 10 条，每条间隔 3~5s）
    python -m boss_archiver --city 杭州 --query Java开发 --detail

    # 控制页数与详情条数
    python -m boss_archiver --city 北京 --query AI产品经理 --pages 1 --detail --max-details 5

    # 自动筛选：全职 + 10-20K + 本科 + 3-5年（条件任意组合）
    python -m boss_archiver --city 深圳 --query 数据分析 --job-type 全职 --salary 10-20K --degree 本科 --experience 3-5年

    # 城市直接传 code；指定输出文件
    python -m boss_archiver --city 101210100 --query 测试 --out my.csv

    # 调试日志
    python -m boss_archiver --city 杭州 --query Go --verbose

流程说明：脚本会打开带登录态的浏览器窗口 → 若登录失效则引导扫码（一次，之后复用）→
按参数打开检索页 →（传了筛选参数时）自动在筛选面板选择生效 → 自动翻页收集 →
（仅加 --detail 时）以 3~5s 间隔串行抓取最多 10 条职位描述 → 写入 out/ 目录 CSV。全程自动化，无需人工干预。

## 开发与验证（最终 Gate）

    check.bat

等价于：python -m compileall -q boss_archiver tests && python -m pytest -q tests

## Project Map

| 职责 | 位置 |
|---|---|
| CLI 入口 | boss_archiver/cli.py、__main__.py |
| 配置 Schema（唯一权威） | boss_archiver/config.py |
| 领域模型 / 去重 | boss_archiver/models.py |
| 响应解析（纯函数） | boss_archiver/parsing.py |
| 节拍与风险信号（纯逻辑） | boss_archiver/pacing.py、risk.py |
| 浏览器适配器（唯一 DrissionPage 依赖点） | boss_archiver/browser.py |
| 用例编排 | boss_archiver/collector.py |
| CSV 写出 | boss_archiver/writer.py |
| 单元测试 | tests/ |
| 规格 / 任务 / 评审 | docs/SPEC.md、TASKS.md、REVIEWS.md |
| Agent 行为协议 | AGENTS.md |

## 城市码

常用城市码表维护在 boss_archiver/config.py 的 CITY_CODES 中。
浏览器打开 BOSS 直聘城市页，地址栏 ?city= 后的数字即为该城市 code，可直接 --city 传入，
也欢迎提交 PR 增补码表。

## 常见问题

- 登录失效：删除 .runtime/browser_profile 后重跑，重新扫码一次。
- 抓不到数据：检查是否登录、城市码是否正确、是否触发了安全校验（脚本会熔断提示，
  请稍后再试并降低 --pages）。
- CSV 中文乱码：文件为 UTF-8-SIG，Excel 直接打开正常；若用其它工具请按 UTF-8 读取。
