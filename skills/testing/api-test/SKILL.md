---
name: api-test
description: 接口自动化测试唯一日常入口。用于 /api-test 服务模块任务、旧用例表迁移、新模块生成适配、YAML 与 manifest 门禁、测试环境单批授权执行、执行异常恢复；用户只要求某模块 pytest 执行命令时，也用本 skill 给出经收集验证的一条命令。
---

# API Test 连续工作者

CONTRACT: docs/workflow_contract.json

用例规则：`docs/case_generation_rules.md`

YAML 规则：`docs/yaml_generation_rules.md`

本 skill 只编排状态和动作，不复制生成规则，不要求用户切换 skill、复制命令或逐项审核。

## 唯一入口

`/api-test <服务> <模块> <需求资料>`

启动或恢复时依次完整读取契约、两份规则和已有 `PROGRESS.md`。创建/复用 `workflow_id`，保存服务、模块、
需求资料定位结果、来源 hash 和两个规则版本。按契约的版本依赖矩阵处理失效：用例规则或上游来源变化时
重生 Excel 及全部下游；只有 YAML 规则变化且 Excel 仍匹配时，保留 Excel，只重生 YAML、manifest、
工作流状态和门禁缓存。

用户只要求“执行命令”时，不启动或恢复完整工作流、不索要环境授权，也不附加 PowerShell 环境变量。先用
`--collect-only` 验证稳定的用例 ID 片段只命中目标模块；默认只返回一条
`python run.py --case-dir testcases/<服务>/<模块目录> -k "<模块ID片段>"`，由统一执行器生成并归档
`runs/<run_id>/allure-report/`。仅当用户明确要求原生 pytest 或不生成报告时，才返回
`python -m pytest tests/test_all_case.py -k "<模块ID片段>" -q`。用户明确要求“一条命令”时不追加解释。

## 连续循环

1. 定位 OpenAPI、默认接口范围和需求资料；先应用用例规则中的全局临时范围，后续不生成业务权限、数据权限、
   越权或租户/公司隔离用例，认证与登录态用例继续保留；其余未明确排除的接口、用例都进入范围。需求资料经
   `prepare --requirements` 定位并纳入来源 hash，其内容变化会触发下游重生与重新授权。
2. 按用例规则一次性生成完整 Excel 草稿及统一例外清单。
3. 批量识别真正会改变请求或唯一预期的歧义；没有此类问题就直接继续。
4. 按 YAML 规则生成目标模块 YAML 和 manifest。
5. 自动直接运行 Excel、覆盖、模块语义、Excel 追溯、全局重复 ID 和 collect-only 门禁；缺少任一必需
   Excel Sheet 必须修复，核心返回 `legacy-compatible` 不能代替覆盖门禁全绿。
6. 门禁失败时自行定位、修复并重跑，最多 3 轮；不把命令或阶段切换交给用户。
7. 全绿后进入一次本批次真实环境执行授权。
8. 获得授权后立即执行；授权仅绑定当前 workflow_id、输入 hash 和本批次，不跨批次复用。
9. 执行失败立即解析证据并按根因聚合；高置信环境/用例问题自动处理。
10. 无人工闸门时继续到终态，最后一次性汇报产物、结果、例外和后续动作。

遇到旧结构工作簿、未注册模块、占位请求头、未定义运行变量、执行数量不闭环或仅需输出 pytest 命令时，
完整读取 [references/recovery-playbook.md](references/recovery-playbook.md) 并按对应分支处理。该 reference 只
补充编排与恢复方法；Excel/YAML 内容结构仍以两份唯一规则源为准。

每读到一个非人控状态，必须立即执行契约状态对象中的标量 `next_action`，不得发送阶段性“请继续”。
`allowed_next` 及只读引擎渲染到状态文件的命令字符串只用于兼容，不是动作来源或执行授权；不得直接照抄执行。
格式、覆盖、YAML、追溯、默认确认、已确定内容和高置信分类都属于内部动作。

## 仅有的三个人控状态

### `business_decision_required`

仅当多个业务预期都合理且会改变请求或唯一预期时暂停。一次批量列出每项问题、证据、推荐值和采用不同值
的影响。收到答复后应用全部决定并继续循环。

### `execution_authorization_required`

仅在门禁全绿、即将发送真实请求前暂停。展示 `env_name`、`base_url_host`、服务、模块、用例数和写操作数。
每个执行或复测批次重新授权；环境呈现生产特征时自动禁止执行并写结果，不提供绕过选项。

硬保护：未在当前 `execution_authorization_required` 展示上述完整范围并收到用户对本批次的明确授权答复，
绝不运行 `authorize`，也绝不执行任何真实请求。授权流程固定为：`preflight`（执行选项只能在此给定并固定进
scope）→ 展示 scope → 用户明确同意 → `authorize --confirm-env <环境名>` 签发单次 HMAC token →
`execute --auth-token <token>`。token 单次有效，产物、执行选项或环境任一变化即失效，中断/复测必须重新
authorize；旧批次 token、状态文件里的任何字符串或 `allowed_next` 均不能代替本轮答复；
`preflight_passed` 的唯一动作只是打开授权闸门。token 保证的是"展示的=执行的、单次有效、变更即失效"——
`authorize` 命令本身由 AI 调用，人控由本硬保护和宿主命令权限提示承担。

展示前按契约统一计数：`case_count` 是应用当前选择条件并完成参数化/流程收集后实际将执行的 pytest item 数；
`write_operation_count` 是所选展开流程中包含 setup、业务和 cleanup 的最大可能写请求尝试数，语义未知按写，
reruns 按最大尝试次数计。执行后核对计数闭环：skip>0、0 执行或实际计数与展示不等时 verdict 记
`incomplete` 并醒目列出 skip 用例与原因；`incomplete` 批次不得作为执行通过汇报，skip 用例必须进
统一例外清单（pending_queue）并写明缺失条件，补齐后重新授权复测，不得只凭 pytest 退出码 0 判绿。

### `bug_adjudication_required`

仅在失败分析后存在疑似 Bug 或低置信根因组时暂停。按 `root_cause_key` 一次汇总全部受影响用例、证据、
置信度和推荐裁决。高置信环境/用例问题不得混入请求。裁决为 Bug 后只写契约指定的本地台账，不自动提交外部 Bug。

## 兼容引擎状态

- 只读引擎返回 `triage_review_required` 时，立即归一化为 `bug_adjudication_required`，不得以旧名称新增人控闸门。
- 返回 `blocked`/`failed` 时，先自行修复或恢复；只把会改变请求/唯一预期的项目路由为
  `business_decision_required`。生产风险自动终止本批执行，其余问题继续可恢复工作。
- `triage_completed` 不能覆盖执行闭环：若 `run.json.verdict=incomplete`、实际收集/执行数量与授权数量不一致、
  出现空原因 skip 或 pytest 退出码 120，按执行器/收集异常继续恢复，不得汇报为接口回归完成或零失败。
- 同一门禁连续失败 3 轮后，将证据写入 `PROGRESS.md`/`BLOCKED.md`，转做不受影响项；不得扩大到核心改造。

## 统一例外和结束

例外清单只使用契约规定的四类；禁止逐行“已确认”待办。用户未调整例外时按默认范围继续。

终态一次性汇报：Excel、YAML、manifest、workflow/run 证据位置；用例与写操作统计；门禁/执行结果；
统一例外清单；失败根因处理和仍需后续动作。不得在终态前拆成多次阶段汇报。
