# ⚽ Premier League H/D/A Prediction

Dự án xây dựng dữ liệu **trước trận** và một mô hình Random Forest để dự đoán kết quả Premier League: **H** (chủ nhà thắng), **D** (hòa), **A** (đội khách thắng). Bộ dữ liệu gồm **3.040 trận** thuộc tám mùa 2018-19 đến 2025-26. Mô hình đã được đánh giá theo thứ tự thời gian; kết quả test được công bố nguyên trạng, kể cả hạn chế với lớp hòa.

---

## 📊 Mục tiêu và kết quả

| Nội dung | Thiết kế đã khóa |
|---|---|
| Đầu vào | Đúng 12 đặc trưng biết trước ngày thi đấu |
| Chia dữ liệu | Train 2018-19–2023-24: 2.280; validation 2024-25: 380; test 2025-26: 380 |
| Tiền xử lý | Kiểm tra schema, `SimpleImputer(strategy="median")` |
| Mô hình | `RandomForestClassifier`, 100 cây, `max_depth=8`, `min_samples_leaf=5`, seed 42 |
| Chỉ số chính | Macro F1, với thứ tự lớp H/D/A |

| Tập đánh giá | Macro F1 | Accuracy | Recall D |
|---|---:|---:|---:|
| Validation | 0.377725 | 0.507895 | 0.000000 |
| Test | 0.353406 | 0.484211 | 0.000000 |

Mốc luôn dự đoán H đạt macro F1 **0.199262** trên test. Mô hình tốt hơn mốc này về macro F1, nhưng **không nhận ra trận hòa nào trong 104 trận hòa test**. Xem [báo cáo validation](reports/model_validation.md) và [báo cáo test](reports/model_test.md) để biết chỉ số từng lớp và bảng nhầm lẫn. `P(H)`, `P(D)`, `P(A)` là đầu ra của Random Forest, **chưa hiệu chuẩn**.

---

## 🧭 Quy trình

1. Thu thập kết quả trận, lịch thi đấu mọi giải và thông tin đội theo mùa.
2. Chuẩn hóa tên đội, ghép dữ liệu theo trận và tính đặc trưng chỉ từ sự kiện có ngày **trước** trận.
3. [Kiểm toán đầu vào](reports/model_input_audit.md): đối chiếu nhãn với tỷ số, ghép 1:1 và tính lại 12 cột trên toàn bộ 3.040 trận.
4. Chia theo mùa, huấn luyện một cấu hình Random Forest, đánh giá validation, khóa cấu hình rồi đánh giá test **một lần**.

Nguồn dữ liệu: [Football-Data.co.uk](https://www.football-data.co.uk/englandm.php) cho kết quả Premier League, [11v11](https://www.11v11.com/) cho lịch và chi tiết trận, [Wikipedia](https://en.wikipedia.org/wiki/Premier_League) cho thông tin đội theo mùa. Xem [quy trình crawl](QUY_TRINH_CRAWL_DATA.md), [từ điển đặc trưng](data/model/feature_dictionary.md) và [kế hoạch mô hình](KE_HOACH_TRAIN_MODEL.md). Kho HTML thô được giữ ngoài Git; CSV đã xử lý và đầu vào mô hình nằm trong repo.

---

## 🛠️ Công nghệ

Python 3.12, `pandas`, `numpy`, `scikit-learn` và `joblib`. Các phiên bản để chạy mô hình được ghim trong [requirements-model.txt](requirements-model.txt); thư viện cho quy trình thu thập dữ liệu ở [requirements.txt](requirements.txt).

---

## 🚀 Chạy dự đoán

Trong PowerShell, tại thư mục gốc repo:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-model.txt
.\.venv\Scripts\python.exe -m src.predict_match examples/prematch_input.json
```

Lệnh cuối nạp [pipeline đã lưu](models/premier_league_hda.joblib), kiểm tra **đúng 12 giá trị** trong [JSON ví dụ](examples/prematch_input.json), rồi trả nhãn và ba giá trị P theo thứ tự H/D/A. Không nhập tỷ số, `result` hoặc nhãn trận cần dự đoán. Xem [hướng dẫn sử dụng và tái lập](reports/model_usage.md) để dùng API Python hoặc chạy lại từ hai CSV.

---

## 🗂️ Cấu trúc repo

```text
data/cleaned/    CSV đã chuẩn hóa và ghép nguồn để kiểm toán
data/model/      Đặc trưng, manifest chia tập và dự đoán đã lưu
examples/        Một bản ghi 12 giá trị trước trận
models/          Pipeline, metadata và cấu hình đã khóa
reports/         Báo cáo dữ liệu, validation, test và cách sử dụng
src/             Mã tạo dữ liệu, kiểm toán, train, đánh giá, dự đoán và kiểm tra
```

Các artifact quan trọng: [model_metadata.json](models/model_metadata.json), [model_lock.json](models/model_lock.json), [test_predictions.csv](data/model/test_predictions.csv). `src/evaluate_test.py` không fit hay chấm lại khi artifact Phase 07 đã tồn tại. Một lần chạy mới trên cùng mùa 2025-26 **không** được xem là test độc lập đầu tiên.

## ⚠️ Giới hạn

Công cụ hiện nhận **12 giá trị đã tính trước trận**. Để nhập tên hai đội và ngày thi đấu, cần thêm bước dựng các giá trị này từ các trận đã hoàn tất trước ngày đó. Mô hình không tự tra cứu lịch thi đấu và chưa giải quyết được lớp hòa.
