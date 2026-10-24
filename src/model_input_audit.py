"""Phase 01/08: independently audit the fixed 12 H/D/A model inputs.

Run from any directory: python src/model_input_audit.py
No model is fitted and no validation/test score is calculated.
"""

from __future__ import annotations

import hashlib
import math
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
FEATURES = ROOT / "data/model/prematch_features.csv"
SPLITS = ROOT / "data/model/split_manifest.csv"
BASE = ROOT / "data/cleaned/matches_base.csv"
JOINED = ROOT / "data/cleaned/matches_joined.csv"
FIXTURES = ROOT / "data/cleaned/all_fixtures.csv"
ALIASES = ROOT / "data/cleaned/team_aliases.csv"
REPORT = ROOT / "reports/model_input_audit.md"

COLUMNS = [
    "home_matches_available_last_5", "away_matches_available_last_5",
    "home_points_avg_last_5", "away_points_avg_last_5",
    "home_goal_diff_last_5", "away_goal_diff_last_5",
    "home_days_since_last_match", "away_days_since_last_match",
    "home_matches_last_7_days", "away_matches_last_7_days",
    "is_promoted_home", "is_promoted_away",
]
SEASONS = [f"{y}-{str(y + 1)[-2:]}" for y in range(2018, 2026)]
SPLIT_BY_SEASON = {s: ("train" if i < 6 else "validation" if i == 6 else "test")
                   for i, s in enumerate(SEASONS)}
# The first season precedes this dataset. This is the preseason membership
# recorded in phase_06_features.py; later seasons are checked independently
# against the previous season's Premier League membership.
FIRST_SEASON_PROMOTED = {"Cardiff City", "Fulham", "Wolverhampton Wanderers"}
META = ["season", "match_date", "canonical_home", "canonical_away", "result"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def iso(value: str) -> date:
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError(f"Noncanonical ISO date: {value}")
    return parsed


def sample(items: list[str], limit: int = 5) -> str:
    return "; ".join(items[:limit]) if items else "0"


def run() -> bool:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    checks: list[tuple[str, bool, str]] = []
    issues: list[str] = []

    def check(name: str, condition: bool, evidence: str) -> None:
        checks.append((name, bool(condition), evidence))

    feat = pd.read_csv(FEATURES, dtype={"match_id": "string"}, keep_default_na=True)
    split = pd.read_csv(SPLITS, dtype={"match_id": "string"}, keep_default_na=True)
    base = pd.read_csv(BASE, dtype="string", keep_default_na=True)
    joined = pd.read_csv(JOINED, dtype={"match_id": "string"})
    fix = pd.read_csv(FIXTURES, dtype="string")
    aliases = pd.read_csv(ALIASES, dtype="string")

    required = set(COLUMNS + ["match_id"] + META)
    required_split = set(["match_id", "split_set"] + META)
    missing = sorted(required - set(feat.columns))
    missing_split = sorted(required_split - set(split.columns))
    if missing or missing_split:
        raise ValueError(f"Missing columns: features={missing}; manifest={missing_split}")

    keys_ok = (len(feat) == len(split) == 3040
               and feat.match_id.notna().all() and split.match_id.notna().all()
               and feat.match_id.is_unique and split.match_id.is_unique)
    check("Khóa và số dòng", keys_ok,
          f"features={len(feat)}, manifest={len(split)}; unique IDs={feat.match_id.nunique()}/{split.match_id.nunique()}")
    if not (feat.match_id.is_unique and split.match_id.is_unique):
        raise ValueError("Duplicate match_id prevents a meaningful 1:1 audit")
    merged = feat.merge(split, on="match_id", how="outer", validate="one_to_one",
                        indicator="join_status", suffixes=("_feat", "_split"))
    unmatched = merged.loc[merged.join_status != "both", "match_id"].tolist()
    metadata_bad = [str(row.match_id) for row in merged.itertuples()
                    if row.join_status == "both" and any(
                        getattr(row, f"{c}_feat") != getattr(row, f"{c}_split") for c in META)]
    check("Ghép 1:1 và metadata", not unmatched and not metadata_bad,
          f"unmatched={len(unmatched)} [{sample(unmatched)}]; metadata mismatch={len(metadata_bad)} [{sample(metadata_bad)}]")

    season_counts = feat.season.value_counts().to_dict()
    split_counts = split.split_set.value_counts().to_dict()
    expected_split = split.season.map(SPLIT_BY_SEASON)
    split_bad = split.loc[split.split_set.ne(expected_split), "match_id"].tolist()
    temporal_ok = False
    try:
        for frame in (feat, split):
            frame["parsed_date"] = frame.match_date.map(iso)
        dates = split.groupby("split_set").parsed_date.agg(["min", "max"])
        temporal_ok = (dates.loc["train", "max"] < dates.loc["validation", "min"]
                       and dates.loc["validation", "max"] < dates.loc["test", "min"])
    except (ValueError, KeyError) as exc:
        issues.append(f"Invalid date/split: {exc}")
    check("Mùa, split và thời gian", season_counts == {s: 380 for s in SEASONS}
          and split_counts == {"train": 2280, "validation": 380, "test": 380}
          and not split_bad and temporal_ok,
          f"seasons={season_counts}; split={split_counts}; assignment mismatch={len(split_bad)}; chronological={temporal_ok}")

    labels = feat.result.value_counts(dropna=False).to_dict()
    check("Nhãn H/D/A", feat.result.notna().all() and set(labels) == {"H", "D", "A"},
          f"label counts={labels}")

    numeric_rows = []
    parsed = {}
    for col in COLUMNS:
        raw = feat[col]
        val = pd.to_numeric(raw, errors="coerce")
        malformed = int((raw.notna() & val.isna()).sum())
        infinite = int((val.notna() & ~val.map(math.isfinite)).sum())
        missing_n = int(val.isna().sum())
        domain = pd.Series(True, index=feat.index)
        if "matches_available" in col:
            domain = val.between(0, 5) & val.mod(1).eq(0) & val.notna()
        elif "points_avg" in col:
            domain = val.isna() | val.between(0, 3)
        elif "goal_diff" in col:
            domain = val.isna() | val.mod(1).eq(0)
        elif "days_since" in col:
            domain = val.isna() | (val.ge(1) & val.mod(1).eq(0))
        elif "matches_last_7" in col:
            domain = val.notna() & val.ge(0) & val.mod(1).eq(0)
        elif "is_promoted" in col:
            domain = val.isin([0, 1])
        bad_domain = int((~domain).sum())
        numeric_rows.append((col, missing_n, malformed, infinite, bad_domain))
        parsed[col] = val
    check("Kiểu số, NaN, vô hạn và miền", all(m == 0 and i == 0 and d == 0
          for _, _, m, i, d in numeric_rows),
          "12 columns; see per-column table below")

    # Independently map Football-Data club names, then compare its natural key
    # and goals to the joined table and both model CSVs.
    def alias_map(source: str) -> dict[str, str]:
        rows = aliases[aliases.source.eq(source)]
        if rows.source_name.duplicated().any():
            raise ValueError(f"Ambiguous aliases for {source}")
        return dict(zip(rows.source_name, rows.canonical_team))

    fd_map = alias_map("football_data")
    eleven_map = alias_map("11v11")
    base["canonical_home"] = base.home_team_raw.map(fd_map)
    base["canonical_away"] = base.away_team_raw.map(fd_map)
    base_bad = []
    for c in ("home_goals", "away_goals"):
        numbers = pd.to_numeric(base[c], errors="coerce")
        base_bad.extend(base.index[numbers.isna() | ~numbers.ge(0) | ~numbers.mod(1).eq(0)].astype(str).tolist())
        base[c] = numbers
    natural = ["season", "match_date", "canonical_home", "canonical_away"]
    base_dups = int(base.duplicated(natural).sum())
    feat_dups = int(feat.duplicated(natural).sum())
    check("Khóa tự nhiên nguồn", not base_bad and not base_dups and not feat_dups
          and base.canonical_home.notna().all() and base.canonical_away.notna().all(),
          f"invalid goals={len(base_bad)}, duplicate natural keys base/features={base_dups}/{feat_dups}")
    if base_dups or feat_dups:
        raise ValueError("Duplicate natural match keys prevent score comparison")
    score_join = feat.merge(base[natural + ["home_goals", "away_goals", "result"]],
                            on=natural, how="outer", validate="one_to_one", indicator="join_status",
                            suffixes=("_feat", "_base"))
    score_bad = []
    for row in score_join.itertuples():
        if row.join_status != "both":
            score_bad.append(f"unmatched {row.match_date} {row.canonical_home}-{row.canonical_away}")
            continue
        expected = "H" if row.home_goals > row.away_goals else "A" if row.home_goals < row.away_goals else "D"
        if row.result_feat != expected or row.result_base != expected:
            score_bad.append(f"{row.match_date} {row.canonical_home}-{row.canonical_away}: {row.home_goals}-{row.away_goals}, {row.result_feat}/{row.result_base}")
    joined_bad = []
    j = joined.merge(base[natural + ["home_goals", "away_goals", "result"]],
                     on=natural, how="outer", validate="one_to_one", indicator="join_status",
                     suffixes=("_joined", "_base"))
    for row in j.itertuples():
        if row.join_status != "both" or row.home_goals_joined != row.home_goals_base or row.away_goals_joined != row.away_goals_base or row.result_joined != row.result_base:
            joined_bad.append(str(row.match_id))
    check("Tỷ số và nhãn từ matches_base", len(score_bad) == len(joined_bad) == 0,
          f"feature/base mismatches={len(score_bad)} [{sample(score_bad)}]; joined/base mismatches={len(joined_bad)} [{sample(joined_bad)}]")
    if not joined.match_id.is_unique:
        raise ValueError("Duplicate match_id in matches_joined.csv")
    source_id_join = feat.merge(joined[["match_id"] + META], on="match_id", how="outer",
                                validate="one_to_one", indicator="join_status",
                                suffixes=("_feat", "_joined"))
    source_id_bad = [str(row.match_id) for row in source_id_join.itertuples()
                     if row.join_status != "both" or any(
                         getattr(row, f"{c}_feat") != getattr(row, f"{c}_joined") for c in META)]
    check("match_id so với nguồn ghép", not source_id_bad,
          f"mismatches={len(source_id_bad)} [{sample(source_id_bad)}]")

    # Recalculate all twelve cells from raw score history, fixture dates and
    # prior-season membership. Never use the row's own score in a feature.
    pl = defaultdict(list)
    for row in base.itertuples():
        d = iso(row.match_date)
        for team, gf, ga in ((row.canonical_home, row.home_goals, row.away_goals),
                             (row.canonical_away, row.away_goals, row.home_goals)):
            pl[(row.season, team)].append((d, int(gf), int(ga),
                                          3 if gf > ga else 1 if gf == ga else 0))
    for history in pl.values():
        history.sort(key=lambda x: x[0])

    fixture_history = defaultdict(dict)
    fixture_collisions = []
    for row in fix.itertuples():
        d = iso(row.match_date)
        for raw in (row.home_team_raw, row.away_team_raw):
            team = eleven_map.get(raw, raw)
            key = (d, row.competition)  # Phase 6's documented deduplication key.
            old = fixture_history[team].get(key)
            if old and old != row.match_url:
                fixture_collisions.append(f"{team} {d} {row.competition}")
            fixture_history[team][key] = row.match_url
    check("Fixture deduplication", not fixture_collisions,
          f"different URLs sharing team/date/competition={len(fixture_collisions)} [{sample(fixture_collisions)}]")
    for team, entries in fixture_history.items():
        fixture_history[team] = sorted((d, comp, url) for (d, comp), url in entries.items())

    season_teams = {s: set(feat.loc[feat.season.eq(s), "canonical_home"])
                    | set(feat.loc[feat.season.eq(s), "canonical_away"]) for s in SEASONS}
    promoted = {SEASONS[0]: FIRST_SEASON_PROMOTED}
    for previous, current in zip(SEASONS, SEASONS[1:]):
        promoted[current] = season_teams[current] - season_teams[previous]
    promoted_ok = all(len(season_teams[s]) == 20 and len(promoted[s]) == 3 for s in SEASONS)
    check("Nguồn cờ thăng hạng", promoted_ok,
          "; ".join(f"{s}: {', '.join(sorted(promoted[s]))}" for s in SEASONS))

    mismatches = []
    traces = {}
    # Preselected by match context; cases are traced regardless of whether
    # their labels are H/D/A. No label is used to choose inputs or a design.
    cases = {
        ("2018-19", "2018-08-10", "Manchester United"): "đầu mùa",
        ("2018-19", "2018-09-22", "Liverpool"): "sau cúp/lịch dày",
        ("2018-19", "2018-09-15", "Tottenham Hotspur"): "thông thường",
    }
    values_by_id = feat.set_index("match_id")[COLUMNS]
    for row in feat.itertuples(index=False):
        d = iso(row.match_date)
        expected = {}
        context = {}
        for side, team in (("home", row.canonical_home), ("away", row.canonical_away)):
            prior_pl = [m for m in pl[(row.season, team)] if m[0] < d]
            last_five = prior_pl[-5:]
            k = len(last_five)
            expected[f"{side}_matches_available_last_5"] = k
            expected[f"{side}_points_avg_last_5"] = round(sum(m[3] for m in last_five) / k, 3) if k else math.nan
            expected[f"{side}_goal_diff_last_5"] = sum(m[1] - m[2] for m in last_five) if k else math.nan
            prior_fix = [f for f in fixture_history[team] if f[0] < d]
            last_seven = [f for f in prior_fix if 1 <= (d - f[0]).days <= 7]
            expected[f"{side}_days_since_last_match"] = (d - prior_fix[-1][0]).days if prior_fix else math.nan
            expected[f"{side}_matches_last_7_days"] = len(last_seven)
            expected[f"is_promoted_{side}"] = int(team in promoted[row.season])
            context[side] = (team, last_five, prior_fix[-1] if prior_fix else None, last_seven)
            if any(m[0] >= d for m in last_five) or any(f[0] >= d for f in last_seven):
                mismatches.append(f"{row.match_id}: nonprior source event")
        for col in COLUMNS:
            actual = values_by_id.at[row.match_id, col]
            wanted = expected[col]
            if not ((pd.isna(actual) and pd.isna(wanted)) or
                    (pd.notna(actual) and pd.notna(wanted) and math.isclose(float(actual), float(wanted), abs_tol=1e-9))):
                mismatches.append(f"{row.match_id} {col}: CSV={actual}, source={wanted}")
        case = cases.get((row.season, row.match_date, row.canonical_home))
        if case:
            traces[case] = (row, expected, context)
    check("Tính lại 12 cột trên toàn bộ trận", not mismatches,
          f"compared={len(feat) * len(COLUMNS):,} cells; mismatches={len(mismatches)} [{sample(mismatches)}]")
    check("Ba ca truy vết", len(traces) == 3,
          f"found={', '.join(traces)}")

    lines = [
        "# Kiểm toán đầu vào mô hình — Phase 01/08", "",
        "Chạy lại: `.\\.venv\\Scripts\\python.exe src/model_input_audit.py` từ thư mục dự án.",
        "Chỉ kiểm tra dữ liệu; không train và không tính metric validation/test.", "",
        "Không dùng `CHECK_5_LEAKAGE_AUDIT` hoặc `CHECK_8_JOIN_INTEGRITY` của Phase 7 làm bằng chứng: kiểm toán này tự ghép nguồn, đối chiếu tỷ số và tính lại từng ô từ sự kiện có ngày trước trận.", "",
        "## Kết quả", "", "| Kiểm tra | Kết quả | Bằng chứng |", "|---|---|---|",
    ]
    for name, passed, evidence in checks:
        lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} | {evidence.replace('|', '/')} |")
    lines += ["", "## 12 cột đã chốt", "",
              "| Cột | NaN | Sai kiểu | Vô hạn | Ngoài miền |",
              "|---|---:|---:|---:|---:|"]
    for name, missing_n, malformed, infinite, bad_domain in numeric_rows:
        lines.append(f"| `{name}` | {missing_n} | {malformed} | {infinite} | {bad_domain} |")
    lines += ["", "NaN phong độ chỉ hợp lệ khi chưa có trận Premier League trước ngày thi đấu trong mùa; NaN ngày nghỉ chỉ hợp lệ khi chưa có fixture trước đó. Phép tính lại toàn bộ ô kiểm tra chính sách này.",
              "", "## Công thức và mốc thời gian", "",
              "- Phong độ: lấy tối đa 5 trận Premier League cùng mùa có `date < match_date`; `k=min(N,5)`, điểm trung bình `round(sum(3/1/0)/k,3)`, hiệu số `sum(bàn ghi − bàn thua)`; khi `k=0`, hai giá trị sau là NaN.",
              "- Nghỉ/lịch dày: dùng fixture mọi giải có `date < match_date`; nghỉ = chênh ngày với fixture gần nhất, NaN nếu không có; mật độ = số fixture có chênh 1–7 ngày. Fixture trùng trang crawl được gộp theo đội/ngày/giải như Phase 6.",
              "- Thăng hạng: cờ theo mùa, biết trước trận. Từ 2019-20 trở đi đối chiếu đội tham gia với mùa trước; 2018-19 đối chiếu danh sách đầu mùa trong mã Phase 6.",
              "", "## Truy vết ca đại diện", ""]
    for label in ("đầu mùa", "sau cúp/lịch dày", "thông thường"):
        if label not in traces:
            continue
        row, expected, context = traces[label]
        lines.append(f"### {label}: `{row.match_id}` — {row.match_date}, {row.canonical_home} vs {row.canonical_away}")
        lines.append("")
        for side in ("home", "away"):
            team, last_five, last_fix, seven = context[side]
            recent = ", ".join(f"{m[0]} ({m[1]}-{m[2]}, {m[3]}đ)" for m in last_five) or "không có"
            seven_text = ", ".join(f"{f[0]} {f[1]}" for f in seven) or "không có"
            lines.append(f"- **{side} — {team}**: PL trước ngày trận: {recent}; fixture gần nhất: {last_fix[0]} {last_fix[1]} (`{last_fix[2]}`)" if last_fix else
                         f"- **{side} — {team}**: PL trước ngày trận: {recent}; fixture gần nhất: không có")
            lines.append(f"  - Fixture 1–7 ngày: {seven_text}. `k={expected[f'{side}_matches_available_last_5']}`, điểm TB=`{expected[f'{side}_points_avg_last_5']}`, hiệu số=`{expected[f'{side}_goal_diff_last_5']}`, nghỉ=`{expected[f'{side}_days_since_last_match']}`, số trận 7 ngày=`{expected[f'{side}_matches_last_7_days']}`, thăng hạng=`{expected[f'is_promoted_{side}']}`.")
        lines.append("")
    lines += ["## SHA-256 sau kiểm toán", "",
              f"- `data/model/prematch_features.csv`: `{sha256(FEATURES)}`",
              f"- `data/model/split_manifest.csv`: `{sha256(SPLITS)}`", "",
              "## Kết luận", ""]
    passed = all(ok for _, ok, _ in checks) and not issues
    if issues:
        lines.extend(f"- FAIL: {issue}" for issue in issues)
    lines.append("**PASS — đủ điều kiện sang Phase 02.**" if passed else
                 "**FAIL — chưa đủ điều kiện sang Phase 02; sửa pipeline nguồn và kiểm toán lại.**")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for name, ok, evidence in checks:
        print(f"{'PASS' if ok else 'FAIL'} {name}: {evidence[:180]}")
    print(f"Report: {REPORT}")
    return passed


if __name__ == "__main__":
    raise SystemExit(0 if run() else 1)
