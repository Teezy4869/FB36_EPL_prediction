# Báo Cáo Phase 1: Dữ Liệu Nền Tảng và Nhãn (Football-Data)

- **Dự án**: Dự đoán kết quả Ngoại Hạng Anh (Premier League Outcome Prediction)
- **Thư mục gốc**: `D:\PTIT\PAYT\Mini_project`
- **Thời gian thực hiện**: `2026-10-24 09:57:05 UTC`
- **Tệp đầu ra chính**: `data/cleaned/matches_base.csv`
- **Thư mục raw**: `data/raw/football_data/`

---

## 1. Tổng Quan Kết Quả Nhập Dữ Liệu

- **Tổng số mùa giải xử lý**: `8` mùa (2018/19 đến 2025/26)
- **Tổng số trận hợp lệ nhập vào `matches_base.csv`**: `3,040` trận
- **Số trận trùng lặp khóa (Date + HomeTeam + AwayTeam)**: `0` trận
- **Dòng trống (Blank lines)**: `0` dòng
- **Trận thiếu nhãn kết quả / chưa thi đấu**: `0` trận
- **Ngày thi đấu lỗi định dạng**: `0` trận

---

## 2. Thống Kê Theo Mùa Giải

| Mùa giải | Dòng dữ liệu | Trận hợp lệ | Dòng trống | Thiếu nhãn/kết quả | Số cột CSV | Phân bố H / D / A |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2018-19** | 380 | **380** | 0 | 0 | 62 | H: 181 (47.6%), D: 71 (18.7%), A: 128 (33.7%) |
| **2019-20** | 380 | **380** | 0 | 0 | 106 | H: 172 (45.3%), D: 92 (24.2%), A: 116 (30.5%) |
| **2020-21** | 380 | **380** | 0 | 0 | 106 | H: 144 (37.9%), D: 83 (21.8%), A: 153 (40.3%) |
| **2021-22** | 380 | **380** | 0 | 0 | 106 | H: 163 (42.9%), D: 88 (23.2%), A: 129 (33.9%) |
| **2022-23** | 380 | **380** | 0 | 0 | 106 | H: 184 (48.4%), D: 87 (22.9%), A: 109 (28.7%) |
| **2023-24** | 380 | **380** | 0 | 0 | 106 | H: 175 (46.1%), D: 82 (21.6%), A: 123 (32.4%) |
| **2024-25** | 380 | **380** | 0 | 0 | 120 | H: 155 (40.8%), D: 93 (24.5%), A: 132 (34.7%) |
| **2025-26** | 380 | **380** | 0 | 0 | 132 | H: 162 (42.6%), D: 104 (27.4%), A: 114 (30.0%) |

---

## 3. Phân Bố Nhãn Toàn Diện (H / D / A)

- **Tổng số trận**: `3,040`
- **Đội nhà thắng (`H`)**: `1,336` (43.95%)
- **Hòa (`D`)**: `700` (23.03%)
- **Đội khách thắng (`A`)**: `1,004` (33.03%)

> [!NOTE]
> Đặc biệt ghi nhận mùa giải **2020-21**: Số trận đội khách thắng (`A`: 153 trận, 40.3%) cao hơn đội nhà thắng (`H`: 144 trận, 37.9%). Điều này hoàn toàn khớp với thực tế lịch sử khi các trận đấu mùa 2020-21 diễn ra trên sân không có khán giả (behind closed doors) do đại dịch COVID-19 làm suy giảm lợi thế sân nhà.

---

## 4. Kiểm Tra Trùng Lặp Khóa (Duplicate Key Check)

Khóa kiểm tra: `(match_date, home_team_raw, away_team_raw)`.
- **Kết quả**: `0` trường hợp trùng lặp được phát hiện.
- Đảm bảo mỗi trận đấu trong lịch sử Premier League là một bản ghi duy nhất, không nhân đôi dòng.

---

## 5. Biến Động Cột Dữ Liệu Theo Mùa (Schema Variations)

Football-Data bổ sung và điều chỉnh các cột tỷ lệ cược nhà cái qua các thời kỳ:
- **Mùa 2018-19**: 62 cột (Gồm thống kê trận cơ bản: Sút, Phạt góc, Thẻ phạt, và các nhà cái B365, BW, IW, PS, WH, VC).
- **Mùa 2019-20 đến 2023-24**: 106 cột (Bổ sung thêm Max/Avg odds từ Betbrain/Betfair Exchange và các cột cược châu Á).
- **Mùa 2024-25**: 120 cột.
- **Mùa 2025-26**: 132 cột (Bổ sung thêm tỷ lệ cược mở cửa và dòng tiền).

**Xử lý trong Phase 1**: Đã trích xuất chính xác 9 cột nền tảng chuẩn hóa cho `data/cleaned/matches_base.csv`:
1. `season`: Mùa giải chuẩn hóa (ví dụ: `2024-25`)
2. `match_date`: Ngày thi đấu định dạng ISO `YYYY-MM-DD`
3. `home_team_raw`: Tên đội nhà theo Football-Data
4. `away_team_raw`: Tên đội khách theo Football-Data
5. `home_goals`: Bàn thắng đội nhà (integer)
6. `away_goals`: Bàn thắng đội khách (integer)
7. `result`: Nhãn kết quả `H`, `D`, hoặc `A`
8. `source_url`: URL tệp CSV gốc
9. `source_row_id`: Chỉ số dòng gốc (1-based index) để phục vụ kiểm toán nguồn gốc dữ liệu

> [!IMPORTANT]
> Không sử dụng bất kỳ thống kê nào sau trận (như số cú sút, thẻ phạt, phạt góc) làm đặc trưng ở giai đoạn này nhằm ngăn chặn triệt để nguy cơ rò rỉ dữ liệu tương lai (data leakage).

---

## 6. Danh Mục Tệp Raw & Metadata Đã Lưu

Tất cả tệp raw gốc và metadata SHA-256 đã được lưu trữ trong `data/raw/football_data/`:
- `data/raw/football_data/2018-19_E0.csv` kèm `2018-19_E0.meta.json`
- `data/raw/football_data/2019-20_E0.csv` kèm `2019-20_E0.meta.json`
- `data/raw/football_data/2020-21_E0.csv` kèm `2020-21_E0.meta.json`
- `data/raw/football_data/2021-22_E0.csv` kèm `2021-22_E0.meta.json`
- `data/raw/football_data/2022-23_E0.csv` kèm `2022-23_E0.meta.json`
- `data/raw/football_data/2023-24_E0.csv` kèm `2023-24_E0.meta.json`
- `data/raw/football_data/2024-25_E0.csv` kèm `2024-25_E0.meta.json`
- `data/raw/football_data/2025-26_E0.csv` kèm `2025-26_E0.meta.json`
