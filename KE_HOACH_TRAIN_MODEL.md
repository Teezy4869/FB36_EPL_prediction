# Kế hoạch train model tối giản dự đoán kết quả Premier League

Cập nhật: 24/10/2026. Đây là kế hoạch áp dụng cho giai đoạn sau crawl. Các số liệu bên dưới được đối chiếu trực tiếp với hai CSV trong data/model. Chưa train model nên chưa có độ chính xác thực tế.

## 1. Mục tiêu và phạm vi

- Dự đoán kết quả một trận trước khi bóng lăn theo ba nhãn: H = chủ nhà thắng, D = hòa, A = đội khách thắng. Dữ liệu có 700 trận hòa trong 3.040 trận, vì vậy phải giữ lớp D.
- Chỉ dùng dữ liệu biết được trước ngày thi đấu. Không dùng tỷ số, nhãn kết quả, đội hình của chính trận cần dự đoán hoặc thông tin từ tương lai làm đầu vào.
- Chỉ huấn luyện một mô hình chính: RandomForestClassifier của scikit-learn, với một cấu hình cố định. Có một mốc so sánh rất đơn giản: luôn dự đoán lớp phổ biến nhất trong tập train.
- Không tìm siêu tham số, không thử nhiều thuật toán, không cross-validation, calibration, ablation, neural network hoặc các kỹ thuật nâng cao trong phiên bản này.

## 2. Dữ liệu và danh sách đầu vào đã chốt

Hai tệp đầu vào:

- data/model/prematch_features.csv: 3.040 dòng, 44 cột; gồm 6 cột định danh/nhãn và 38 đặc trưng.
- data/model/split_manifest.csv: 3.040 match_id và nhãn train/validation/test đã gán theo mùa.

Chỉ dùng đúng 12 cột dưới đây làm X, theo thứ tự cố định:

| Nhóm | Cột |
|---|---|
| Số trận lịch sử | home_matches_available_last_5, away_matches_available_last_5 |
| Phong độ | home_points_avg_last_5, away_points_avg_last_5, home_goal_diff_last_5, away_goal_diff_last_5 |
| Nghỉ và mật độ thi đấu | home_days_since_last_match, away_days_since_last_match, home_matches_last_7_days, away_matches_last_7_days |
| Đội mới thăng hạng | is_promoted_home, is_promoted_away |

Lý do: các cột này có ý nghĩa trực tiếp và sẵn trong bộ dữ liệu; không cần tạo thêm đặc trưng hoặc chạy thử nhiều tổ hợp. Bốn cột phong độ trung bình/hiệu số mỗi chiều thiếu 80/3.040 dòng, chủ yếu khi chưa có trận trong mùa. Hai cột ngày nghỉ thiếu lần lượt 10 và 9 dòng. Cột matches_available giúp phân biệt chưa có lịch sử với phong độ bằng 0. Các cột đội hình thiếu nhiều không dùng.

Các cột match_id, season, match_date, canonical_home, canonical_away, result và split_set chỉ dùng để ghép, kiểm tra hoặc đánh giá; tuyệt đối không nằm trong X.

## 3. Quy trình tuần tự

### Bước 1 — Kiểm toán dữ liệu đầu vào

1. Ghép hai CSV theo match_id với quan hệ 1:1. Kiểm tra 3.040 mã duy nhất, mỗi mùa 380 trận, không có nhãn ngoài H/D/A và không có dòng lệch giữa hai tệp.
2. Đối chiếu result với tỷ số trong data/cleaned/matches_base.csv. Kiểm tra kiểu số, giá trị thiếu và miền hợp lệ của 12 cột đã chốt.
3. Kiểm tra thủ công một số trận đầu mùa, sau lịch thi đấu dày và sau trận cúp: phong độ/ngày nghỉ phải được tính từ trận có ngày trước match_date. Đối chiếu trực tiếp công thức của 12 cột trong src/phase_06_features.py với dữ liệu gốc.
4. Ghi kết quả vào reports/model_input_audit.md. Nếu phát hiện nhãn sai, ghép sai hoặc dùng thông tin tương lai, sửa ở pipeline tạo dữ liệu rồi tạo lại CSV trước khi train.

Lý do cần làm bước này: báo cáo Phase 7 ghi 9/9 PASS nhưng phép kiểm tra ghép nguồn CHECK_8_JOIN_INTEGRITY đang đặt PASS cố định, còn CHECK_5_LEAKAGE_AUDIT chủ yếu kiểm tra tên cột. Không dựa riêng vào hai kết luận đó để xác nhận 12 giá trị đầu vào an toàn.

Điều kiện qua bước: 12 cột có nguồn gốc và thời điểm khả dụng rõ ràng; lỗi nghiêm trọng đã được sửa.

### Bước 2 — Chia tập theo thời gian

Giữ nguyên split_manifest.csv, không chia ngẫu nhiên:

| Tập | Mùa | Số trận | Vai trò |
|---|---|---:|---|
| Train | 2018-19 đến 2023-24 | 2.280 | Học mô hình và giá trị điền thiếu |
| Validation | 2024-25 | 380 | Kiểm tra quy trình đã chốt |
| Test | 2025-26 | 380 | Đánh giá cuối, chỉ xem một lần sau khi khóa mô hình |

Kiểm tra các match_id không trùng giữa các tập và ngày của train luôn trước validation, validation trước test. Không dùng nhãn test để thay đổi đặc trưng, tham số hoặc quy tắc đánh giá.

### Bước 3 — Chuẩn bị đầu vào

1. Tạo X bằng danh sách 12 cột cố định; y lấy từ result.
2. Chuyển 12 cột sang số; báo lỗi nếu có chuỗi không hợp lệ hoặc giá trị vô hạn.
3. Dùng SimpleImputer(strategy="median") trong Pipeline. Imputer chỉ học median trên phần đang train, sau đó áp dụng cho validation/test. Không tự thay NaN bằng 0.
4. Không chuẩn hóa dữ liệu vì Random Forest không cần bước đó. Lưu thứ tự cột để lúc dự đoán dùng lại đúng schema.

Điều kiện qua bước: không còn NaN sau tiền xử lý, số cột và thứ tự cột nhất quán, không lọt result hoặc metadata vào X.

### Bước 4 — Tạo mốc so sánh

Từ nhãn của train, lấy lớp phổ biến nhất và dự đoán lớp đó cho mọi trận validation. Báo accuracy, macro F1 và bảng nhầm lẫn. Đây là mốc tham chiếu để biết Random Forest có mang lại giá trị; không phải vòng thử thuật toán.

### Bước 5 — Train đúng một cấu hình Random Forest

Dùng Pipeline gồm SimpleImputer và RandomForestClassifier với cấu hình định trước:

- n_estimators = 100
- max_depth = 8
- min_samples_leaf = 5
- random_state = 42
- n_jobs = -1

Các tham số khác dùng mặc định của phiên bản scikit-learn được ghi trong metadata. Fit một lần trên 2.280 trận train. Lưu phiên bản Python/thư viện, danh sách 12 cột và mã băm của hai CSV để chạy lại được. Không chỉnh tham số dựa trên điểm validation.

### Bước 6 — Đánh giá validation và khóa quy trình

Dự đoán 380 trận mùa 2024-25. Báo:

- Macro F1 là chỉ số chính, vì ba lớp không cân bằng.
- Accuracy, precision/recall/F1 cho H/D/A và bảng nhầm lẫn để thấy mô hình xử lý lớp hòa ra sao.
- So với mốc luôn dự đoán lớp phổ biến nhất.

Có thể lưu ba xác suất P(H), P(D), P(A) do mô hình trả về, nhưng không diễn giải chúng là xác suất đã hiệu chuẩn. Nếu kết quả thấp, ghi nhận và phân tích lỗi dữ liệu/quy trình; không thử thêm cấu hình trong kế hoạch này. Sau khi kiểm tra quy trình đúng, khóa danh sách cột, tiền xử lý, tham số và mã đánh giá.

### Bước 7 — Fit cuối và đánh giá test một lần

Fit lại đúng Pipeline đã khóa trên train + validation (2.660 trận); imputer cũng chỉ học từ 2.660 trận này. Dự đoán 380 trận test mùa 2025-26 đúng một lần và xuất data/model/test_predictions.csv gồm match_id, nhãn thật, nhãn dự đoán và P(H), P(D), P(A). Báo lại macro F1, accuracy, chỉ số từng lớp và bảng nhầm lẫn trong reports/model_test.md; so với mốc tham chiếu được fit trên train + validation.

Nếu test kém, công bố kết quả đúng như vậy. Không sửa mô hình rồi dùng lại cùng mùa test để tuyên bố kết quả mới là đánh giá độc lập.

### Bước 8 — Lưu mô hình và cách dự đoán trận mới

Lưu toàn bộ Pipeline vào models/premier_league_hda.joblib cùng metadata: 12 cột đúng thứ tự, mã H/D/A, tham số, phiên bản thư viện, mùa dùng để fit và kết quả đánh giá. Tạo lệnh dự đoán nhận đúng 12 giá trị trước trận; kiểm tra ba xác suất cộng xấp xỉ 1 và nhãn là lớp có xác suất lớn nhất.

Để dự đoán một trận tương lai từ tên đội và ngày, cần dựng 12 giá trị bằng các trận đã hoàn tất trước ngày đó. Không được dùng dòng tương lai từ CSV có sẵn nhãn result làm đầu vào trực tiếp. Nếu phần dựng đầu vào cho trận mới chưa có, mô hình chỉ được xem là đã huấn luyện và đánh giá, chưa phải công cụ dự đoán trực tiếp từ tên hai đội.

## 4. Sản phẩm bàn giao tối thiểu

- reports/model_input_audit.md: kiểm toán 12 cột và nhãn.
- src/train_model.py: nạp dữ liệu, ghép, tiền xử lý, train, đánh giá và lưu mô hình theo các bước trên.
- src/predict_match.py: dự đoán từ đúng 12 giá trị trước trận.
- requirements-model.txt: các thư viện và phiên bản cần để chạy lại.
- models/premier_league_hda.joblib và models/model_metadata.json.
- data/model/validation_predictions.csv, data/model/test_predictions.csv.
- reports/model_validation.md, reports/model_test.md.
- Hướng dẫn chạy lại từ hai CSV, không cần thao tác thủ công giữa các bước.

Hoàn thành khi chạy lại từ dữ liệu đã khóa tạo được cùng số dòng, cùng split, mô hình chạy được và báo cáo có kết quả validation/test thật. Kế hoạch này chưa khẳng định mô hình sẽ đạt độ chính xác cụ thể.


