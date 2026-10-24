# Kiểm toán đầu vào mô hình — Phase 01/08

Chạy lại: `.\.venv\Scripts\python.exe src/model_input_audit.py` từ thư mục dự án.
Chỉ kiểm tra dữ liệu; không train và không tính metric validation/test.

Không dùng `CHECK_5_LEAKAGE_AUDIT` hoặc `CHECK_8_JOIN_INTEGRITY` của Phase 7 làm bằng chứng: kiểm toán này tự ghép nguồn, đối chiếu tỷ số và tính lại từng ô từ sự kiện có ngày trước trận.

## Kết quả

| Kiểm tra | Kết quả | Bằng chứng |
|---|---|---|
| Khóa và số dòng | PASS | features=3040, manifest=3040; unique IDs=3040/3040 |
| Ghép 1:1 và metadata | PASS | unmatched=0 [0]; metadata mismatch=0 [0] |
| Mùa, split và thời gian | PASS | seasons={'2018-19': 380, '2019-20': 380, '2020-21': 380, '2021-22': 380, '2022-23': 380, '2023-24': 380, '2024-25': 380, '2025-26': 380}; split={'train': 2280, 'validation': 380, 'test': 380}; assignment mismatch=0; chronological=True |
| Nhãn H/D/A | PASS | label counts={'H': 1336, 'A': 1004, 'D': 700} |
| Kiểu số, NaN, vô hạn và miền | PASS | 12 columns; see per-column table below |
| Khóa tự nhiên nguồn | PASS | invalid goals=0, duplicate natural keys base/features=0/0 |
| Tỷ số và nhãn từ matches_base | PASS | feature/base mismatches=0 [0]; joined/base mismatches=0 [0] |
| match_id so với nguồn ghép | PASS | mismatches=0 [0] |
| Fixture deduplication | PASS | different URLs sharing team/date/competition=0 [0] |
| Nguồn cờ thăng hạng | PASS | 2018-19: Cardiff City, Fulham, Wolverhampton Wanderers; 2019-20: Aston Villa, Norwich City, Sheffield United; 2020-21: Fulham, Leeds United, West Bromwich Albion; 2021-22: Brentford, Norwich City, Watford; 2022-23: AFC Bournemouth, Fulham, Nottingham Forest; 2023-24: Burnley, Luton Town, Sheffield United; 2024-25: Ipswich Town, Leicester City, Southampton; 2025-26: Burnley, Leeds United, Sunderland |
| Tính lại 12 cột trên toàn bộ trận | PASS | compared=36,480 cells; mismatches=0 [0] |
| Ba ca truy vết | PASS | found=đầu mùa, thông thường, sau cúp/lịch dày |

## 12 cột đã chốt

| Cột | NaN | Sai kiểu | Vô hạn | Ngoài miền |
|---|---:|---:|---:|---:|
| `home_matches_available_last_5` | 0 | 0 | 0 | 0 |
| `away_matches_available_last_5` | 0 | 0 | 0 | 0 |
| `home_points_avg_last_5` | 80 | 0 | 0 | 0 |
| `away_points_avg_last_5` | 80 | 0 | 0 | 0 |
| `home_goal_diff_last_5` | 80 | 0 | 0 | 0 |
| `away_goal_diff_last_5` | 80 | 0 | 0 | 0 |
| `home_days_since_last_match` | 10 | 0 | 0 | 0 |
| `away_days_since_last_match` | 9 | 0 | 0 | 0 |
| `home_matches_last_7_days` | 0 | 0 | 0 | 0 |
| `away_matches_last_7_days` | 0 | 0 | 0 | 0 |
| `is_promoted_home` | 0 | 0 | 0 | 0 |
| `is_promoted_away` | 0 | 0 | 0 | 0 |

NaN phong độ chỉ hợp lệ khi chưa có trận Premier League trước ngày thi đấu trong mùa; NaN ngày nghỉ chỉ hợp lệ khi chưa có fixture trước đó. Phép tính lại toàn bộ ô kiểm tra chính sách này.

## Công thức và mốc thời gian

- Phong độ: lấy tối đa 5 trận Premier League cùng mùa có `date < match_date`; `k=min(N,5)`, điểm trung bình `round(sum(3/1/0)/k,3)`, hiệu số `sum(bàn ghi − bàn thua)`; khi `k=0`, hai giá trị sau là NaN.
- Nghỉ/lịch dày: dùng fixture mọi giải có `date < match_date`; nghỉ = chênh ngày với fixture gần nhất, NaN nếu không có; mật độ = số fixture có chênh 1–7 ngày. Fixture trùng trang crawl được gộp theo đội/ngày/giải như Phase 6.
- Thăng hạng: cờ theo mùa, biết trước trận. Từ 2019-20 trở đi đối chiếu đội tham gia với mùa trước; 2018-19 đối chiếu danh sách đầu mùa trong mã Phase 6.

## Truy vết ca đại diện

### đầu mùa: `PL_201819_0001` — 2018-08-10, Manchester United vs Leicester City

- **home — Manchester United**: PL trước ngày trận: không có; fixture gần nhất: không có
  - Fixture 1–7 ngày: không có. `k=0`, điểm TB=`nan`, hiệu số=`nan`, nghỉ=`nan`, số trận 7 ngày=`0`, thăng hạng=`0`.
- **away — Leicester City**: PL trước ngày trận: không có; fixture gần nhất: không có
  - Fixture 1–7 ngày: không có. `k=0`, điểm TB=`nan`, hiệu số=`nan`, nghỉ=`nan`, số trận 7 ngày=`0`, thăng hạng=`0`.

### sau cúp/lịch dày: `PL_201819_0057` — 2018-09-22, Liverpool vs Southampton

- **home — Liverpool**: PL trước ngày trận: 2018-08-12 (4-0, 3đ), 2018-08-20 (2-0, 3đ), 2018-08-25 (1-0, 3đ), 2018-09-01 (2-1, 3đ), 2018-09-15 (2-1, 3đ); fixture gần nhất: 2018-09-18 UEFA Champions League (`https://www.11v11.com/matches/liverpool-v-paris-st-germain-18-september-2018-359791/`)
  - Fixture 1–7 ngày: 2018-09-15 Premier League, 2018-09-18 UEFA Champions League. `k=5`, điểm TB=`3.0`, hiệu số=`9`, nghỉ=`4`, số trận 7 ngày=`2`, thăng hạng=`0`.
- **away — Southampton**: PL trước ngày trận: 2018-08-12 (0-0, 1đ), 2018-08-18 (1-2, 0đ), 2018-08-25 (1-2, 0đ), 2018-09-01 (2-0, 3đ), 2018-09-17 (2-2, 1đ); fixture gần nhất: 2018-09-17 Premier League (`https://www.11v11.com/matches/southampton-v-brighton-and-hove-albion-17-september-2018-359177/`)
  - Fixture 1–7 ngày: 2018-09-17 Premier League. `k=5`, điểm TB=`1.0`, hiệu số=`0`, nghỉ=`5`, số trận 7 ngày=`1`, thăng hạng=`0`.

### thông thường: `PL_201819_0046` — 2018-09-15, Tottenham Hotspur vs Liverpool

- **home — Tottenham Hotspur**: PL trước ngày trận: 2018-08-11 (2-1, 3đ), 2018-08-18 (3-1, 3đ), 2018-08-27 (3-0, 3đ), 2018-09-02 (1-2, 0đ); fixture gần nhất: 2018-09-02 Premier League (`https://www.11v11.com/matches/watford-v-tottenham-hotspur-02-september-2018-359105/`)
  - Fixture 1–7 ngày: không có. `k=4`, điểm TB=`2.25`, hiệu số=`5`, nghỉ=`13`, số trận 7 ngày=`0`, thăng hạng=`0`.
- **away — Liverpool**: PL trước ngày trận: 2018-08-12 (4-0, 3đ), 2018-08-20 (2-0, 3đ), 2018-08-25 (1-0, 3đ), 2018-09-01 (2-1, 3đ); fixture gần nhất: 2018-09-01 Premier League (`https://www.11v11.com/matches/leicester-city-v-liverpool-01-september-2018-359063/`)
  - Fixture 1–7 ngày: không có. `k=4`, điểm TB=`3.0`, hiệu số=`8`, nghỉ=`14`, số trận 7 ngày=`0`, thăng hạng=`0`.

## SHA-256 sau kiểm toán

- `data/model/prematch_features.csv`: `44fb34abebf74bdcdfd30b9ab8c0dd04f2351da503025bee532311f301203083`
- `data/model/split_manifest.csv`: `3b9efe26c0051d86a8f350355985478c702aad7c410228a34fe6ad1ed4851f6a`

## Kết luận

**PASS — đủ điều kiện sang Phase 02.**
