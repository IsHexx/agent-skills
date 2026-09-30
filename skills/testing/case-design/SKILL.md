---
name: case-design
description: 旧 /case-design 参数兼容入口；只把参数转交 /api-test。
---

# case-design 兼容转发

CONTRACT: docs/workflow_contract.json
FORWARD_ONLY: /api-test

- `/case-design <服务>`：把服务及“全部模块”范围转交 `/api-test`，需求资料由统一入口定位。
- `/case-design <服务> <模块> [需求资料]`：原样转交 `/api-test <服务> <模块> <需求资料>`。
