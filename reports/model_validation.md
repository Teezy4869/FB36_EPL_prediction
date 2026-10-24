# Đánh giá validation — Phase 06/08

Pipeline train-only từ Phase 05 được nạp lại và chạy **một lượt `predict_proba`** trên 380 trận mùa 2024-25. CSV nguồn, 12 cột, median train, tham số và phiên bản khớp metadata Phase 05. Không fit lại mô hình.

## Kết quả thật

- **Macro F1 (chính): 0.377725**
- Accuracy: 0.507895
- Thứ tự lớp cố định: H, D, A; `zero_division=0`.

| Lớp | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| H | 0.485075 | 0.838710 | 0.614657 | 155 |
| D | 0.000000 | 0.000000 | 0.000000 | 93 |
| A | 0.567568 | 0.477273 | 0.518519 | 132 |

Confusion matrix (hàng nhãn thật, cột dự đoán):

| Thật \ Dự đoán | H | D | A |
|---|---:|---:|---:|
| H | 130 | 1 | 24 |
| D | 69 | 0 | 24 |
| A | 69 | 0 | 63 |

Số dự đoán theo lớp: H=268, D=1, A=111. Riêng lớp hòa D: recall **0.000000** (0/93 trận hòa được nhận ra).

## So với mốc Phase 04

Hai kết quả dùng cùng 380 `match_id`, cùng nhãn thật và thứ tự H,D,A. Baseline CSV được kiểm tra khớp loader trước khi tính lại metric.

| Chỉ số | Baseline luôn H | Random Forest | Chênh lệch |
|---|---:|---:|---:|
| Macro F1 | 0.193146 | 0.377725 | +0.184579 |
| Accuracy | 0.407895 | 0.507895 | +0.100000 |
| Recall D | 0.000000 | 0.000000 | +0.000000 |

## Lỗi và giới hạn

- Nhầm lẫn lớn nhất: **69 trận thật D dự đoán H, 69 trận thật A dự đoán H**. Bảng trên cho thấy toàn bộ lỗi theo lớp; kết quả được giữ nguyên dù thấp hơn baseline ở chỉ số nào.
- **10** trận validation có ít nhất một đội chưa có trận Premier League trước đó trong mùa; **4** trận trong nhóm này bị dự đoán sai. Khi đầu mùa, phong độ 5 trận của đội đó là NaN và imputer dùng median học từ train; `matches_available_last_5=0` vẫn giữ dấu hiệu thiếu lịch sử. Đây là giới hạn thông tin đầu vào, không được dùng để đổi thiết kế sau validation.
- `P(H)`, `P(D)`, `P(A)` là đầu ra `predict_proba` của Random Forest, **chưa được hiệu chuẩn**. Không diễn giải chúng là xác suất thực tế đã hiệu chuẩn.

CSV: `data/model/validation_predictions.csv`, đúng 380 dòng theo thứ tự manifest. Quy tắc, artifact và checksum được khóa tại `models/model_lock.json` trước Phase 07. Mã đánh giá không gọi API lấy nhãn test, không tính metric test; không tuning, calibration hay fit lại.

Chạy lại: `.\.venv\Scripts\python.exe -m src.validate_model` từ thư mục dự án.
