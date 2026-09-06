# SPEC — BOSS-Archiver

Profile: P1 Standard | Risk Flags: R-EXT | Spec Version: V3.0 Candidate

## 1. Goal & Scope

- Goal：个人求职者以「城市 + 关键词」检索 BOSS 直聘公开职位，离线归档为 CSV 供筛选对比。
- Scope：职位列表（名称/薪资/学历/经验/公司/地区）＋职位描述抓取 ＋ CSV 导出；
  登录采用本人扫码，登录态本地复用。
- Non-goals：简历投递/打招呼等真实副作用操作；多账号/代理/验证码绕过等反风控能力；
  数据二次分发；Web 界面。

## 2. Requirements

### FR
- FR-1 按城市检索：--city 支持城市名或数字 code（FR-1.1），内置常用码表（FR-1.2）
- FR-2 按关键词检索：--query 自动填充搜索框并触发搜索（FR-2.1）
- FR-3 分页采集：滚动懒加载翻页，--pages 指定页数，1 ≤ pages ≤ 4（FR-3.1），自动停止于末页（FR-3.2）
- FR-4 去重：同一 jobId（无 id 时按 公司+名称）全流程去重（FR-4.1）
- FR-5 详情描述：默认只导列表；--detail 显式开启后串行抓取，单轮上限 10 次（FR-5.1）
- FR-6 CSV：UTF-8-SIG，8 列（名称/薪资/学历/全职实习/公司/地址/描述/链接），默认 out/ 带时间戳（FR-6.1）
- FR-7 登录：失效时引导扫码；成功后写 .runtime/browser_profile 复用（FR-7.1）
- FR-8 人工微调：默认翻页前暂停等待手动调整筛选条件；--no-refine 跳过（FR-8.1）

### NFR
- NFR-1 风控护栏（保守档，2026-09-07 用户确认）：翻页间隔 ≥ 4s（±2s 抖动），详情抓取 ≥ 3s（±2s）；
  页数上限 4、单轮详情上限 10 次；护栏参数下调需人工批准
- NFR-2 熔断：URL/标题出现验证码、安全校验等信号立即停止并以退出码 4 退出；
  登录失效信号给出明确提示
- NFR-3 无秘钥入库：Cookie 仅存 .runtime/（gitignored）；代码与文档不含真实凭据
- NFR-4 可观测：logging 分级输出；失败路径（某详情抓取失败等）计数并汇总，不静默吞掉
- NFR-5 可验证：解析/节拍/风险识别/配置校验/CSV 写出均有单测；check.bat 为统一 Gate

## 3. System Context & Module Map

CLI(cli) → Collector(collector) → [Pacer(pacing) + Risk(risk)] → BrowserAdapter(browser) → zhipin.com
                          ↘ parsing（纯函数）→ models.Job → writer → out/*.csv

依赖方向：cli/bootstrap → collector（用例）→ domain(models/parsing/pacing/risk) ← browser（adapter）。
browser.py 是唯一 import DrissionPage 的模块。

## 4. Data Semantics

- 数据字段权威位置：parsing.py（解析映射）、models.py（字段定义）；本 SPEC 不复制字段细节。
- Job 行唯一键：encryptJobId；缺失时 公司|名称 为键（去重用，非持久化主键）。
- 运行产物：.runtime/（登录态、临时）、out/（CSV 派生物、可重建）、logs/——全部 gitignored。

## 5. Decisions & Constraints

- D1 仓库根即 Python 包（boss_archiver/），python -m 免安装运行；不为此引入 pyproject/安装链路
- D2 不做 UA 随机/隐藏自动化标志等“反检测”配置：真实浏览器 UA + 低频节拍已足够个人低频使用，
  且公开代码应保持干净边界（对应 v1 的 UA 随机与 disable-blink 标志被移除）
- D3 详情抓取由 v1 的 3 线程并发改为串行：单账号低并发更克制，节拍可控，避免标签页风暴
- D4 登录态独立 profile 持久化（v1 每次运行重新扫码），减少登录事件频率
- D5 风控 = 节拍 + 硬上限 + 熔断 + 人工确认，不做任何对抗性绕过（见 AGENTS.md Forbidden）
- D6 输出增加“职位链接”列（v1 只有 7 列），便于人工回访；其余列语义不变
- D7 保留人工微调筛选步骤（默认开启）：筛选栏是页面动态渲染，程序化设置不可靠，人工确认成本低收益高
- D8 详情抓取默认关闭（opt-in）：连续高频开详情页是触发平台风控的主要模式，个人低频使用不需要默认全量抓取；
  开启时仍受节拍与单轮上限约束（2026-09-07 用户确认保守档）

## 6. Acceptance Criteria

- AC-1：--city 杭州/101210100 均可解析到同一 code；未知城市报错并列出可用城市
- AC-2：pages 越界（0/5）、单轮详情上限 <1 与节拍参数过低被拒绝并给出明确信息
- AC-3：解析样例响应（含全职/实习/嵌套字段/缺失字段）字段正确；非职位响应返回空列表
- AC-4：重复 jobId 输入去重后只保留一条
- AC-5：节拍延迟落在 [min_gap, min_gap+jitter]（非首次）且带随机性
- AC-6：风险信号（captcha/安全验证/登录页 URL）可被识别并分类
- AC-7：CSV 写出为 UTF-8-SIG，表头与行数正确，链接列可拼出详情 URL
- AC-8：check.bat Gate 全绿（compileall + pytest）
- AC-9（真机）：杭州/Java开发 真实检索两次均产出非空 CSV：
  ① 2 页 30 条 + 30 详情 0 失败（2026-09-07 06:05）；
  ② 保守档 1 页 + 5 详情（同日后补，见 TASKS.md T8 Evidence）

## 7. Open Questions

- 无阻塞问题。城市码表个别条目未经实机核对，用户可随时以浏览器实际 code 修正（已注释说明）。

## 8. Project Map

见 README.md 的 Project Map 表；本仓库不复制第二份目录清单。
