from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path


@dataclass(frozen=True)
class AttendanceRow:
    day: date
    weekday_cn: str
    work_hours: float


@dataclass(frozen=True)
class WeeklyReport:
    submit_date: date
    coverage_start: date
    coverage_end: date
    summary: str


def _parse_hhmm(value: str) -> int:
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", value.strip())
    if not m:
        raise ValueError(f"Invalid time: {value!r} (expected HH:MM)")
    hh = int(m.group(1))
    mm = int(m.group(2))
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        raise ValueError(f"Invalid time: {value!r}")
    return hh * 60 + mm


def _fmt_hhmm(minutes: int) -> str:
    # If it spills into the next day, wrap but keep display simple.
    minutes = minutes % (24 * 60)
    hh, mm = divmod(minutes, 60)
    return f"{hh:02d}:{mm:02d}"


def _load_image_cv(path: Path):
    import cv2  # type: ignore
    import numpy as np  # type: ignore

    data = path.read_bytes()
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Failed to decode image: {path}")
    return img


def _preprocess_for_ocr(img, scale: int):
    import cv2  # type: ignore

    if scale <= 1:
        return img
    return cv2.resize(img, (img.shape[1] * scale, img.shape[0] * scale), interpolation=cv2.INTER_CUBIC)


def _rapid_ocr(img):
    from rapidocr_onnxruntime import RapidOCR  # type: ignore

    ocr = RapidOCR(det_use_cuda=False, rec_use_cuda=False)
    res, _elapsed = ocr(img)
    return res or []


def _parse_hours(text: str) -> float | None:
    t = text.replace(",", ".").replace("小时", "")
    t = re.sub(r"[^0-9.\s]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    if not t:
        return None

    # "10 58" -> 10.58
    m = re.fullmatch(r"(\d{1,2})\s+(\d{1,2})", t)
    if m:
        return float(f"{m.group(1)}.{m.group(2)}")

    # "1058" -> 10.58 (common OCR error)
    if re.fullmatch(r"\d{3,4}", t) and "." not in t:
        return float(f"{t[:-2]}.{t[-2:]}")

    m = re.search(r"\d+(?:\.\d+)?", t)
    return float(m.group(0)) if m else None


def extract_attendance(
    *,
    attendance_image: Path,
    year: int,
    month: int,
    scale: int,
    debug_dir: Path | None,
) -> list[AttendanceRow]:
    import numpy as np  # type: ignore

    img = _load_image_cv(attendance_image)
    img = _preprocess_for_ocr(img, scale=scale)
    height, width = img.shape[0], img.shape[1]

    ocr_items = []
    for box, text, score in _rapid_ocr(img):
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        ocr_items.append(
            {
                "x": float(sum(xs) / 4.0),
                "y": float(sum(ys) / 4.0),
                "text": str(text),
                "score": float(score),
            }
        )

    date_re = re.compile(rf"({year}-{month:02d}-\d{{2}}).*(星期[一二三四五六日])")
    date_items = []
    hour_items = []

    for it in ocr_items:
        m = date_re.search(it["text"])
        if m:
            date_items.append({**it, "ymd": m.group(1), "weekday": m.group(2)})
            continue
        if "小时" in it["text"] and any(ch.isdigit() for ch in it["text"]):
            h = _parse_hours(it["text"])
            if h is not None:
                hour_items.append({**it, "hours": float(h)})

    # Pair each date line with the closest right-side hours on the same row.
    right_threshold = width * 0.55
    rows = []
    for d in date_items:
        candidates = [h for h in hour_items if h["x"] >= right_threshold and abs(h["y"] - d["y"]) <= 160]
        if not candidates:
            candidates = [h for h in hour_items if abs(h["y"] - d["y"]) <= 160]
        if not candidates:
            continue

        h = min(candidates, key=lambda hh: (abs(hh["y"] - d["y"]), -hh["score"]))
        day = datetime.strptime(d["ymd"], "%Y-%m-%d").date()
        rows.append(AttendanceRow(day=day, weekday_cn=str(d["weekday"]), work_hours=float(h["hours"])))

    # De-duplicate by day: keep max hours.
    by_day: dict[date, AttendanceRow] = {}
    for r in rows:
        cur = by_day.get(r.day)
        if cur is None or r.work_hours > cur.work_hours:
            by_day[r.day] = r

    out = [by_day[d] for d in sorted(by_day)]

    if debug_dir:
        debug_dir.mkdir(parents=True, exist_ok=True)
        (debug_dir / "attendance_rows.txt").write_text(
            "\n".join(f"{r.day.isoformat()} {r.weekday_cn} {r.work_hours}" for r in out), encoding="utf-8"
        )

    return out


def _normalize_header(value) -> str:
    return str(value or "").strip()


def _summarize_work_text(text: str, max_lines: int) -> str:
    raw = str(text).replace("\r", "\n")
    raw = raw.replace("，", "、").replace(",", "、")
    lines = [ln.strip() for ln in raw.split("\n") if ln.strip()]

    meaningful: list[str] = []
    for ln in lines:
        ln = re.sub(r"^[0-9一二三四五六七八九十]+[、\.]\s*", "", ln)
        ln = re.sub(r"\s+", "", ln)
        if ln in ("部门", "项目", "其他"):
            continue
        ln = re.sub(r"[；;。]+$", "", ln)
        meaningful.append(ln)
        if len(meaningful) >= max_lines:
            break

    return "、".join(meaningful).strip()


def extract_weekly_reports(
    *,
    weekly_report_xlsx: Path,
    name_filter: str | None,
    date_start: date,
    date_end: date,
    summary_lines: int,
) -> list[WeeklyReport]:
    import openpyxl  # type: ignore

    wb = openpyxl.load_workbook(weekly_report_xlsx, data_only=True)
    ws = wb[wb.sheetnames[0]]

    headers = {_normalize_header(ws.cell(1, c).value): c for c in range(1, ws.max_column + 1)}
    col_submit = headers.get("提交时间")
    col_work = headers.get("本周工作")
    col_name = headers.get("姓名")

    if not col_submit or not col_work:
        raise ValueError("Excel must include headers: 提交时间, 本周工作")

    reports: list[WeeklyReport] = []
    for r in range(2, ws.max_row + 1):
        submit = ws.cell(r, col_submit).value
        work = ws.cell(r, col_work).value
        if not submit or not work:
            continue

        if name_filter and col_name:
            nm = str(ws.cell(r, col_name).value or "").strip()
            if nm != name_filter:
                continue

        submit_dt: datetime
        if isinstance(submit, datetime):
            submit_dt = submit
        else:
            submit_dt = datetime.strptime(str(submit).strip(), "%Y-%m-%d %H:%M")

        sd = submit_dt.date()
        if not (date_start <= sd <= date_end):
            continue

        summary = _summarize_work_text(str(work), max_lines=summary_lines)
        if not summary:
            continue

        # Heuristic coverage:
        # - If submitted on Monday: cover previous Mon–Sun
        # - Otherwise: cover Mon–submit day
        if sd.weekday() == 0:
            coverage_start = sd - timedelta(days=7)
            coverage_end = sd - timedelta(days=1)
        else:
            coverage_start = sd - timedelta(days=5)
            coverage_end = sd

        reports.append(
            WeeklyReport(
                submit_date=sd,
                coverage_start=coverage_start,
                coverage_end=coverage_end,
                summary=summary,
            )
        )

    reports.sort(key=lambda x: x.submit_date)
    if not reports:
        raise ValueError("No usable weekly report rows found (check name/date range/headers).")
    return reports


def pick_summary_for_day(reports: list[WeeklyReport], day: date) -> str:
    hits = [r for r in reports if r.coverage_start <= day <= r.coverage_end]
    if hits:
        # Choose the latest report that covers this day.
        return max(hits, key=lambda r: r.submit_date).summary
    # Fallback: closest by submit_date.
    return min(reports, key=lambda r: abs((r.submit_date - day).days)).summary


def build_overtime_lines(
    *,
    attendance: list[AttendanceRow],
    reports: list[WeeklyReport] | None,
    fixed_desc: str | None,
    year: int,
    month: int,
    work_start_min: int,
    weekday_ot_start_min: int,
    saturday_all_day: bool,
    min_ot_minutes: int,
    lunch_minutes: int,
    lunch_threshold_hours: float,
) -> list[str]:
    out: list[str] = []

    for r in attendance:
        if (r.day.year, r.day.month) != (year, month):
            continue

        work_minutes = int(round(r.work_hours * 60))
        lunch = lunch_minutes if r.work_hours >= lunch_threshold_hours else 0
        end_day = work_start_min + work_minutes + lunch

        is_saturday = r.weekday_cn == "星期六"
        start_ot = work_start_min if (saturday_all_day and is_saturday) else weekday_ot_start_min

        ot_minutes = end_day - start_ot
        if ot_minutes <= 0:
            continue
        if (not is_saturday) and ot_minutes < min_ot_minutes:
            continue

        desc = fixed_desc.strip() if fixed_desc else pick_summary_for_day(reports or [], r.day)
        out.append(f"{month}月{r.day.day}日 {_fmt_hhmm(start_ot)}分至{_fmt_hhmm(end_day)}， {desc}；")

    return out


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Generate overtime application text from DingTalk screenshot + weekly report.")
    parser.add_argument("--attendance-image", type=Path, required=True, help="DingTalk attendance screenshot (.png)")
    parser.add_argument("--weekly-report", type=Path, help="Weekly report Excel (.xlsx)")
    parser.add_argument("--out", type=Path, required=True, help="Output .txt path")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument("--name", type=str, default=None, help="Filter Excel rows by 姓名 (optional)")

    parser.add_argument("--work-start", type=str, default="09:10")
    parser.add_argument("--weekday-ot-start", type=str, default="18:10")
    parser.add_argument("--saturday-all-day", action="store_true", default=True)
    parser.add_argument("--no-saturday-all-day", action="store_false", dest="saturday_all_day")
    parser.add_argument("--min-ot-minutes", type=int, default=60)

    parser.add_argument("--lunch-minutes", type=int, default=60)
    parser.add_argument("--lunch-threshold-hours", type=float, default=6.0)

    parser.add_argument("--summary-lines", type=int, default=2, help="How many lines to take from 本周工作")
    parser.add_argument("--fixed-desc", type=str, default=None, help="Use a fixed description for all overtime lines")

    parser.add_argument("--scale", type=int, default=4, help="Upscale factor before OCR")
    parser.add_argument("--debug-dir", type=Path, default=None, help="Write debug artifacts (optional)")

    args = parser.parse_args(argv)

    if args.month < 1 or args.month > 12:
        raise SystemExit("--month must be 1..12")

    if args.fixed_desc and args.weekly_report:
        # Allowed, but unnecessary; keep behavior deterministic.
        pass

    work_start_min = _parse_hhmm(args.work_start)
    weekday_ot_start_min = _parse_hhmm(args.weekday_ot_start)

    attendance = extract_attendance(
        attendance_image=args.attendance_image,
        year=args.year,
        month=args.month,
        scale=args.scale,
        debug_dir=args.debug_dir,
    )

    reports = None
    if args.fixed_desc:
        reports = None
    else:
        if not args.weekly_report:
            raise SystemExit("--weekly-report is required unless --fixed-desc is provided.")
        # Date range: month +/- a bit (weekly reports may be submitted in early next month)
        month_start = date(args.year, args.month, 1)
        month_end = (month_start.replace(day=28) + timedelta(days=10)).replace(day=1) - timedelta(days=1)
        reports = extract_weekly_reports(
            weekly_report_xlsx=args.weekly_report,
            name_filter=args.name,
            date_start=month_start,
            date_end=month_end + timedelta(days=10),
            summary_lines=args.summary_lines,
        )

    lines = build_overtime_lines(
        attendance=attendance,
        reports=reports,
        fixed_desc=args.fixed_desc,
        year=args.year,
        month=args.month,
        work_start_min=work_start_min,
        weekday_ot_start_min=weekday_ot_start_min,
        saturday_all_day=args.saturday_all_day,
        min_ot_minutes=args.min_ot_minutes,
        lunch_minutes=args.lunch_minutes,
        lunch_threshold_hours=args.lunch_threshold_hours,
    )

    args.out.write_text("\n".join(lines), encoding="utf-8")
    sys.stdout.write("\n".join(lines) + ("\n" if lines else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
