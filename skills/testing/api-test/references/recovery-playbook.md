# API Test 迁移与恢复手册

只在 `SKILL.md` 指定的异常或兼容分支出现时完整读取本文件。生成内容仍遵守
`docs/case_generation_rules.md` 和 `docs/yaml_generation_rules.md`，本文件不另立表头、断言或流程规则。

## 旧用例表迁移

当现有工作簿仍有“业务场景清单”和“用例设计明细”时：

1. 先渲染并检查原工作簿，保留样式、用例 ID、接口、场景和设计追溯。
2. 按用例 ID 合并场景行、设计明细行和执行投影行，使一条用例只占“接口测试用例”一行。
3. 删除两个旧 Sheet，保留规则要求的 7 个 Sheet；更新规则版本和实际统计。
4. 再渲染合并后的核心区域，运行 Excel 结构与覆盖门禁。统计差异由 AI 修正，不交给用户。

## 新模块适配

当 OpenAPI 已定位，但模块没有适配器或生成器时：

1. 复用现有读取、语义校验和 manifest 能力，新增薄生成适配器并注册到 `tools/module_adapters.json`。
2. 生成器只负责目标模块目录，名称和 ID 使用稳定模块片段，不能要求用户选择脚本。
3. 生成 YAML 后必须生成 `case_manifest.json`，再进入工作流 preflight。
4. 先检查 Excel 请求头。公共登录态和公司上下文由运行器继承时，执行投影写 `{}`；只有空 token、无效
   token 等认证用例显式覆盖。禁止把 `<有效登录态token>`、`<当前企业ID>` 等说明性占位符写进 YAML。
5. 扫描所有 `${变量}`。变量必须来自运行时内置值、当前文档 variables，或同一流程前序 extract/db_extract。
   其他变量必须改造成自包含 setup→extract→业务→cleanup；无法安全完成时，将该用例记为“确认不测试”，
   同时写明缺失条件和补测方式，不能生成带未定义变量的 YAML。

## 批量业务裁决落盘

用户接受一组推荐值后，一次更新所有受影响用例的请求与唯一预期字段，包括预期结果、HTTP 状态、业务码、
响应、数据库/关联影响及必要备注；同步修正覆盖矩阵引用和统计。随后重新生成全部下游，不保留“按实际结果
确定”“成功或失败均可”“若……则……”等双预期文本。

## 单条执行命令

用户只要类似 `pytest tests/test_excel_cases.py -k "..." -q` 的命令时：

1. 从目标模块 manifest 或 YAML `name` 中选择稳定且唯一的 ID 片段，例如 `hall`、`supplier-mgmt`。
2. 先执行 `python -m pytest tests/test_all_case.py -k "<片段>" --collect-only -q`，确认命中数等于目标模块
   manifest 展开数，且没有其他模块。
3. 只输出 `python -m pytest tests/test_all_case.py -k "<片段>" -q`。不要附加 `$env:CB_API_CASE_DIR=...`。

## incomplete 执行恢复

出现以下任一情况时，执行批次不是接口失败结论：

- `run.json.verdict` 为 `incomplete`；
- 授权数量、pytest 收集数、实际执行数不一致；
- 执行数为 0、出现空原因 skip，或 pytest 退出码为 120；
- Allure 只有少量 skipped 结果，且没有真实请求/断言失败证据。

处理顺序：

1. 保存 `run.json`、原始 Allure result、当前终端输出和授权 scope。
2. 用同一目标目录运行 collect-only，核对 manifest、收集数量和选择表达式。
3. 检查执行子进程的环境传递、输出管道、提前终止、fixture 初始化和 skip reason；不得把“0 failures”当通过。
4. 修复后重跑全部本地门禁。真实复测是新批次，必须重新展示范围并取得授权。
5. 只有实际执行数等于授权用例数、skip 为 0 且 verdict 不是 incomplete，才能进入接口失败 triage 或通过汇报。
