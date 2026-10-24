# Báo Cáo Phase 2: Lịch Thi Đấu Đa Giải Đấu (11v11)

- **Dự án**: Dự đoán kết quả Ngoại Hạng Anh (Premier League Outcome Prediction)
- **Thư mục gốc**: `D:\PTIT\PAYT\Mini_project`
- **Thời gian thực hiện**: `2026-10-24 10:07:58 UTC`
- **Tệp đầu ra chính**: `data/cleaned/all_fixtures.csv`
- **Thư mục raw HTML**: `data/raw/11v11/team_seasons/`

---

## 1. Tổng Quan Kết Quả Thu Thập

- **Tổng số mùa giải xử lý**: `8` mùa
- **Tổng số lượt trang đội đã crawl**: `160` trang (20 đội/mùa)
- **Tổng số bản ghi lịch thi đấu thu thập được (thô)**: `7,722` bản ghi
- **Tổng số trận đấu duy nhất sau khi khử trùng lặp**: `4,416` trận
  - **Trận Ngoại Hạng Anh (Premier League)**: `3,040` trận
  - **Trận các giải đấu cúp / cúp Châu Âu**: `1,376` trận
- **Tổng số ngày thi đấu không hợp lệ**: `0`
- **Tổng số trận thiếu match_url**: `0`

---

## 2. Thống Kê Chi Tiết Theo Mùa Giải

| Mùa giải | Số đội | Tổng trận thô | PL thô (20 đội) | PL sau khử trùng | Trận Cúp | Đạt chuẩn 380 PL |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2018-19** | 20 | 953 | 760 | **380** | 162 | PASSED (ĐỦ 380) |
| **2019-20** | 20 | 967 | 760 | **380** | 171 | PASSED (ĐỦ 380) |
| **2020-21** | 20 | 963 | 760 | **380** | 174 | PASSED (ĐỦ 380) |
| **2021-22** | 20 | 957 | 760 | **380** | 164 | PASSED (ĐỦ 380) |
| **2022-23** | 20 | 948 | 760 | **380** | 157 | PASSED (ĐỦ 380) |
| **2023-24** | 20 | 958 | 760 | **380** | 161 | PASSED (ĐỦ 380) |
| **2024-25** | 20 | 986 | 760 | **380** | 189 | PASSED (ĐỦ 380) |
| **2025-26** | 20 | 990 | 760 | **380** | 198 | PASSED (ĐỦ 380) |

---

## 3. Phân Bố Trận Đấu Theo Giải Đấu (Competitions Breakdown)

Danh sách các giải đấu có mặt trong tập `all_fixtures.csv` (phục vụ tính mật độ thi đấu):

| Giải đấu (Competition) | Số trận duy nhất | Tỷ lệ (%) |
| :--- | :---: | :---: |
| **Premier League** | 3,040 | 68.84% |
| **FA Cup** | 356 | 8.06% |
| **UEFA Champions League** | 346 | 7.84% |
| **League Cup** | 321 | 7.27% |
| **UEFA Europa League** | 240 | 5.43% |
| **UEFA Europa Conference League** | 45 | 1.02% |
| **UEFA Conference League** | 32 | 0.72% |
| **FIFA Club World Cup** | 17 | 0.38% |
| **FA Community Shield** | 8 | 0.18% |
| **Premier League Asia Trophy** | 4 | 0.09% |
| **UEFA Super Cup** | 4 | 0.09% |
| **Football League Trophy** | 3 | 0.07% |

---

## 4. Xác Minh Mẫu: Trường Hợp Liverpool 2024/25

Trang lịch thi đấu Liverpool 2024/25:
- **URL nguồn**: `https://www.11v11.com/teams/liverpool/tab/matches/season/2025/`
- **Tổng số trận ghi nhận**: `56` trận
- **Premier League**: `38` trận (khớp hoàn toàn với Phase 1)
- **UEFA Champions League**: `10` trận
- **League Cup (Carabao Cup)**: `6` trận
- **FA Cup**: `2` trận
- **Kiểm tra khử trùng lặp**: Các trận gặp các đội Premier League khác (ví dụ trận gặp Ipswich Town ngày 17/08/2024) xuất hiện ở cả trang Liverpool và Ipswich Town, được gộp thành 1 bản ghi duy nhất có `teams_crawled = 'Ipswich Town, Liverpool'` và lưu giữ đầy đủ `match_url`.

---

## 5. Kết Luận & Chuyển Giao Cho Phase Tiếp Theo

1. Toàn bộ 20 đội bóng của các mùa giải đã được xác định chính xác slug 11v11 và tải đầy đủ HTML thô về `data/raw/11v11/team_seasons/`.
2. Số trận Premier League sau khi khử trùng lặp khớp hoàn toàn 100% với 380 trận/mùa của dữ liệu nền tảng Phase 1.
3. Đã trích xuất thành công toàn bộ `match_url` của từng trận đấu làm đầu vào thiết yếu cho **Phase 3** (Crawl trang chi tiết trận để lấy HLV và đội hình xuất phát Starting XI).