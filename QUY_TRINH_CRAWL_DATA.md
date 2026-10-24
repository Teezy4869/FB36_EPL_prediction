# Quy trình thu thập dữ liệu Premier League

*Tư liệu cho slide thuyết trình — cập nhật 24/10/2026. Nội dung dưới đây dựa trên các tệp dữ liệu, mã nguồn và báo cáo hiện có trong dự án.*

## 1. Tổng quan vấn đề

**Bài toán:** dự đoán kết quả một trận Premier League trước giờ bóng lăn bằng RandomForestClassifier, với ba nhãn: H = đội nhà thắng, D = hòa, A = đội khách thắng.

**Đơn vị quan sát:** một trận đấu. Bộ dữ liệu bao phủ 8 mùa đã hoàn tất, từ 2018/19 đến 2025/26. Mỗi mùa có 380 trận, tổng cộng 3.040 trận.

**Dữ liệu cần thiết:**

| Nhóm | Trường chính | Vai trò |
|---|---|---|
| Kết quả Premier League | Ngày, đội nhà, đội khách, số bàn, H/D/A | Nhãn và lịch sử phong độ |
| Lịch thi đấu mọi giải | Ngày, đối thủ, giải đấu, tỷ số, liên kết trận | Số ngày nghỉ, mật độ trận, trận cúp |
| Chi tiết trận lịch sử | HLV, đội hình xuất phát, sân, trọng tài | Biến động HLV và độ ổn định đội hình |
| Thông tin theo mùa | Đội, sân, sức chứa, ngày thay HLV | Bối cảnh sân nhà và HLV |
| Đặc trưng trước trận | Phong độ 5 trận, số ngày nghỉ, số trận 7/14 ngày, chênh lệch hai đội | Đầu vào của mô hình |

**Nguồn:** [Football-Data](https://www.football-data.co.uk/englandm.php) cung cấp CSV kết quả; [11v11](https://www.11v11.com/) và [Wikipedia](https://en.wikipedia.org/wiki/2024%E2%80%9325_Premier_League) là hai nguồn được crawl từ HTML. Football-Data là bước tải dữ liệu nền, không được trình bày là crawl HTML. Understat được loại khỏi phạm vi vì [robots.txt](https://understat.com/robots.txt) ghi Disallow: /.

**Luồng tổng quát:** kiểm tra nguồn → tải CSV nền → crawl lịch 11v11 → crawl chi tiết trận 11v11 → crawl Wikipedia → chuẩn hóa và ghép → tạo đặc trưng trước trận → kiểm định.

## 2. Quy trình tuần tự theo giai đoạn

### Phase 0 — Khởi tạo và xác minh nguồn

**Thực hiện:** kiểm tra robots.txt, phản hồi HTTP và cấu trúc mẫu của Football-Data, 11v11, Wikipedia; thử một CSV, một trang lịch, một trang trận và một trang Wikipedia. Tạo cấu trúc dự án, bộ tải dùng lại và môi trường Python.

**Kỹ thuật:** Robots Exclusion Protocol; HTTP GET; User-Agent nhận diện dự án; timeout; giới hạn tốc độ 1,5 giây trên mỗi miền; cache đĩa theo SHA-256 URL; lưu metadata; gặp HTTP 429 thì backoff có giới hạn, gặp 403 thì dừng. Không dùng proxy hoặc đổi danh tính để vượt chặn. Bộ tải nằm tại [src/utils/fetcher.py](src/utils/fetcher.py).

**Kết quả:** ba nguồn chính truy cập được và có cấu trúc phù hợp; Understat bị loại. Báo cáo chi tiết: [phase_00_sources.md](reports/phase_00_sources.md).

### Phase 1 — Thu thập dữ liệu nền Football-Data

**Thực hiện:** tải tệp E0.csv cho từng mùa 2018/19–2025/26; giữ bản CSV gốc cùng URL, thời điểm tải và SHA-256; chuyển ngày và nhãn về dạng thống nhất.

**Kỹ thuật:** tải CSV qua HTTP; xử lý encoding và khác biệt số cột giữa các mùa; kiểm tra dòng trống, nhãn thiếu và khóa trận trùng; giữ provenance đến từng dòng nguồn.

**Kết quả:** [matches_base.csv](data/cleaned/matches_base.csv) có **3.040 dòng × 9 cột**, đủ 380 trận/mùa, không có trận thiếu nhãn hoặc trùng khóa. CSV gốc thay đổi từ 62 đến 132 cột tùy mùa; chỉ giữ các trường cần thiết cho bảng nền. Phân bố nhãn: H = 1.336, D = 700, A = 1.004. Báo cáo: [phase_01_base.md](reports/phase_01_base.md).

### Phase 2 — Crawl lịch thi đấu đa giải từ 11v11

**Thực hiện:** bắt đầu từ 20 đội của mỗi mùa; mở trang lịch đội–mùa; trích ngày, hai đội, giải đấu, tỷ số và URL trang trận. Chỉ đi theo các liên kết thuộc phạm vi đội/mùa/trận đã chọn.

**Kỹ thuật:** focused crawling theo danh sách hạt giống; HTML parsing bằng BeautifulSoup; link traversal từ trang đội sang trang trận; cache HTML; giới hạn tốc độ; loại trùng khi một trận xuất hiện trên trang cả hai đội. Phạm vi xác định và loại trùng giúp giảm nguy cơ spider trap; dự án không sử dụng bộ quét web không giới hạn hoặc multithreading.

**Kết quả:** đã crawl **160 trang đội–mùa**, trích **7.722 bản ghi thô**, sau khử trùng còn **4.416 trận duy nhất**: 3.040 Premier League và 1.376 trận ở giải khác. Mỗi mùa có đúng 380 trận Premier League. Bảng đầu ra [all_fixtures.csv](data/cleaned/all_fixtures.csv) có **4.416 dòng × 10 cột**. Báo cáo: [phase_02_fixtures.md](reports/phase_02_fixtures.md).

### Phase 3 — Crawl trang chi tiết trận từ 11v11

**Thực hiện:** theo URL trận từ Phase 2; lấy HLV, danh sách 11 cầu thủ đá chính của mỗi đội và metadata trận. Trước khi mở rộng, thử pilot 15 trận thuộc nhiều đội và thời điểm.

**Kỹ thuật:** HTML parsing theo từng khối đội nhà/đội khách; tránh đếm hai lần các khối HTML lặp; dedup URL; batch, checkpoint và resume; ghi trường thiếu thay vì suy đoán. Dữ liệu đội hình của chính trận chỉ được dùng như lịch sử cho các trận sau.

**Kết quả:** pilot 15/15 trang có đủ hai HLV và hai đội hình 11 người. Bộ đầu ra hiện có **40 trận**, tương ứng [match_details.csv](data/cleaned/match_details.csv) **80 dòng × 15 cột** và [starting_xi.csv](data/cleaned/starting_xi.csv) **880 dòng × 8 cột**. Đây là **mẫu giới hạn**, mới bao phủ **40/3.040 trận Premier League (1,32%)**; không trình bày là đã crawl chi tiết toàn bộ giải. Báo cáo: [phase_03_details.md](reports/phase_03_details.md).

### Phase 4 — Crawl thông tin theo mùa từ Wikipedia

**Thực hiện:** mở trang Premier League của từng mùa; trích bảng đội/sân/sức chứa và bảng thay HLV. Lưu HTML cùng revision ID của trang.

**Kỹ thuật:** chọn bảng theo tiêu đề cột và đề mục; parser mở rộng ô gộp rowspan/colspan thành lưới để tránh lệch cột; chuẩn hóa ngày sự kiện; lưu revision ID phục vụ truy vết.

**Kết quả:** [team_seasons.csv](data/cleaned/team_seasons.csv) có **161 dòng × 6 cột**; mùa 2018/19 có hai sân gắn với Tottenham nên tổng lớn hơn 20 × 8. [manager_changes.csv](data/cleaned/manager_changes.csv) có **99 dòng × 10 cột**. Tám trang mùa đã được lưu bản gốc. Báo cáo: [phase_04_wikipedia.md](reports/phase_04_wikipedia.md).

### Phase 5 — Chuẩn hóa tên và ghép nguồn

**Thực hiện:** ánh xạ tên đội giữa các website; ví dụ Ipswich ↔ Ipswich Town, Man United ↔ Manchester United. Ghép các trận bằng mùa + ngày + đội nhà + đội khách, rồi nối sân và thông tin HLV theo thời gian.

**Kỹ thuật:** entity resolution với bảng alias có bằng chứng; fuzzy matching chỉ gợi ý, không tự quyết định; kiểm soát cardinality để không nhân đôi trận; kiểm tra tỷ số chéo giữa hai nguồn; xử lý trường hợp Tottenham dùng hai sân trong mùa 2018/19; lưu các trường hợp ngoài phạm vi hoặc chưa có chi tiết vào bảng kiểm toán.

**Kết quả:** [team_aliases.csv](data/cleaned/team_aliases.csv) có **313 dòng**. [matches_joined.csv](data/cleaned/matches_joined.csv) giữ đúng **3.040 dòng × 40 cột**. Cả 3.040 trận ghép được với lịch 11v11 và thông tin sân Wikipedia; tỷ số giữa Football-Data và 11v11 khớp theo báo cáo Phase 5. Chỉ 40 trận có dữ liệu chi tiết. [unmatched_matches.csv](data/cleaned/unmatched_matches.csv) có **4.376 dòng**, gồm 1.376 trận ngoài Premier League và 3.000 trận chưa crawl chi tiết; **không phải 4.376 lỗi ghép trận nền**. Báo cáo: [phase_05_join.md](reports/phase_05_join.md).

### Phase 6 — Tạo đặc trưng trước trận

**Thực hiện:** sắp xếp trận theo thời gian; từ lịch sử đã có, tính phong độ 5 trận, bàn ghi/thủng lưới, số ngày nghỉ, số trận trong 7/14 ngày, trận cúp gần đây, thời gian dưới HLV, sức chứa sân và chênh lệch giữa hai đội.

**Kỹ thuật:** rolling window và phép lọc thời gian nghiêm ngặt; chỉ dùng trận/sự kiện trước ngày cần dự đoán; không dùng tỷ số, đội hình hoặc thống kê của chính trận; giữ giá trị thiếu khi đội chưa có lịch sử thay vì tự đổi thành 0. Dữ liệu đội hình Phase 3 chỉ tạo đặc trưng tùy chọn.

**Kết quả:** [prematch_features.csv](data/model/prematch_features.csv) có **3.040 dòng × 44 cột**: 6 cột định danh/nhãn và 38 đặc trưng, trong đó **36 đặc trưng cốt lõi** và **2 đặc trưng đội hình tùy chọn**. Hai cột đội hình thiếu 77,53%, nên không nên đưa vào mô hình cơ sở khi chưa mở rộng Phase 3. Công thức và nguồn từng cột ở [feature_dictionary.md](data/model/feature_dictionary.md); báo cáo tại [phase_06_features.md](reports/phase_06_features.md).

### Phase 7 — Kiểm định và bàn giao dữ liệu

**Thực hiện:** kiểm tra số dòng, nhãn H/D/A, khóa trận, ngày, trường thiếu, tỷ lệ ghép, dấu hiệu rò rỉ thông tin hậu trận và một phép tính tay đối chiếu. Chia dữ liệu theo mùa, giữ tập kiểm thử ở thời gian mới nhất.

**Kỹ thuật:** kiểm định tự động; kiểm tra provenance; tách train/validation/test theo thời gian để tránh trộn trận tương lai vào tập huấn luyện.

**Kết quả:** báo cáo Phase 7 ghi **9/9 hạng mục kiểm định đạt**. Tách: train 2018/19–2023/24 = **2.280 trận**; validation 2024/25 = **380 trận**; test 2025/26 = **380 trận**. Mình đã chạy lại bộ kiểm thử hiện có ngày 24/10/2026: **51/51 kiểm thử đạt**. Đầu ra là [split_manifest.csv](data/model/split_manifest.csv) và [phase_07_readiness.md](reports/phase_07_readiness.md). Giai đoạn này chưa huấn luyện RandomForestClassifier hoặc báo độ chính xác dự đoán.

## 3. Kết quả tổng hợp

| Chỉ tiêu | Kết quả thực tế |
|---|---:|
| Mùa giải | 8 |
| Trận Premier League có nhãn | 3.040 |
| Bản ghi lịch thô 11v11 | 7.722 |
| Trận duy nhất sau loại trùng lịch | 4.416 |
| Trận ngoài Premier League dùng để tính lịch dày | 1.376 |
| Trang đội–mùa 11v11 | 160 |
| Trận có dữ liệu chi tiết HLV/đội hình | 40 / 3.040 (1,32%) |
| Dòng đội hình xuất phát | 880 |
| Dòng đội/sân Wikipedia | 161 |
| Sự kiện thay HLV Wikipedia | 99 |
| Trận nền ghép lịch và sân thành công | 3.040 / 3.040 |
| Bảng cuối cho mô hình | 3.040 dòng × 44 cột |
| Kiểm thử mã nguồn vừa chạy lại | 51/51 đạt |

**Kết luận dùng cho slide:** dự án đã hoàn thành bộ dữ liệu cốt lõi đa nguồn cho 3.040 trận Premier League và có thể chuyển sang huấn luyện RandomForestClassifier. Phần crawl trang chi tiết trận mới là mẫu 40 trận; hai đặc trưng ổn định đội hình cần để tùy chọn hoặc tiếp tục thu thập trước khi sử dụng rộng rãi. Số liệu kiểm định xác nhận cấu trúc và các quy tắc đã kiểm tra, chưa chứng minh hiệu quả dự đoán của mô hình.
