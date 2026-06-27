#!/usr/bin/env python3
"""
Regression Test Plan Assignment Table Generator

Generates color-coded xlsx files for regression test assignment tracking.
Template structure: 2 sheets (assignment table + work summary)

Usage:
    python gen_xlsx_template.py
        Creates default "regression_test_plan.xlsx" with sample data

    python gen_xlsx_template.py --output /path/to/output.xlsx
        Creates xlsx at specified path

    python gen_xlsx_template.py --config data.json
        Creates xlsx using data from JSON config file
"""

import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter
import json
import sys
from pathlib import Path

# Default colors matching Draw.io diagrams
COLORS = {
    "header": "2F5597",      # Dark blue
    "entry": "D9D9D9",       # Light gray
    "path_a": "d5e8d4",      # Light green
    "path_b": "FFE6CC",      # Light orange
    "path_c": "dae8fc",      # Light blue
    "path_d": "f8cecc",      # Light red/pink
}

def create_thin_border():
    """Create thin border for all cells"""
    s = Side(style="thin", color="BFBFBF")
    return Border(left=s, right=s, top=s, bottom=s)

def fill_color(hex_color):
    """Create fill with specified color"""
    return PatternFill("solid", fgColor=hex_color)

def create_xlsx(output_path="regression_test_plan.xlsx", data_rows=None):
    """Generate regression test plan xlsx file"""

    wb = openpyxl.Workbook()

    # ═════════════════════════════════════════════════════════════
    # SHEET 1: 回归测试分工表
    # ═════════════════════════════════════════════════════════════
    ws = wb.active
    ws.title = "回归测试分工表"

    # Column widths
    col_widths = {"A": 16, "B": 22, "C": 38, "D": 12, "E": 10, "F": 10, "G": 26}
    for col, w in col_widths.items():
        ws.column_dimensions[col].width = w

    # Title row
    ws.merge_cells("A1:G1")
    title_cell = ws["A1"]
    title_cell.value = "生产环境回归测试分工表"
    title_cell.font = Font(name="微软雅黑", bold=True, size=14, color="FFFFFF")
    title_cell.fill = fill_color(COLORS["header"])
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36

    # Header row
    headers = ["阶段", "菜单/功能", "功能要点", "负责人", "计划天数", "优先级", "备注"]
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col_idx, value=header)
        cell.font = Font(name="微软雅黑", bold=True, size=11, color="FFFFFF")
        cell.fill = fill_color(COLORS["header"])
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = create_thin_border()
    ws.row_dimensions[2].height = 22

    # Sample data rows (if not provided)
    if data_rows is None:
        data_rows = [
            # (phase, menu, points, owner, days, priority, note, color_key)
            ("入口", "环境准备 & 数据构造", "账号创建、机器人配置、基础数据录入", "全员", "1", "P0", "第1天", "entry"),

            ("公共层\n（业务平台）", "机器人分组", "新增分组、绑定分公司、删除", "测试人员A", "0.5", "P0", "", "entry"),
            ("公共层\n（业务平台）", "机器人管理", "新增机器人、启用/停用、批量操作、推送更新、删除", "测试人员A", "0.5", "P0", "", "entry"),
            ("公共层\n（业务平台）", "任务管理（集团）", "查看全部分公司任务、筛选、批量取消", "测试人员A", "0.5", "P1", "", "entry"),
            ("公共层\n（业务平台）", "任务管理（分公司）", "查看本分公司任务、筛选、取消", "测试人员A", "0.5", "P1", "", "entry"),

            ("A—办税员\n+票税登录线", "办税员录入", "新增办税员、采集绑定企业(RPA)、查看匹配结果、批量同步、删除", "测试人员A", "1.5", "P0", "依赖：机器人已启用", "path_a"),
            ("A—办税员\n+票税登录线", "票税登录—登录信息维护", "国税/个税登录信息录入与编辑、企业/代理登录切换", "测试人员A", "1", "P0", "", "path_a"),
            ("A—办税员\n+票税登录线", "票税登录—税局登录验证", "RPA触发登录验证、验证码接收（自动/手工）、登录在线/异常状态", "测试人员A", "1", "P0", "依赖：APP验证码转发", "path_a"),
            ("A—办税员\n+票税登录线", "票税登录—纳税人信息采集", "RPA触发信息采集、公司详情更新", "测试人员A", "0.5", "P0", "", "path_a"),
            ("A—办税员\n+票税登录线", "财宝小助手", "安装检测、跳转税局/发票平台、在线判断、自动/手工登录、保活", "测试人员A", "0.5", "P1", "", "path_a"),

            ("B—发票采集线", "发票采集（小规模）", "RPA发票采集、采集状态、发票详情、录入无票收入、零申报确认/取消、确税、预约采集", "测试人员B", "2", "P0", "依赖：票税登录在线", "path_b"),
            ("B—发票采集线", "发票采集（一般纳税人）", "同小规模 + 修改税金、税负率计算、上期留抵税额", "测试人员B", "2", "P0", "", "path_b"),
            ("B—发票采集线", "确税分享（H5）", "预估增值税核对单、客户确认/存疑反馈", "测试人员B", "0.5", "P0", "需真实H5链接", "path_b"),
            ("B—发票采集线", "APP验证码转发", "短信验证码自动转发至RPA任务", "测试人员B", "0.5", "P1", "", "path_b"),

            ("C—零申报\n+报表申报线", "零申报确认", "零申报条件判断（一般/小规模）、确认、取消、账期范围", "测试人员C", "1", "P0", "依赖：发票采集完成", "path_c"),
            ("C—零申报\n+报表申报线", "报表取数", "触发取数、报表数据展示", "测试人员C", "0.5", "P0", "", "path_c"),
            ("C—零申报\n+报表申报线", "批量申报", "批量触发申报、申报状态流转（未申报/申报中/已申报/申报异常）", "测试人员C", "1", "P0", "", "path_c"),
            ("C—零申报\n+报表申报线", "获取完税证明", "RPA触发获取、证明文件展示", "测试人员C", "0.5", "P0", "", "path_c"),
            ("C—零申报\n+报表申报线", "漏报检查", "检查未申报项、漏报提醒", "测试人员C", "0.5", "P1", "", "path_c"),
            ("C—零申报\n+报表申报线", "异常重试", "申报异常后重新触发、重试状态", "测试人员C", "0.5", "P0", "", "path_c"),
            ("C—零申报\n+报表申报线", "批量作废", "批量作废申报记录", "测试人员C", "0.5", "P1", "", "path_c"),

            ("汇聚—全链路闭环", "端到端闭环验证", "跑通5条闭环路径：RPA基础设施链路、办税员→票税登录、发票采集→税金计算、零申报完整链路、异常处理链路", "全员", "1", "P0", "第7-8天", "entry"),

            ("出口", "缺陷回验 & 测试报告", "修复确认、测试报告输出、流程图标注Checklist", "全员", "1", "P0", "第8天", "entry"),

            ("D—运营平台\n管理（独立）", "应用管理", "新增/编辑/发布脚本、启用/禁用、批量发布", "测试人员D", "1", "P0", "独立执行", "path_d"),
            ("D—运营平台\n管理（独立）", "机器人分组（运营）", "新增分组、绑定分公司、删除", "测试人员D", "0.5", "P0", "", "path_d"),
            ("D—运营平台\n管理（独立）", "机器人管理（运营）", "新增/编辑/删除、批量启用/停用、批量推送更新", "测试人员D", "1", "P0", "", "path_d"),
            ("D—运营平台\n管理（独立）", "任务列表", "查看任务详情、终止、删除、超时自动终止(12h)", "测试人员D", "0.5", "P0", "", "path_d"),
            ("D—运营平台\n管理（独立）", "日志管理", "应用/机器人组/机器人/客户端操作日志筛选与查看", "测试人员D", "0.5", "P1", "", "path_d"),
            ("D—运营平台\n管理（独立）", "客户端管理", "发布新版、设置最低兼容版本", "测试人员D", "0.5", "P0", "", "path_d"),
            ("D—运营平台\n管理（独立）", "异常模板管理", "异常分类管理、异常模板新增/编辑/删除/启用/禁用", "测试人员D", "0.5", "P0", "", "path_d"),
            ("D—运营平台\n管理（独立）", "RPA客户端", "账密登录、版本检测更新、指纹上传、任务接收与执行、结果回调、退出", "测试人员D", "1", "P0", "", "path_d"),
        ]

    # Write data rows with color fills
    row_idx = 3
    merge_start = {}
    current_phase = None

    for phase, menu, points, owner, days, priority, note, color_key in data_rows:
        values = [phase, menu, points, owner, days, priority, note]
        color = COLORS.get(color_key, COLORS["entry"])

        for col_idx, val in enumerate(values, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = Font(name="微软雅黑", bold=(col_idx == 1), size=11 if col_idx == 1 else 10)
            cell.fill = fill_color(color)
            cell.border = create_thin_border()

            if col_idx == 1:  # Phase column
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            elif col_idx in (4, 5, 6):  # Owner, Days, Priority
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:  # Menu, Points, Notes
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

        ws.row_dimensions[row_idx].height = 32

        # Track phase grouping for merge
        if phase != current_phase:
            if current_phase is not None and merge_start[current_phase] < row_idx - 1:
                ws.merge_cells(f"A{merge_start[current_phase]}:A{row_idx - 1}")
                ws.cell(row=merge_start[current_phase], column=1).alignment = Alignment(
                    horizontal="center", vertical="center", wrap_text=True
                )
            merge_start[phase] = row_idx
            current_phase = phase

        row_idx += 1

    # Final phase merge
    if current_phase and merge_start[current_phase] < row_idx - 1:
        ws.merge_cells(f"A{merge_start[current_phase]}:A{row_idx - 1}")
        ws.cell(row=merge_start[current_phase], column=1).alignment = Alignment(
            horizontal="center", vertical="center", wrap_text=True
        )

    # Freeze panes
    ws.freeze_panes = "B3"

    # ═════════════════════════════════════════════════════════════
    # SHEET 2: 工作量汇总
    # ═════════════════════════════════════════════════════════════
    ws2 = wb.create_sheet("工作量汇总")

    # Column widths
    ws2.column_dimensions["A"].width = 20
    ws2.column_dimensions["B"].width = 14
    ws2.column_dimensions["C"].width = 14
    ws2.column_dimensions["D"].width = 14
    ws2.column_dimensions["E"].width = 28

    # Title row
    ws2.merge_cells("A1:E1")
    title_cell2 = ws2["A1"]
    title_cell2.value = "工作量汇总"
    title_cell2.font = Font(name="微软雅黑", bold=True, size=14, color="FFFFFF")
    title_cell2.fill = fill_color(COLORS["header"])
    title_cell2.alignment = Alignment(horizontal="center", vertical="center")
    ws2.row_dimensions[1].height = 36

    # Header row
    headers2 = ["负责人", "模块", "计划天数", "菜单数", "备注"]
    for col_idx, header in enumerate(headers2, 1):
        cell = ws2.cell(row=2, column=col_idx, value=header)
        cell.font = Font(name="微软雅黑", bold=True, size=11, color="FFFFFF")
        cell.fill = fill_color(COLORS["header"])
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = create_thin_border()
    ws2.row_dimensions[2].height = 22

    # Summary rows
    summary_rows = [
        ("测试人员A", "公共层 + A线（办税员/票税登录）", "5.5", "9", "", "path_a"),
        ("测试人员B", "B线（发票采集 + H5 + APP）", "5.0", "4", "", "path_b"),
        ("测试人员C", "C线（零申报 + 报表申报）", "4.5", "7", "", "path_c"),
        ("测试人员D", "D线（运营平台管理）", "5.0", "8", "独立执行", "path_d"),
        ("全员", "入口准备 + 全链路闭环 + 出口", "3.0", "3", "", "entry"),
        ("合计", "", "23.0", "31", "", "entry"),
    ]

    for r_idx, (person, module, days, menus, note, color_key) in enumerate(summary_rows, 3):
        color = COLORS.get(color_key, COLORS["entry"])
        vals = [person, module, days, menus, note]

        for col_idx, val in enumerate(vals, 1):
            cell = ws2.cell(row=r_idx, column=col_idx, value=val)
            cell.font = Font(name="微软雅黑", bold=(person == "合计"), size=10)
            cell.fill = fill_color(color)
            cell.border = create_thin_border()

            if col_idx != 2:  # Not module column
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

        ws2.row_dimensions[r_idx].height = 28

    # Save
    wb.save(output_path)
    print(f"✓ Generated: {output_path}")

if __name__ == "__main__":
    output_file = "regression_test_plan.xlsx"
    config_file = None

    # Parse arguments
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--output" and i < len(sys.argv) - 1:
            output_file = sys.argv[i + 1]
        elif arg == "--config" and i < len(sys.argv) - 1:
            config_file = sys.argv[i + 1]

    # Load config if provided
    data = None
    if config_file:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            data = config.get("rows", None)

    create_xlsx(output_path=output_file, data_rows=data)
