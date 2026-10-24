# Mốc so sánh validation — Phase 04/08

Mốc duy nhất: luôn dự đoán nhãn phổ biến nhất của **2.280 trận train**. Lớp được chọn trước khi dùng nhãn validation để tính metric. Split do `split_manifest.csv` quy định; không shuffle.

## Phân bố nhãn train

| Nhãn | Số trận | Tỷ lệ |
|---|---:|---:|
| H | 1019 | 44.69% |
| D | 503 | 22.06% |
| A | 758 | 33.25% |

Nhãn phổ biến nhất: **H**. Quy tắc hòa số lượng, nếu có: thứ tự H, D, A.

## Validation (380 trận, mùa 2024-25)

- Accuracy: **0.407895**
- Macro F1: **0.193146**
- `zero_division=0`; thứ tự lớp cố định: H, D, A.

| Lớp | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| H | 0.407895 | 1.000000 | 0.579439 | 155 |
| D | 0.000000 | 0.000000 | 0.000000 | 93 |
| A | 0.000000 | 0.000000 | 0.000000 | 132 |

Confusion matrix, hàng là nhãn thật; cột là dự đoán, đều theo H, D, A:

| Thật \ Dự đoán | H | D | A |
|---|---:|---:|---:|
| H | 155 | 0 | 0 |
| D | 93 | 0 | 0 |
| A | 132 | 0 | 0 |

Mốc này dự đoán cùng một lớp cho mọi trận. Vì lớp D không phổ biến nhất trong train, mốc không bao giờ dự đoán hòa; recall và F1 của D bằng 0. Đây là điểm tham chiếu, không phải kết quả của Random Forest.

Đầu ra theo đúng thứ tự `match_id` validation từ loader: `data/model/baseline_validation_predictions.csv` (380 dòng). Không dùng nhãn hoặc metric test; không fit imputer hay mô hình.

Chạy lại: `.\.venv\Scripts\python.exe -m src.train_model` từ thư mục dự án.
