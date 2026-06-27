---
name: dingtalk-overtime-application
description: Generate monthly overtime application text (Chinese) from a DingTalk attendance screenshot (.png) plus a weekly report Excel (.xlsx). Use when asked to output formatted lines like “1月4日 18:10分至19:50， …；” with rules such as weekday overtime starting at 18:10, Saturday counting as full-day overtime, and ignoring overtime durations under 60 minutes.
---

# DingTalk Overtime Application（钉钉加班申请生成）

## Workflow

Use `scripts/generate_overtime_text.py` to extract daily work hours from the DingTalk screenshot (OCR), map each day to a short work description from the weekly report, then output the overtime application text.

### Inputs

- DingTalk attendance screenshot that lists each day as `YYYY-MM-DD（星期X）` and shows right-side `X小时` values (e.g. `*钉钉*考勤*.png`)
- Weekly report Excel that includes columns `提交时间` and `本周工作` (e.g. `*工作周报*.xlsx`)

### Setup (once)

Install dependencies:

`python -m pip install -U rapidocr-onnxruntime opencv-python-headless numpy openpyxl`

### Generate overtime text

Run (example for January 2026):

`python C:/Users/win10/.codex/skills/local/dingtalk-overtime-application/scripts/generate_overtime_text.py --attendance-image "1月加班钉钉考勤记录.png" --weekly-report "何祥-工作周报(周) (2025_11_03-2026_02_07) (1).xlsx" --year 2026 --month 1 --name "何祥" --out "1月加班申请文本.txt"`

### Common rule knobs

- `--work-start` (default `09:10`): used to infer the end time from “X小时”
- `--weekday-ot-start` (default `18:10`): Mon–Fri overtime starts from this time
- `--saturday-all-day / --no-saturday-all-day` (default: all-day): count Saturday from `--work-start`
- `--min-ot-minutes` (default `60`): ignore overtime shorter than this (not applied to Saturday)
- `--lunch-minutes` (default `60`) and `--lunch-threshold-hours` (default `6`): if daily hours ≥ threshold, add lunch to inferred end time
- `--fixed-desc` (optional): use a fixed description for every overtime line (skip Excel mapping)

### Notes

- DingTalk screenshot usually only shows total “打卡工时(小时)”, not explicit off-work time; the script infers end time from `--work-start` + hours (+ optional lunch). Adjust knobs if your HR rule differs.
- If OCR misreads some rows, try increasing `--scale` or using `--debug-dir` to inspect OCR crops and parsed rows.
