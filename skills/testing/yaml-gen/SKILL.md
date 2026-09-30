---
name: yaml-gen
description: 旧 /yaml-gen 参数兼容入口；只把参数转交 /api-test。
---

# yaml-gen 兼容转发

CONTRACT: docs/workflow_contract.json
FORWARD_ONLY: /api-test

- `/yaml-gen L0 <服务>`：转交时固定模块为“全部模块”，把 L0 兼容意图和可定位需求资料一并传给 `/api-test`。
  此 L0 是历史范围参数（全部模块），与用例分层规则中 L0 业务主流程的含义无关，转交时不得混淆。
- `/yaml-gen L1 <Excel路径>`：从 Excel 路径解析服务、模块，把 Excel 作为需求资料之一转交 `/api-test`。
- `/yaml-gen L2 <Excel路径>`：同上，并把 L2 兼容意图作为上下文转交。
