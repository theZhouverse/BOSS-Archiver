# TASKS — BOSS-Archiver

执行状态记录（Task Contract 语义见 AGENTS.md；状态机：TODO → IN_PROGRESS → DONE/BLOCKED）

## T1 项目骨架与规范文档

- Status: DONE（2026-09-06）
- Goal: 建立 P1 工程资产：README/AGENTS/SPEC/TASKS/REVIEWS/.gitignore/requirements/check.bat
- Verification: 文件齐全且内容自洽

## T2 核心重构：v1 单文件脚本 → 模块化单体

- Status: DONE
- Trace To: SPEC FR-1~FR-8 / D1~D7
- Goal: 把 v1（611_极速版.py，297 行单文件）按依赖方向拆分为
  config/models/parsing/pacing/risk/browser/collector/writer/cli
- Allowed files: boss_archiver/**, tests/**
- Verification: compileall + pytest 全绿

## T3 地区与职位检索优化

- Status: DONE
- Trace To: FR-1 / FR-2 / D6
- Goal: 城市名/code 双入口 + 关键词 CLI 参数自动搜索 + 职位 ID 去重 + 输出链接列
- Verification: tests/test_config.py、test_parsing.py、test_writer.py 通过

## T4 风控护栏

- Status: DONE
- Trace To: NFR-1 / NFR-2 / D2 / D3 / D5
- Goal: 节拍策略（间隔+抖动）、页数上限、熔断信号识别、profile 登录态复用、串行详情抓取
- Verification: tests/test_pacing.py、tests/test_risk.py 通过

## T5 测试与最终 Gate

- Status: DONE
- Verification: check.bat 全绿（compileall + pytest）

## T6 GitHub 发布

- Status: DONE
- Goal: 公开仓库 theZhouverse/BOSS-Archiver（与文件夹同名），全新 git 历史，推送 main
- Evidence: https://github.com/theZhouverse/BOSS-Archiver（public）；origin/main = 74cdd6a；
  git ls-remote 确认 refs/heads/main 已推送；v1 旧文件归档于 D:\projects\toy\_boss_zhipin_tool_v1_archive
- Verification: gh repo create + git ls-remote 回执

## T7 Project Compass 建档登记（备案）

- Status: DONE
- Goal: 在本地 Project Compass（127.0.0.1:48327）中登记本项目：repo_path、摘要、ownership=personal、基线 commit
- Evidence: Compass 项目 id=61（name=boss_zhipin_tool, status=assessment, repo_path=D:\projects\BOSS-Archiver）；
  POST /api/projects 返回 201
- Verification: GET /api/projects?include_all=1 可见 id=61 记录
- Note: 后续 Review 阶段（成本复核/复盘/HANDOFF/维护登记）在 Compass UI 中继续

## T8 风控护栏收敛为保守档（用户反馈）

- Status: DONE（2026-09-07）
- Context: 初版默认档（详情 0.8~1.8s、无单轮上限）真机验证时被用户指出过于激进，
  连续高频开详情页存在触发平台风控、影响账号的风险（知识库同类教训：紫鸟/微信读书）
- Decision（用户已通过确认选择批准）: 默认只导列表；详情 --detail 显式开启；页数默认 2/上限 4；
  详情间隔 ≥3s（±2s）；单轮详情上限 10 次（成功+失败）；翻页间隔 ≥4s（±2s）
- Trace To: SPEC NFR-1 / FR-3 / FR-5 / AC-2
- Verification: pytest 全绿；真机复跑（1 页 + 5 条详情）结果见 Evidence 追加

## Review Findings

见 docs/REVIEWS.md；已解决的以 Commit 关联闭环。
