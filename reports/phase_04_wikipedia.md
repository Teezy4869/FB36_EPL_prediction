# Báo Cáo Phase 4: Crawl Dữ Liệu Đội Bóng & Biến Động HLV Từ Wikipedia

- **Dự án**: Dự đoán kết quả Ngoại Hạng Anh (Premier League Outcome Prediction)
- **Thư mục gốc**: `D:\PTIT\PAYT\Mini_project`
- **Thời gian thực hiện**: `2026-10-24 10:20:02 UTC`
- **Tệp đầu ra chính**:
  - `data/cleaned/team_seasons.csv` (Sân vận động, sức chứa, địa điểm)
  - `data/cleaned/manager_changes.csv` (Lịch sử biến động HLV trong mùa)
- **Thư mục raw HTML**: `data/raw/wikipedia/`

---

## 1. Kết Quả Thử Nghiệm Pilot Mùa Giải 2024/25

Trang Wikipedia: `https://en.wikipedia.org/wiki/2024%E2%80%9325_Premier_League`:
- **Revision ID (oldid)**: `1380532736`
- **Bảng Sân Vận Động**: Xác nhận **đủ 20 đội bóng** của Ngoại Hạng Anh mùa 2024/25.
- **Bảng Biến Động HLV**: Trích xuất thành công các sự kiện thay tướng cả **trước mùa giải** (Pre-season: Roberto De Zerbi, Jürgen Klopp, David Moyes, Mauricio Pochettino, Enzo Maresca) và **giữa mùa giải** (Erik ten Hag $\rightarrow$ Ruud van Nistelrooy $\rightarrow$ Ruben Amorim, Steve Cooper, Gary O'Neil, Russell Martin).
- **Xử lý `rowspan` / `colspan`**: Đã sử dụng bộ mở rộng ô 2 chiều (2D grid parser) để ngăn ngừa triệt để lỗi lệch cột khi Wikipedia gộp ô `Pre-season` hoặc gộp tên câu lạc bộ thay đổi HLV nhiều lần.

> [!TIP]
> Thử nghiệm pilot 2024/25 đạt chuẩn tuyệt đối, cho phép mở rộng thu thập cho toàn bộ 8 mùa giải từ 2018/19 đến 2025/26.

---

## 2. Thống Kê Tổng Hợp Qua 8 Mùa Giải (2018/19 – 2025/26)

| Mùa giải | Revision ID (oldid) | Số bản ghi Sân đấu | Biến động HLV | Pre-season HLV | In-season HLV |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **2018-19** | `1376994818` | 21 (Gồm Wembley & Tottenham Stadium) | 10 | 4 | 6 |
| **2019-20** | `1378847413` | 20 | 10 | 3 | 7 |
| **2020-21** | `1376692557` | 20 | 4 | 0 | 4 |
| **2021-22** | `1376972129` | 20 | 17 | 4 | 13 |
| **2022-23** | `1376677138` | 20 | 22 | 1 | 21 |
| **2023-24** | `1377546063` | 20 | 7 | 4 | 3 |
| **2024-25** | `1380532736` | 20 | 16 | 5 | 11 |
| **2025-26** | `1380557932` | 20 | 13 | 2 | 11 |

- **Tổng số bản ghi sân đấu thu thập được**: `161` bản ghi
- **Tổng số sự kiện thay đổi HLV được ghi nhận**: `99` sự kiện
- **Số giá trị sức chứa (capacity) bị thiếu**: `0`

---

## 3. Đối Chiếu Danh Xưng Đội Bóng (Wikipedia vs Football-Data Phase 1)

Do Wikipedia sử dụng tên đầy đủ mang tính bách khoa trong khi Football-Data sử dụng tên thương mại/rút gọn, bảng dưới đây liệt kê các trường hợp danh xưng khác biệt cần thiết lập alias trong Phase 5:

| Tên trên Wikipedia | Tên trên Football-Data (Phase 1) | Ghi chú chuẩn hóa |
| :--- | :--- | :--- |
| `Brighton & Hove Albion` | `Brighton` | Tên đầy đủ vs Tên rút gọn |
| `Manchester United` | `Man United` | Tên đầy đủ vs Tên rút gọn |
| `Manchester City` | `Man City` | Tên đầy đủ vs Tên rút gọn |
| `Newcastle United` | `Newcastle` | Tên đầy đủ vs Tên rút gọn |
| `Nottingham Forest` | `Nott'm Forest` | Ký tự viết tắt apostrophe |
| `Tottenham Hotspur` | `Tottenham` | Bỏ tiếp vĩ ngữ Hotspur |
| `West Ham United` | `West Ham` | Bỏ tiếp vĩ ngữ United |
| `Wolverhampton Wanderers` | `Wolves` | Biệt danh chính thức |
| `AFC Bournemouth` | `Bournemouth` | Bỏ tiền tố AFC |
| `Leicester City` | `Leicester` | Bỏ tiếp vĩ ngữ City |
| `Ipswich Town` | `Ipswich` | Bỏ tiếp vĩ ngữ Town |
| `Leeds United` | `Leeds` | Bỏ tiếp vĩ ngữ United |
| `Cardiff City` | `Cardiff` | Bỏ tiếp vĩ ngữ City |
| `Huddersfield Town` | `Huddersfield` | Bỏ tiếp vĩ ngữ Town |
| `Norwich City` | `Norwich` | Bỏ tiếp vĩ ngữ City |
| `Luton Town` | `Luton` | Bỏ tiếp vĩ ngữ Town |

---

## 4. Kiểm Toán Nguồn Gốc & Quy Tắc Thời Gian (Temporal Causality)

1. **Tái lập dữ liệu (Reproducibility)**: Mỗi mùa giải đều lưu trữ kèm `revision_id` cụ thể của Wikimedia Foundation. Bất kể các sửa đổi trong tương lai trên Wikipedia, dữ liệu tải về trong thư mục `data/raw/wikipedia/` được cố định và bảo toàn nguyên vẹn.
2. **Quy tắc ngăn rò rỉ dữ liệu (No Data Leakage)**: Dữ liệu biến động HLV trong `manager_changes.csv` chứa `date_of_vacancy` và `date_of_appointment`. Ở **Phase 6**, khi tạo đặc trưng số ngày kể từ khi HLV mới được bổ nhiệm, hệ thống chỉ kích hoạt nếu `date_of_appointment < match_date`. Tuyệt đối không dùng thông tin thay tướng sau ngày diễn ra trận đấu.