# Sử dụng mô hình H/D/A — Phase 08/08

## Cài đặt và artifact

Từ thư mục `D:\PTIT\PAYT\Mini_project`, dùng Python 3.12.10:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-model.txt
```

Pipeline cuối đã lưu tại `models/premier_league_hda.joblib`; cấu hình và checksum ở `models/model_metadata.json` và `models/model_lock.json`. Hai CSV nguồn là `data/model/prematch_features.csv` và `data/model/split_manifest.csv`. Báo cáo đầu vào, validation và test lần lượt ở `reports/model_input_audit.md`, `reports/model_validation.md`, `reports/model_test.md`.

## Dự đoán một trận

Chuẩn bị một JSON object có **đúng 12 khóa** như `examples/prematch_input.json`, chỉ dùng dữ liệu biết trước trận. Chạy:

```powershell
.\.venv\Scripts\python.exe -m src.predict_match examples/prematch_input.json
```

Ví dụ này lấy 12 giá trị trước trận của một dòng lịch sử (`PL_201819_0057`); JSON không chứa `match_id`, nhãn, tỷ số, ngày hoặc tên đội. Đầu ra là `label` và `P(H)`, `P(D)`, `P(A)`. H là chủ nhà thắng, D là hòa, A là đội khách thắng. Ba số P là đầu ra của Random Forest, **chưa hiệu chuẩn**. Mã từ chối khóa thiếu/thừa (kể cả `result`), chuỗi thay số, cờ không phải 0/1, giá trị vô hạn và giá trị ngoài miền. `null` chỉ hợp lệ ở những cột có thể thiếu lịch sử; imputer trong pipeline điền median đã học từ 2.660 trận fit.

Đầu ra của tệp ví dụ trên với artifact hiện tại:

```json
{"label": "H", "P(H)": 0.7506496973175438, "P(D)": 0.14285377242769542, "P(A)": 0.10649653025476033}
```

API Python cũng nhận một `dict` 12 khóa:

```python
import json
from src.predict_match import predict_match

with open("examples/prematch_input.json", encoding="utf-8") as stream:
    record = json.load(stream)
print(predict_match(record))
```

## Tái lập quy trình train từ hai CSV

Các lệnh sau dành cho **bản sao mới của dự án**, khi muốn tái lập toàn bộ quy trình đã khóa từ hai CSV. Chạy theo thứ tự; không chạy lại các bước train/validation trên thư mục chứa artifact test đầu tiên rồi tuyên bố test là đánh giá độc lập mới.

```powershell
.\.venv\Scripts\python.exe src/model_input_audit.py
.\.venv\Scripts\python.exe -m src.train_model baseline
.\.venv\Scripts\python.exe -m src.train_model train
.\.venv\Scripts\python.exe -m src.validate_model
.\.venv\Scripts\python.exe -m src.evaluate_test
```

`model_data.py` nạp hai CSV và chia theo `split_manifest.csv`; `model_pipeline.py` giữ đúng 12 cột và imputer median. Bước test chỉ mở nhãn sau khi fit và lưu pipeline cuối. Nếu artifact test đã tồn tại, `src.evaluate_test` chỉ báo trạng thái, không fit hoặc chấm lại. Đọc kết quả đã công bố trong `reports/model_validation.md` và `reports/model_test.md`.

`models/model_metadata.json` là ảnh chụp **artifact hiện tại**. Nếu chạy lại train trong một bản sao và tạo joblib mới, cần đóng gói metadata theo checksum, phiên bản và báo cáo của lần chạy đó trước khi dùng lệnh dự đoán; lệnh sẽ từ chối joblib không khớp metadata. Lần chạy test mới trên cùng mùa 2025-26 không phải một đánh giá độc lập đầu tiên nữa.

## Giới hạn

Công cụ hiện **nhận sẵn 12 giá trị trước trận**. Muốn nhập tên hai đội và ngày thi đấu, cần thêm bước tính 12 giá trị này từ những trận đã hoàn tất **trước** ngày đó; chưa có bước đó trong gói Phase 08. Không lấy nguyên một dòng tương lai có `result` từ CSV để dự đoán. Test đã công bố có macro F1 0.353406, accuracy 0.484211 và recall lớp hòa D bằng 0; vì vậy cần đọc bảng lỗi trong báo cáo trước khi dùng kết quả.
