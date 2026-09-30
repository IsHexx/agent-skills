---
name: failure-triage
description: 旧 /failure-triage 参数兼容入口；只把 run_id 转交 /api-test。
---

# failure-triage 兼容转发

CONTRACT: docs/workflow_contract.json
FORWARD_ONLY: /api-test

- `/failure-triage`：定位最近已完成批次，把关联工作流转交 `/api-test` 恢复。
- `/failure-triage <run_id>`：解析 run_id 的服务、模块和 workflow_id，转交 `/api-test` 恢复。
