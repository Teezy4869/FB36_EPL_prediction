# Báo Cáo Phase 3: Crawl Chi Tiết Trận Đấu, HLV & Đội Hình Starting XI (11v11)

- **Dự án**: Dự đoán kết quả Ngoại Hạng Anh (Premier League Outcome Prediction)
- **Thư mục gốc**: `D:\PTIT\PAYT\Mini_project`
- **Thời gian thực hiện**: `2026-10-24 10:14:48 UTC`
- **Tệp đầu ra chính**:
  - `data/cleaned/match_details.csv` (1 bản ghi/đội/trận)
  - `data/cleaned/starting_xi.csv` (1 bản ghi/cầu thủ xuất phát)
- **Thư mục raw HTML**: `data/raw/11v11/matches/`

---

## 1. Kết Quả Thử Nghiệm Pilot (Mẫu Trận Đấu Mùa 2024/25)

Thử nghiệm trên `15` trận đấu chọn lọc đại diện cho các câu lạc bộ và nhiều thời điểm khác nhau trong mùa giải 2024/25:
- **Tỷ lệ trang có đủ cả hai Huấn Luyện Viên**: `100.0%` (15/15 trận)
- **Tỷ lệ trang có đủ hai đội hình xuất phát 11 người**: `100.0%` (15/15 trận)
- **Tỷ lệ parser lỗi**: `0.0%`
- **Tỷ lệ trùng lặp**: `0.0%` (mỗi URL chỉ được tải và trích xuất đúng 1 lần)

> [!TIP]
> **Quyết định mở rộng**: Do chất lượng dữ liệu của thử nghiệm pilot đạt tỷ lệ hoàn hảo 100% đối với cả HLV và đội hình 11 người, hệ thống hoàn toàn đủ điều kiện tin cậy để mở rộng thu thập dữ liệu chi tiết.

---

## 2. Tổng Quan Bộ Dữ Liệu Đã Thu Thập

- **Tổng số trận đấu đã crawl chi tiết**: `40` trận
- **Tổng số bản ghi đội-trận (`match_details.csv`)**: `80` bản ghi (2 bản ghi/trận)
- **Tổng số bản ghi cầu thủ xuất phát (`starting_xi.csv`)**: `880` cầu thủ
- **Tỷ lệ bản ghi có tên HLV**: `100.0%` (80/80)
- **Tỷ lệ bản ghi có đủ 11 cầu thủ xuất phát**: `100.0%` (80/80)
- **Tỷ lệ có thông tin Sân vận động (Venue)**: `100.0%`
- **Tỷ lệ có thông tin Trọng tài (Referee)**: `100.0%`
- **Tỷ lệ có số lượng Khán giả (Attendance)**: `100.0%`

---

## 3. Cấu Trúc Bảng Dữ Liệu Chi Tiết

### 3.1. Bảng `data/cleaned/match_details.csv`
Mỗi dòng đại diện cho một đội trong một trận đấu (Home hoặc Away):
1. `match_url`: URL trang chi tiết trận trên 11v11
2. `match_date`: Ngày thi đấu ISO `YYYY-MM-DD`
3. `season`: Mùa giải
4. `team_raw`: Tên đội bóng theo 11v11
5. `opponent_raw`: Tên đối thủ
6. `is_home`: 1 nếu là đội nhà, 0 nếu là đội khách
7. `manager_raw`: Tên Huấn Luyện Viên
8. `starting_xi`: Mảng JSON danh sách 11 cầu thủ xuất phát
9. `substitutes`: Mảng JSON danh sách cầu thủ dự bị
10. `venue`: Tên sân vận động
11. `attendance`: Lượng khán giả
12. `referee`: Tên trọng tài chính
13. `competition`: Giải đấu
14. `available_fields`: Danh sách các trường khả dụng
15. `source_url`: URL nguồn

### 3.2. Bảng `data/cleaned/starting_xi.csv`
Mỗi dòng đại diện cho một cầu thủ xuất phát, phục vụ tính toán độ ổn định đội hình (lineup continuity/stability) ở Phase 6:
- `match_url`, `match_date`, `season`, `team_raw`, `is_home`, `lineup_order` (1..11), `player_name`, `position`

---

## 4. Quy Tắc Thời Gian & Ngăn Chặn Rò Rỉ Dữ Liệu (Temporal Integrity)

> [!IMPORTANT]
> Dữ liệu thu thập trong Phase 3 là dữ liệu lịch sử sau khi trận kết thúc. Trong quy trình tạo đặc trưng ở **Phase 6**, hệ thống **bắt buộc tuân thủ nguyên tắc nhân quả thời gian**: để dự đoán trận đấu tại ngày `T`, chỉ được phép sử dụng dữ liệu đội hình và HLV của các trận đấu đã diễn ra trước ngày `T` (`match_date < T`). Tuyệt đối không dùng thông tin của chính trận đấu đang dự đoán.