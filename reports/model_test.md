# Đánh giá test — Phase 07/08

Đây là **lần đánh giá test đầu tiên** với mô hình và quy tắc đã khóa ở Phase 06. Trước khi mở nhãn test, audit Phase 01 PASS, checksum và cấu hình `model_lock.json` khớp dữ liệu, mã và artifact Phase 05/06. Pipeline được fit đúng một lần trên 2.660 trận train + validation (2018-19 đến 2024-25), lưu và nạp lại thành công; median chỉ học từ 2.660 trận đó. Sau đó chạy một lượt `predict_proba` trên 380 trận test mùa 2025-26. Thời gian fit: 0.287 giây.

## Kết quả test

- **Macro F1 (chính): 0.353406**
- Accuracy: 0.484211
- Thứ tự H,D,A; `zero_division=0`.

| Lớp | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| H | 0.496350 | 0.839506 | 0.623853 | 162 |
| D | 0.000000 | 0.000000 | 0.000000 | 104 |
| A | 0.452830 | 0.421053 | 0.436364 | 114 |

Confusion matrix (hàng nhãn thật, cột dự đoán):

| Thật \ Dự đoán | H | D | A |
|---|---:|---:|---:|
| H | 136 | 0 | 26 |
| D | 72 | 0 | 32 |
| A | 66 | 0 | 48 |

Dự đoán theo lớp: H=274, D=0, A=106. Lớp hòa D có recall **0.000000** (0/104 trận hòa).

## Mốc lớp phổ biến nhất

Nhãn của 2.660 trận fit: H=1174, D=596, A=890; lớp phổ biến nhất là **H**. Mốc dự đoán H cho mọi trận test, không dùng nhãn test để chọn lớp.

| Chỉ số | Baseline | Random Forest | Chênh lệch |
|---|---:|---:|---:|
| Macro F1 | 0.199262 | 0.353406 | +0.154144 |
| Accuracy | 0.426316 | 0.484211 | +0.057895 |
| Recall D | 0.000000 | 0.000000 | +0.000000 |

## Lỗi và giới hạn

- Nhầm lẫn lớn nhất: 72 trận thật D dự đoán H. Confusion matrix cho biết toàn bộ lỗi H/D/A; kết quả test được giữ nguyên dù chỉ số nào thấp.
- Có 10 trận ít nhất một đội chưa có trận Premier League trước đó trong mùa; 6 trận dự đoán sai. Phong độ đầu mùa thiếu lịch sử, imputer dùng median học trên train + validation; cột `matches_available_last_5=0` vẫn đánh dấu tình trạng này.
- `P(H)`, `P(D)`, `P(A)` là đầu ra Random Forest **chưa hiệu chuẩn**, không phải xác suất thực tế đã hiệu chuẩn.

Không thay cột, tham số, imputer, ngưỡng hay metric sau validation/test. Lịch sử sửa kỹ thuật Phase 07: thêm mã đánh giá có kiểm tra khóa và chốt chặn artifact; không sửa dữ liệu nguồn hoặc cấu hình đã khóa.

## Artifact và bằng chứng

- Mô hình: `models/premier_league_hda.joblib`; nạp lại PASS; SHA-256 `931cf900c28e24531da8d75f4807b60f86a0c8c0ef770a095d24b6974990f09b`.
- Dự đoán: `data/model/test_predictions.csv`; 380 dòng đúng thứ tự manifest; SHA-256 `4c9087ee876e06e9e6648c3b3f4831a41122d1501137e15c8d11f1f1f2b40852`.
- Lock: `models/model_lock.json`; SHA-256 `ca2f325e2ebfdb70924dd109be01b0b239b6de50e3dec475d5e2f5962853aab4`.
- CSV đầu vào: `prematch_features.csv` `44fb34abebf74bdcdfd30b9ab8c0dd04f2351da503025bee532311f301203083`; `split_manifest.csv` `3b9efe26c0051d86a8f350355985478c702aad7c410228a34fe6ad1ed4851f6a`.

Chạy lệnh `.\.venv\Scripts\python.exe -m src.evaluate_test` từ thư mục dự án để xem trạng thái artifact hiện có. Lệnh sẽ không fit, ghi đè hay chấm lại khi artifact Phase 07 đã tồn tại. Test này không được tuyên bố là một lần đánh giá độc lập nữa.
