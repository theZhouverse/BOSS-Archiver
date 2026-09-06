# REVIEWS — BOSS-Archiver

## Finding R-2026-09-06-01（v1 → v2 重构动机）
- Status: Resolved（由 T2 重构闭环）
- Context: v1 单文件 611_极速版.py：297 行、杭州写死、等待固定 10s、
  翻页无节拍、详情 3 线程并发、结果不去重、依赖无声明、无测试、无 .gitignore（CSV 曾被 stage）
- Expected: 模块化、参数化、可测、有护栏、产物不污染仓库
- Impact: 可维护性、账号/站点风险、公开仓库卫生
- Action Task: T2 / T3 / T4
- Commit: v2 首个 feat 提交

## Finding R-2026-09-06-02（UA 随机 / disable-blink-features 的处理）
- Status: Resolved
- Context: v1 用随机 UA + 隐藏自动化标志。评估：DrissionPage 非 WebDriver 通道，真实浏览器 UA
  更一致；随机 UA 与真实指纹不一致反而增加识别特征；公开代码应保持干净边界。
- Decision: 移除 v1 反检测配置；风险控制以节拍/上限/熔断为主（SPEC D2）
- Action Task: T4

## Finding R-2026-09-06-03（登录态复用）
- Status: Resolved
- Context: v1 每次运行都走扫码（等待固定 10s），登录事件频繁对账号不友好
- Decision: 独立用户数据目录 .runtime/browser_profile 持久化，失效才重新扫码（SPEC D4）

## Finding R-2026-09-06-04（公开仓库合规边界）
- Status: Open（持续约束）
- Context: 公开仓库涉及第三方平台数据；README 已声明个人求职用途与合规边界；
  .gitignore 排除运行产物/CSV/凭据；AGENTS.md Forbidden 明确禁止反风控对抗能力
- Expected: 任何后续 PR 不得突破上述边界

## Finding R-2026-09-07-01（默认档位过于激进，用户反馈）
- Status: Resolved（T8）
- Context: v2.0 初版默认档：详情 0.8~1.8s 连续开页、无单轮上限、页数上限 8。
  真机验证（2 页 30 条 + 30 详情，约 1 分钟内完成）期间用户指出过于激进。
- Decision: 收敛为保守档（用户确认）：详情 opt-in + 单轮上限 10 + 间隔 3~5s；
  页数默认 2/上限 4；翻页间隔 4~6s
- Impact: 默认单次运行开页数从 30+ 降至 ≤10，动作间隔整体放宽约 3 倍
- Action Task: T8
- Commit: （见 T8 闭环提交）
