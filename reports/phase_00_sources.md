# Báo Cáo Phase 0: Cấu Trúc Dự Án và Xác Minh Nguồn Dữ Liệu

- **Dự án**: Dự đoán kết quả Ngoại Hạng Anh (Premier League Match Outcome Prediction)
- **Thư mục gốc**: `D:\PTIT\PAYT\Mini_project`
- **Thời gian kiểm tra**: `2026-10-24 09:49:40 UTC`
- **Môi trường**: Python 3.12 (môi trường ảo `.venv` nội bộ dự án)
- **Bộ tải dữ liệu**: `PoliteFetcher` (tự định danh User-Agent, tôn trọng robots.txt, rate limit 1.5s/domain, lưu cache đĩa, xử lý 429 backoff / 403 stop, không dùng proxy).

---

## 1. Bảng Tổng Hợp Kiểm Tra Nguồn Dữ Liệu

| Nguồn | Loại dữ liệu | robots.txt | HTTP Status | Content-Type | Quyết định sử dụng |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Football-Data** | CSV (Nền tảng & kết quả trận) | Cho phép (`User-agent: *`) | `200 OK` | `text/csv` | **CHẤP NHẬN** (Phase 1) |
| **11v11** | HTML (Lịch thi đấu & Chi tiết trận) | Cho phép (`/teams/`, `/matches/`) | `200 OK` | `text/html; charset=UTF-8` | **CHẤP NHẬN** (Phase 2 & 3) |
| **Wikipedia** | HTML (Sân vận động, thay đổi HLV) | Cho phép (`/wiki/`) | `200 OK` | `text/html; charset=UTF-8` | **CHẤP NHẬN** (Phase 4) |
| **Understat** | Thống kê nâng cao (xG) | **Chặn hoàn toàn (`Disallow: /`)** | `200 OK` (robots) | `text/plain` | **LOẠI BỎ** (Ethical scraping) |

---

## 2. Chi Tiết Xác Minh Từng Nguồn

### 2.1. Football-Data (`https://www.football-data.co.uk`)
- **Vai trò**: Cung cấp dữ liệu kết quả nền, tỷ số, bàn thắng, nhãn trận đấu (`FTR: H/D/A`), thống kê trận (sút, phạt góc, thẻ phạt) và tỷ lệ cược tham khảo cho các mùa giải 2018/19 đến 2025/26.
- **robots.txt**: `https://www.football-data.co.uk/robots.txt`
  - HTTP Status: `200`
  - Nội dung: Cho phép tổng quát `User-agent: *`, `Disallow:`. Có chặn riêng các bot đào tạo AI lớn (GPTBot, ClaudeBot, PerplexityBot).
  - Tuân thủ của dự án: Định danh User-Agent giáo dục hợp lệ, truy cập được cho phép.
- **Kiểm tra mẫu (Mùa 2024/25 - Mã E0)**:
  - URL kiểm tra: `https://www.football-data.co.uk/mmz4281/2425/E0.csv`
  - URL cuối cùng: `https://football-data.co.uk/mmz4281/2425/E0.csv`
  - HTTP Status: `200`
  - Content-Type: `text/csv`
  - Tổng số trận đã hoàn tất: `380` trận (đủ trọn vẹn 380 trận của một mùa giải Ngoại Hạng Anh).
  - Các trường quan sát được (120 cột):
    `Div`, `Date`, `Time`, `HomeTeam`, `AwayTeam`, `FTHG`, `FTAG`, `FTR`, `HTHG`, `HTAG`, `HTR`, `Referee`, `HS`, `AS`, `HST`...
  - Mẫu dữ liệu trận đầu tiên: `{'Div': 'E0', 'Date': '16/08/2024', 'Time': '20:00', 'HomeTeam': 'Man United', 'AwayTeam': 'Fulham', 'FTHG': '1', 'FTAG': '0', 'FTR': 'H'}`
- **Hạn chế & Lưu ý**: Tệp dữ liệu là tệp tĩnh cập nhật theo kỳ. Cần chuẩn hóa tên đội (Phase 5) vì Football-Data sử dụng tên rút gọn (ví dụ `Man United`, `Nott'm Forest`).

### 2.2. 11v11 (`https://www.11v11.com`)
- **Vai trò**: Cung cấp lịch thi đấu đa giải đấu (Premier League, FA Cup, League Cup, Champions League) để tính mật độ thi đấu (Phase 2) và trang chi tiết trận để lấy HLV và đội hình xuất phát Starting XI (Phase 3).
- **robots.txt**: `https://www.11v11.com/robots.txt`
  - HTTP Status: `200`
  - Quy tắc: Cho phép thu thập các đường dẫn `/teams/` và `/matches/`. Chỉ cấm `/plugins/feedback.php`, `/tags/`, `/forums/`, `/404.php`.
- **Kiểm tra mẫu 1 (Lịch thi đấu Liverpool 2024/25)**:
  - URL: `https://www.11v11.com/teams/liverpool/tab/matches/season/2025/`
  - HTTP Status: `200`
  - Bảng lịch thi đấu gồm các cột: `Date`, `Match`, `Result`, `Score`, `Competition`
  - Số liên kết trận đấu trích xuất được từ trang đội: `56` liên kết (bao gồm cả Ngoại Hạng Anh và các giải đấu cúp).
- **Kiểm tra mẫu 2 (Chi tiết trận đấu Ipswich Town v Liverpool, 17/08/2024)**:
  - URL: `https://www.11v11.com/matches/ipswich-town-v-liverpool-17-august-2024-384855/`
  - HTTP Status: `200`
  - Tiêu đề: `Ipswich Town v Liverpool, 17 August 2024 - 11v11 match report`
  - Các trường dữ liệu nhận diện thành công:
    - Metadata trận: `Score` (0-2), `Referee` (Tim Robinson), `Competition` (Premier League), `Venue` (Portman Road), `Attendance` (30,014), `Kick-off` (12.30pm).
    - HLV hai đội: `Kieran McKenna` (Ipswich Town), `Arne Slot` (Liverpool).
    - Đội hình xuất phát (Starting Lineup): Danh sách 11 cầu thủ xuất phát của cả 2 đội kèm vị trí (Goalkeeper, Defender, Midfielder, Forward).
    - Dữ liệu phụ: Cầu thủ thay người (Substitutions), thẻ phạt (Cards), danh sách dự bị (On the bench), bình luận trận đấu (Comments).
- **Hạn chế & Lưu ý**: Máy chủ yêu cầu tốc độ vừa phải. Áp dụng giới hạn tối thiểu 1.5s giữa các lượt request; lưu cache đĩa toàn bộ HTML tải về để tránh lặp request khi 1 trận xuất hiện trên trang của cả hai đội.

### 2.3. Wikipedia (`https://en.wikipedia.org`)
- **Vai trò**: Cung cấp thông tin sân vận động, sức chứa (stadium capacity) và bảng ghi nhận các đợt thay đổi HLV trong mùa giải (managerial changes) phục vụ tạo đặc trưng số ngày/số trận kể từ khi bổ nhiệm HLV (Phase 4).
- **robots.txt**: `https://en.wikipedia.org/robots.txt`
  - HTTP Status: `200`
  - Quy tắc: Cho phép thu thập các trang bài viết bách khoa `/wiki/`. Yêu cầu User-Agent tuân thủ chính sách Wikimedia Foundation (chỉ rõ dự án và thông tin liên hệ).
- **Kiểm tra mẫu (Premier League 2024–25)**:
  - URL: `https://en.wikipedia.org/wiki/2024%E2%80%9325_Premier_League`
  - HTTP Status: `200`
  - Tiêu đề trang: `2024–25 Premier League - Wikipedia`
  - Các bảng cấu trúc nhận diện được:
    - Bảng Sân vận động & Sức chứa: `Team`, `Location`, `Stadium`, `Capacity[28]`
    - Bảng Thay đổi Huấn Luyện Viên: `Team`, `Outgoing manager`, `Manner of departure`, `Date of vacancy`, `Position in the table`, `Incoming manager`, `Date of appointment`
- **Hạn chế & Lưu ý**: Chỉ crawl một lần cho mỗi mùa giải, lưu cache đĩa HTML; khi trích xuất bảng thay đổi HLV cần kiểm tra ngữ cảnh tiêu đề bảng thay vì dựa vào chỉ số bảng cố định do cấu trúc bài viết có thể chênh lệch giữa các mùa.

### 2.4. Understat (`https://understat.com`) — Nguồn Loại Bỏ
- **robots.txt**: `https://understat.com/robots.txt`
- **Nội dung robots.txt**:
  ```text
User-agent: *
Disallow: /
  ```
- **Quyết định**: **EXCLUDED (LOẠI BỎ KHỎI DỰ ÁN)**
- **Lý do chi tiết**:
  https://understat.com/robots.txt cấu hình 'User-agent: * Disallow: /'. Toàn bộ bot/crawler tự động đều bị cấm truy cập toàn trang. Nhằm tuân thủ tuyệt đối chuẩn mực thu thập dữ liệu có đạo đức, tôn trọng điều khoản dịch vụ và chính sách robots.txt của máy chủ, dự án quyết định loại bỏ Understat khỏi danh sách nguồn dữ liệu và không thực hiện bất kỳ lệnh crawl/fetch dữ liệu nào đối với trang này.

---

## 3. Kiến Trúc Bộ Tải Dữ Liệu (`src/utils/fetcher.py`)

Bộ tải `PoliteFetcher` được thiết kế phục vụ xuyên suốt từ Phase 0 đến Phase 4 với các tiêu chuẩn kỹ thuật dữ liệu nghiêm ngặt:
1. **Nhận diện User-Agent**: `PremierLeaguePredictor/0.1 (DataEngineeringEducationalProject; Contact: student@ptit.edu.vn)`.
2. **Cơ chế Cache đĩa**: Mọi phản hồi HTTP thành công được băm SHA-256 URL và lưu trữ tại `data/raw/cache/` (nội dung nhị phân/văn bản + tệp metadata JSON ghi nhận URL cuối, mã trạng thái, SHA-256 nội dung, thời điểm tải UTC). Khi chạy lại, dữ liệu được nạp từ cache, không gọi mạng thừa thãi.
3. **Giới hạn tốc độ (Rate Limiting)**: Đo khoảng cách thời gian giữa các request trên từng tên miền (`netloc`), tự động ngủ đủ 1.5s.
4. **Kiểm tra robots.txt**: Tích hợp `urllib.robotparser.RobotFileParser` để tự động kiểm tra quyền truy cập trước khi thực hiện request.
5. **Xử lý 429 & 403**:
   - Gặp HTTP 429: Đọc header `Retry-After` và áp dụng bounded exponential backoff tối đa 2 lần thử lại; nếu tiếp tục bị 429 thì dừng an toàn và ném ngoại lệ `RateLimitExceededError`.
   - Gặp HTTP 403: Dừng ngay lập tức, ghi log nghiêm trọng, ném `ForbiddenAccessError`. Tuyệt đối không thử lại bằng proxy hay hoán đổi User-Agent để vượt chặn.

---

## 4. Xác Minh và Giới Hạn Phạm Vi (Smoke Test Scope)

### 4.1. Điều gì đã xác minh (Verified in Phase 0)
1. Cấu trúc thư mục dự án chuẩn hóa: `src/`, `src/utils/`, `data/raw/`, `data/cleaned/`, `data/model/`, `reports/`, `logs/` đã được thiết lập đúng quy cách với đường dẫn suy biến tương đối từ gốc dự án (`PROJECT_ROOT`).
2. Cấu hình tập trung `src/config.py` đã định nghĩa đầy đủ 8 mùa giải mục tiêu (2018/19 đến 2025/26), cùng danh mục đường dẫn chuẩn.
3. Bộ thư viện phụ thuộc đã cài đặt hoàn tất vào môi trường ảo `.venv` nội bộ và lưu trữ tại `requirements.txt`.
4. Quy tắc robots.txt và khả năng truy cập HTTP 200 OK của cả 3 nguồn chính (Football-Data, 11v11, Wikipedia) đã được xác minh thực tế.
5. Kiểm tra mẫu từng cấu trúc nội dung:
   - File CSV Football-Data E0 2024/25 có đủ 380 trận và đầy đủ các trường kết quả/tỷ lệ cược.
   - Trang lịch Liverpool 2024/25 có đầy đủ các cột Date, Match, Result, Score, Competition và các liên kết trận đấu.
   - Trang chi tiết trận đấu 11v11 cung cấp đầy đủ tên HLV và 11 cầu thủ xuất phát của cả 2 đội.
   - Trang Wikipedia mùa 2024–25 có đầy đủ bảng thông tin sân vận động/sức chứa và bảng thay đổi HLV.
6. Xác minh và lập tài liệu rõ ràng về việc loại bỏ Understat do chính sách robots `Disallow: /`.
7. Bộ tải `PoliteFetcher` hoạt động tốt với cache đĩa, rate limiting và xử lý lỗi an toàn.

### 4.2. Điều gì chưa xác minh trong Phase 0 (Out of Scope for Phase 0)
1. **Chưa crawl hàng loạt**: Chưa tải toàn bộ các mùa 2018/19–2025/26 (sẽ thực hiện theo từng phase: Phase 1 cho Football-Data, Phase 2–3 cho 11v11, Phase 4 cho Wikipedia).
2. **Chưa chuẩn hóa tên đội**: Chưa xây dựng bảng ánh xạ danh xưng (team aliases) giữa các nguồn (sẽ thực hiện tại Phase 5).
3. **Chưa ghép nối dữ liệu (Join)**: Chưa ghép các nguồn lại với nhau (thuộc phạm vi Phase 5).
4. **Chưa tạo đặc trưng (Feature Engineering)**: Chưa tính toán rolling metrics, khoảng cách ngày thi đấu (thuộc phạm vi Phase 6).
5. **Chưa kiểm định bộ dữ liệu & huấn luyện mô hình**: Thuộc phạm vi Phase 7.
