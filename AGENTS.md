# Agent Instructions

Project Profile: P1 Standard（可维护个人工具，公开仓库）
Specification Version: V3.0 Candidate
Risk Flags: R-EXT（第三方站点/浏览器自动化强依赖）

## Read First
1. AGENTS.md
2. docs/TASKS.md
3. docs/SPEC.md（含 Decisions 与 Acceptance Criteria）
4. 当前 Task 相关源码与测试

## Modification Policy
- 只修改当前 Task Allowed files。
- 不得删除或弱化既有测试来让结果通过。
- 未授权不得：新增依赖、改公开 CLI 参数、改 CSV 列语义、改配置 Schema、改架构。
- 不读取或输出真实 Secret（登录 Cookie 由 .runtime/ 浏览器 profile 持有，永不入库）。
- 不捕获异常后静默忽略；失败路径必须可观测。
- 不修改 Task 无关文件。

## Requires Human Approval
- 新增第三方依赖
- 调整风控节拍默认值（降低间隔/提高页数上限属于降低护栏）
- git push / 发布 Release
- 扩大抓取范围（多账号、代理、验证码处理等一律不做）

## Forbidden
- 自动绕过验证码/安全校验、账号轮换、指纹伪装等反风控对抗能力
- force push / reset --hard 覆盖用户工作
- 把 .runtime/、out/、*.csv 等运行产物提交入库
- 在公开仓库中引入任何真实 Cookie/Token/个人数据

## Verification
Task 验证（pytest + compileall）PASS 后执行项目最终 Gate（check.bat），Gate PASS 才可 DONE。

## Stop Conditions
- SPEC / Task / Code 冲突
- BOSS 直聘页面结构或接口契约变化超出本 Task 范围
- 修改范围显著扩大
- 需要人工授权
