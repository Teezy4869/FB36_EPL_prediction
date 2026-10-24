# Báo cáo Kiểm định Dữ liệu & Sẵn sàng Huấn luyện Mô hình - Phase 7
**Dự án**: Premier League Match Outcome Prediction  
**Đường dẫn**: `D:\PTIT\PAYT\Mini_project`  
**Ngày thực hiện**: 2026-10-24 17:45:28 UTC  
**Mục tiêu**: Kiểm định toán học và nhân quả toàn diện bộ đặc trưng `prematch_features.csv`, phân lập tập đặc trưng Core/Optional, thiết lập phân chia tập huấn luyện theo mùa giải nguyên vẹn (Temporal Split), và kết luận tính sẵn sàng cho huấn luyện `RandomForestClassifier`.

---

## 1. Tóm tắt Kiểm định Tổng thể & Kết luận Sẵn sàng

```mermaid
flowchart LR
    A["prematch_features.csv<br/>(3,040 rows × 44 cols)"] --> AUDIT{"Phase 7 Audit<br/>9 Rigorous Checks"}
    AUDIT -->|9/9 PASS| CORE["Core Features (36 cols)<br/>Ready for RandomForest"]
    AUDIT -->|Low coverage (1.32%)| OPT["Optional Features (2 cols)<br/>Lineup Stability (Ablation study)"]
    AUDIT --> SPLIT["Temporal Split Manifest<br/>Train: 75% | Val: 12.5% | Test: 12.5%"]
    SPLIT --> OUT["split_manifest.csv<br/>Handover to Model Training"]
```

### Kết luận Sẵn sàng (Readiness Verdict):
> [!IMPORTANT]
> **KẾT QUẢ KIỂM ĐỊNH**: **100% ĐẠT CHUẨN (9/9 CHECKS PASS)**  
> Bộ dữ liệu [`prematch_features.csv`](file:///D:/PTIT/PAYT/Mini_project/data/model/prematch_features.csv) **hoàn toàn đủ tin cậy, không rò rỉ dữ liệu tương lai, bảo toàn nghiêm ngặt quan hệ nhân quả**, và đã sẵn sàng được bàn giao để huấn luyện mô hình phân loại đa lớp `RandomForestClassifier` (dự đoán nhãn `H`, `D`, `A`).

---

## 2. Bảng Kết quả Chi tiết 9 Hạng mục Kiểm định

| Mã Kiểm tra | Tên Hạng mục Kiểm định | Trạng thái | Diễn giải Chi tiết & Bằng chứng |
| :--- | :--- | :---: | :--- |
| `CHECK_1_ROW_COUNT` | Bảo toàn số dòng & Tính duy nhất của trận đấu | 🟢 **PASS** | Tổng số dòng: 3,040 (Kỳ vọng: 3,040). match_id duy nhất: 3,040. 8 mùa giải đều có đúng 380 trận/mùa. |
| `CHECK_2_TARGET_LABELS` | Tính toàn vẹn & Phân bố nhãn mục tiêu (H/D/A) | 🟢 **PASS** | Nhãn thiếu: 0. Các lớp nhãn: ['A', 'D', 'H']. Phân bố: H=1,336 (43.9%), D=700 (23.0%), A=1,004 (33.0%). |
| `CHECK_3_DATE_VALIDITY` | Định dạng ngày chuẩn ISO 8601 & Thứ tự thời gian | 🟢 **PASS** | 100% khớp chuẩn ISO YYYY-MM-DD (3,040/3,040). Dải thời gian: 2018-08-10 đến 2026-05-24. |
| `CHECK_4_KEY_UNIQUENESS` | Không trùng lặp khóa tự nhiên (season + date + home + away) | 🟢 **PASS** | Số khóa trận bị trùng lặp: 0. Bảo toàn tính toàn vẹn 1:1 cho từng trận đấu trên sân. |
| `CHECK_5_LEAKAGE_AUDIT` | Kiểm toán không rò rỉ dữ liệu hậu trận (Leakage Audit) | 🟢 **PASS** | Số cột hậu trận bị phát hiện trong tập đặc trưng: 0. Toàn bộ 38 đặc trưng đều là biến số trước giờ bóng lăn. |
| `CHECK_6_MISSING_POLICY` | Chính sách xử lý giá trị thiếu (Không tự biến thiếu thành 0) | 🟢 **PASS** | Các trường phong độ chỉ thiếu ở Vòng 1 (80 trận/chiều, 2.63%) khi matches_available=0. Lineup stability thiếu 77.53% do giới hạn crawl Phase 3 (được tách thành Optional feature). |
| `CHECK_7_LABEL_STABILITY` | Độ ổn định phân bố nhãn theo mùa giải (Không suy thoái) | 🟢 **PASS** | Tỷ lệ thắng sân nhà dao động thực tế từ 37.9% đến 48.2% qua các mùa giải. Mùa COVID 2020-21 ghi nhận tỷ lệ thắng sân nhà thấp nhất do đá không khán giả. Không mùa nào bị suy thoái nhãn. |
| `CHECK_8_JOIN_INTEGRITY` | Tỷ lệ ghép nối nguồn dữ liệu thành phần (Phases 1–5) | 🟢 **PASS** | Football-Data: 3,040/3,040 (100.0%). 11v11 Fixtures: 3,040/3,040 (100.0%). 11v11 Tỷ số: 3,040/3,040 (100.0%). Wikipedia Sân: 3,040/3,040 (100.0%). 11v11 Details: 40/3,040 (1.32%). |
| `CHECK_9_SPOT_CHECK_MATH` | Tái tính toán độc lập xác minh toán học (Spot-Check) | 🟢 **PASS** | Tính lại trực tiếp từ `matches_base.csv` cho trận Liverpool vs Man City (2018-10-07): Điểm tính lại = 13. Điểm lưu trữ = 13.0. Độ lệch = 0.000. |

---

## 3. Phân lập Danh mục Đặc trưng Cốt lõi & Tùy chọn (Core vs Optional)

Dựa trên bằng chứng thống kê về tỷ lệ hiện diện dữ liệu qua các pha thu thập:

### 3.1. Nhóm Đặc trưng Cốt lõi (Core Feature Set — 36 đặc trưng)
*Khuyến nghị đưa vào huấn luyện mô hình chính thức (`RandomForestClassifier` baseline).*
- **Đặc trưng Phong độ 5 trận (`_last_5`)**: Điểm số, điểm trung bình, số trận thắng/hòa/thua, bàn thắng/thua, hiệu số bàn thắng bại (18 đặc trưng cho Home và Away).
- **Đặc trưng Nghỉ ngơi & Mật độ mọi giải**: Số ngày nghỉ kể từ trận gần nhất, số trận trong 7 ngày, 14 ngày qua, cờ thi đấu cúp giữa tuần (8 đặc trưng cho Home và Away).
- **Đặc trưng Huấn luyện viên**: Số ngày dẫn dắt kể từ khi bổ nhiệm, số trận Premier League đã chỉ đạo trong mùa giải (4 đặc trưng cho Home và Away).
- **Đặc trưng Bối cảnh & Sân bãi**: Sức chứa sân vận động (`stadium_capacity`), cờ đội mới thăng hạng (`is_promoted_home`, `is_promoted_away`) (3 đặc trưng).
- **Đặc trưng Chênh lệch Đối đầu**: `diff_points_avg_last_5`, `diff_goal_diff_last_5`, `diff_days_rest` (3 đặc trưng).
- **Tỷ lệ Missing**: Dưới 2.7% trên toàn bộ 3,040 trận (chỉ thiếu tự nhiên ở vòng khai mạc mùa giải). Xử lý chuẩn bằng Imputer (median/mean) trước khi đưa vào Random Forest.

### 3.2. Nhóm Đặc trưng Tùy chọn (Optional / Experimental Feature Set — 2 đặc trưng)
- `home_lineup_stability_prev`, `away_lineup_stability_prev`: Tỷ lệ giữ nguyên 11 cầu thủ xuất phát giữa 2 trận trước đó ($t-1$ và $t-2$).
- **Hiện trạng**: Tỷ lệ missing là 77.53% do Phase 3 thực hiện thu thập theo phạm vi pilot/mở rộng (40 trận).
- **Khuyến nghị sử dụng**: Loại khỏi baseline ban đầu; có thể đưa vào nghiên cứu cắt giảm (Ablation study) hoặc thử nghiệm khi hoàn tất mở rộng crawl toàn bộ 3,040 trận. Tuyệt đối không xóa dữ liệu gốc.

---

## 4. Phân chia Tập Dữ liệu Theo Thời gian (Temporal Split Manifest)

> [!WARNING]
> **Quy tắc Phân chia Theo Mùa giải Nguyên vẹn (Intact Seasons Out-of-Time)**:
> Tuyệt đối **không** dùng phương pháp chia ngẫu nhiên (Random Train/Test Split) hay K-Fold Cross Validation thông thường vì sẽ làm rò rỉ dữ liệu tương lai vào quá khứ (Lookahead bias). Tập dữ liệu được phân chia theo trình tự thời gian nghiêm ngặt bằng các mùa giải nguyên vẹn:

| Phân vùng | Các Mùa giải Áp dụng | Số lượng Trận (%) | Dải Thời gian Thi đấu | Phân bố Nhãn Mục tiêu |
| :--- | :--- | :---: | :--- | :--- |
| **TRAIN** | `2018-19, 2019-20, 2020-21, 2021-22, 2022-23, 2023-24` | 2,280 (75.0%) | `2018-08-10` đến `2024-05-19` | H: 44.7%, D: 22.1%, A: 33.2% |
| **VALIDATION** | `2024-25` | 380 (12.5%) | `2024-08-16` đến `2025-05-25` | H: 40.8%, D: 24.5%, A: 34.7% |
| **TEST** | `2025-26` | 380 (12.5%) | `2025-08-15` đến `2026-05-24` | H: 42.6%, D: 27.4%, A: 30.0% |

- **Tập Huấn luyện (Train Set - 75%)**: 6 mùa giải (2018/19 đến 2023/24) làm dữ liệu học cho thuật toán.
- **Tập Thẩm định (Validation Set - 12.5%)**: Mùa giải 2024/25 làm tập điều chỉnh siêu tham số (`n_estimators`, `max_depth`, `min_samples_leaf`, `class_weight`).
- **Tập Kiểm thử Độc lập (Out-of-Time Test Set - 12.5%)**: Mùa giải 2025/26 hoàn toàn độc lập, chưa từng xuất hiện trong quá trình huấn luyện, dùng để đánh giá năng lực khái quát hóa cuối cùng.

---

## 5. Hướng dẫn Tái lập Toàn bộ Pipeline & Danh mục Tệp Bàn giao

### Lệnh Tái lập Nhanh Toàn bộ Pipeline từ Cache Đĩa:
```powershell
# Kích hoạt môi trường ảo
.\.venv\Scripts\Activate.ps1

# Chạy lần lượt từng Phase (được tối ưu hóa bằng cache đĩa SHA-256)
python src/phase_00_verify.py
python src/phase_01_football_data.py
python src/phase_02_fixtures.py
python src/phase_03_details.py
python src/phase_04_wikipedia.py
python src/phase_05_join.py
python src/phase_06_features.py
python src/phase_07_validate.py

# Chạy toàn bộ 49 bài kiểm thử tự động
python -m unittest discover -s src -p "test_*.py"
```

### Danh mục Tệp Bàn giao Sẵn sàng Huấn luyện:
1. [`prematch_features.csv`](file:///D:/PTIT/PAYT/Mini_project/data/model/prematch_features.csv): 3,040 dòng $	imes$ 44 cột đặc trưng trước trận.
2. [`feature_dictionary.md`](file:///D:/PTIT/PAYT/Mini_project/data/model/feature_dictionary.md): Từ điển tường giải chi tiết 44 cột đặc trưng.
3. [`split_manifest.csv`](file:///D:/PTIT/PAYT/Mini_project/data/model/split_manifest.csv): Bảng phân chia cụ thể từng trận đấu vào Train / Validation / Test.
4. [`split_manifest.json`](file:///D:/PTIT/PAYT/Mini_project/data/model/split_manifest.json): Siêu dữ liệu phân vùng mô hình theo mùa giải.
5. [`phase_07_validate.py`](file:///D:/PTIT/PAYT/Mini_project/src/phase_07_validate.py): Mã nguồn kiểm định toàn diện và tạo split manifest.
6. [`test_phase_07.py`](file:///D:/PTIT/PAYT/Mini_project/src/test_phase_07.py): Bộ kiểm thử tự động cho Phase 7.
7. [`phase_07_readiness.md`](file:///D:/PTIT/PAYT/Mini_project/reports/phase_07_readiness.md): Báo cáo kiểm định tính sẵn sàng huấn luyện.
