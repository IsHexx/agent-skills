# -*- coding: utf-8 -*-
"""平台适配层：create_bug.py / import_defects.py / probe_fields.py 只调用本文件。

第 0 阶段由 Agent 按目标平台（禅道 / Jira / 云效 / TAPD …）的官方 API 文档
实现 DefectClient 的各个方法。配置加载与错误类型已实现，无需修改。

契约见 SKILL.md「适配层接口契约」一节。
"""

import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = BASE_DIR / "config.json"


class DefectApiError(Exception):
    """平台接口调用失败（HTTP 错误或业务错误）。"""

    def __init__(self, message, status=None, body=None):
        super().__init__(message)
        self.status = status
        self.body = body


def load_config(path=None):
    """读取配置文件（默认同目录 config.json），并支持环境变量覆盖敏感项：
    DEFECT_TOKEN / DEFECT_BASE_URL / DEFECT_PROJECT。
    """
    cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)
    env_map = {
        "DEFECT_TOKEN": "token",
        "DEFECT_BASE_URL": "base_url",
        "DEFECT_PROJECT": "project",
    }
    for env_key, cfg_key in env_map.items():
        if os.environ.get(env_key):
            cfg[cfg_key] = os.environ[env_key]
    return cfg


def client_from_config(cfg):
    """按配置 dict 构造 DefectClient。"""
    if not cfg.get("token"):
        raise DefectApiError("未配置 token：请填 config.json 的 token 或设置环境变量 DEFECT_TOKEN")
    if not cfg.get("base_url"):
        raise DefectApiError("未配置 base_url：请填 config.json 的 base_url 或设置环境变量 DEFECT_BASE_URL")
    return DefectClient(
        token=cfg["token"],
        base_url=cfg["base_url"],
        platform=cfg.get("platform", ""),
    )


class DefectClient:
    """缺陷平台客户端。以下方法均需按目标平台实现（当前为未实现桩）。"""

    def __init__(self, token, base_url, platform="", timeout=30):
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.platform = platform
        self.timeout = timeout

    def search_projects(self):
        """列项目 → [{id, key, name}, ...]。"""
        raise NotImplementedError("按目标平台 API 实现：列出有权限的项目")

    def list_issue_types(self, project):
        """列缺陷类工作项类型 → [{id, name, enabled}, ...]。"""
        raise NotImplementedError("按目标平台 API 实现：列出缺陷类型")

    def get_type_fields(self, project, type_id):
        """拉字段配置 → [{id, name, type, format, required, options:[{id, displayValue, value}]}, ...]。"""
        raise NotImplementedError("按目标平台 API 实现：查字段配置")

    def search_members(self, name):
        """姓名 → [{name, id}, ...]（精确匹配由调用方做）。"""
        raise NotImplementedError("按目标平台 API 实现：成员搜索")

    def create_issue(self, project, type_id, title, description,
                     assignee=None, verifier=None, custom_fields=None, **extra):
        """创建缺陷，返回缺陷 ID/key。extra 可带 sprint / versions，平台不支持则忽略。"""
        raise NotImplementedError("按目标平台 API 实现：创建缺陷")

    def upload_attachment(self, issue_id, file_bytes, filename):
        """上传附件，返回可内嵌进描述的标记；平台不支持内嵌则返回附件链接。"""
        raise NotImplementedError("按目标平台 API 实现：上传附件")

    def update_issue(self, issue_id, **fields):
        """更新缺陷字段（主要用于把截图内嵌标记回写进 description）。"""
        raise NotImplementedError("按目标平台 API 实现：更新缺陷")
