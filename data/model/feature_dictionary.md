# Từ Điển Đặc Trưng Trước Trận (Pre-Match Feature Dictionary)
**Dự án**: Premier League Match Outcome Prediction  
**Tệp đầu ra**: `data/model/prematch_features.csv`  
**Quy tắc thời gian bắt buộc**: Mọi đặc trưng đều được tính toán từ các sự kiện diễn ra nghiêm ngặt trước ngày thi đấu (`event_date < match_date`). Tuyệt đối không dùng dữ liệu sau trận hoặc cùng ngày chưa rõ giờ.

---

## 1. Định danh & Nhãn Mục tiêu

| Tên Đặc trưng | Kiểu Dữ liệu | Nguồn | Thời điểm Khả dụng | Ý nghĩa & Cách Xử lý Missing |
| :--- | :---: | :--- | :--- | :--- |
| `match_id` | `string` | Football-Data / Phase 5 | Khi xếp lịch | Khóa chính duy nhất đại diện cho trận đấu (VD: `PL_201819_0001`). Không có missing. |
| `season` | `string` | Football-Data | Đầu mùa giải | Chuỗi định danh mùa giải (`2018-19` đến `2025-26`). Không có missing. |
| `match_date` | `string` | Football-Data / 11v11 | Khi công bố lịch | Ngày thi đấu thực tế trên sân theo chuẩn ISO 8601 (`YYYY-MM-DD`). Không có missing. |
| `canonical_home` | `string` | `team_aliases.csv` | Khi xếp lịch | Tên chuẩn hóa của câu lạc bộ chủ nhà. Không có missing. |
| `canonical_away` | `string` | `team_aliases.csv` | Khi xếp lịch | Tên chuẩn hóa của câu lạc bộ làm khách. Không có missing. |
| `result` | `string` | Football-Data | **SAU KHI KẾT THÚC** | **Nhãn mục tiêu (Ground Truth Label)**: `H` (Chủ nhà thắng), `D` (Hòa), `A` (Khách thắng). Chỉ dùng để huấn luyện/đánh giá mô hình. |

---

## 2. Nhóm Đặc trưng Phong độ 5 Trận Gần nhất (Premier League Form)

*Được tính toán riêng biệt cho `home_` và `away_` từ các trận Premier League đã hoàn tất trong cùng mùa giải trước `match_date`.*

| Tên Đặc trưng | Kiểu Dữ liệu | Nguồn | Công thức / Quy tắc Tính toán | Cách Xử lý Missing & Giá trị Huyết mạch |
| :--- | :---: | :--- | :--- | :--- |
| `home_matches_available_last_5` / `away_matches_available_last_5` | `integer` | `matches_joined.csv` | $k = \min(N_{\text{prior\_PL}}, 5)$ trong cùng mùa giải. | Giá trị từ `0` đến `5`. Không missing. Vòng 1 luôn bằng `0`. |
| `home_points_last_5` / `away_points_last_5` | `float` | `matches_joined.csv` | $\sum_{i=1}^k \text{Points}_i$ ($W=3, D=1, L=0$). | Nếu $k=0$ (Vòng 1), nhận giá trị `NaN`. Không tự biến missing thành 0. |
| `home_points_avg_last_5` / `away_points_avg_last_5` | `float` | `matches_joined.csv` | $\text{Points}_{\text{last\_5}} / k$. | Nếu $k=0$, nhận giá trị `NaN`. Đại diện tốc độ kiếm điểm/trận. |
| `home_wins_last_5` / `away_wins_last_5` | `integer` | `matches_joined.csv` | Số trận thắng trong $k$ trận gần nhất. | Nếu $k=0$, bằng `0` kèm `matches_available=0`. |
| `home_draws_last_5` / `away_draws_last_5` | `integer` | `matches_joined.csv` | Số trận hòa trong $k$ trận gần nhất. | Nếu $k=0$, bằng `0` kèm `matches_available=0`. |
| `home_losses_last_5` / `away_losses_last_5` | `integer` | `matches_joined.csv` | Số trận thua trong $k$ trận gần nhất. | Nếu $k=0$, bằng `0` kèm `matches_available=0`. |
| `home_goals_scored_last_5` / `away_goals_scored_last_5` | `float` | `matches_joined.csv` | Tổng bàn thắng ghi được trong $k$ trận gần nhất. | Nếu $k=0$, nhận giá trị `NaN`. |
| `home_goals_conceded_last_5` / `away_goals_conceded_last_5` | `float` | `matches_joined.csv` | Tổng bàn thua phải nhận trong $k$ trận gần nhất. | Nếu $k=0$, nhận giá trị `NaN`. |
| `home_goal_diff_last_5` / `away_goal_diff_last_5` | `float` | `matches_joined.csv` | $\text{Goals Scored} - \text{Goals Conceded}$. | Nếu $k=0$, nhận giá trị `NaN`. |

---

## 3. Nhóm Đặc trưng Mật độ & Nghỉ ngơi (Rest & Congestion - All Competitions)

*Được tính toán từ toàn bộ các giải đấu (Premier League, FA Cup, League Cup, UEFA Champions League, Europa League, Conference League) lấy từ `all_fixtures.csv`.*

| Tên Đặc trưng | Kiểu Dữ liệu | Nguồn | Công thức / Quy tắc Tính toán | Cách Xử lý Missing & Giải thích |
| :--- | :---: | :--- | :--- | :--- |
| `home_days_since_last_match` / `away_days_since_last_match` | `float` | `all_fixtures.csv` | $\text{match\_date} - \max(\text{fixture\_date})$ với $\text{fixture\_date} < \text{match\_date}$. | Nếu là trận đầu tiên của đội trong tập dữ liệu (Vòng 1 mùa 2018-19), nhận `NaN`. Giai đoạn COVID 2020 nhận giá trị > 90 ngày. |
| `home_matches_last_7_days` / `away_matches_last_7_days` | `integer` | `all_fixtures.csv` | Số trận thi đấu trong cửa sổ $1 \le \Delta t \le 7$ ngày. | Giá trị nguyên $\ge 0$. Đại diện mật độ thi đấu dồn dập. |
| `home_matches_last_14_days` / `away_matches_last_14_days` | `integer` | `all_fixtures.csv` | Số trận thi đấu trong cửa sổ $1 \le \Delta t \le 14$ ngày. | Giá trị nguyên $\ge 0$. |
| `home_had_cup_match_last_7_days` / `away_had_cup_match_last_7_days` | `integer` | `all_fixtures.csv` | $1$ nếu có ít nhất 1 trận cúp/châu Âu trong 7 ngày qua, ngược lại $0$. | Nhị phân `0` hoặc `1`. Phản ánh sự bào mòn thể lực từ cúp giữa tuần. |

---

## 4. Nhóm Đặc trưng Ổn định Băng ghế Huấn luyện (Managerial Stability)

| Tên Đặc trưng | Kiểu Dữ liệu | Nguồn | Công thức / Quy tắc Tính toán | Cách Xử lý Missing & Giải thích |
| :--- | :---: | :--- | :--- | :--- |
| `home_days_since_manager_appointment` / `away_days_since_manager_appointment` | `float` | `manager_changes.csv` & Wikipedia | $\text{match\_date} - \text{appointment\_date}$ của HLV đương nhiệm. | Giá trị số nguyên ngày. Trận đầu tiên sau khi đổi HLV có số ngày rất nhỏ (VD: 3 ngày ở Solskjaer). Nếu mốc không rõ, nhận `NaN`. |
| `home_matches_under_manager_in_season` / `away_matches_under_manager_in_season` | `integer` | `manager_changes.csv` & `matches_joined.csv` | Số trận Premier League trong mùa đã dẫn dắt trước ngày thi đấu. | Nếu vừa mới bổ nhiệm (trận ra mắt), nhận giá trị `0`. Không missing. |

---

## 5. Nhóm Đặc trưng Ổn định Đội hình Xuất phát (Lineup Stability)

| Tên Đặc trưng | Kiểu Dữ liệu | Nguồn | Công thức / Quy tắc Tính toán | Cách Xử lý Missing & Giải thích |
| :--- | :---: | :--- | :--- | :--- |
| `home_lineup_stability_prev` / `away_lineup_stability_prev` | `float` | `starting_xi.csv` (Phase 3) | $\frac{\|\text{Starters}(t-1) \cap \text{Starters}(t-2)\|}{11}$. | Tỷ lệ cầu thủ giữ nguyên giữa 2 trận trước đó ($t-1$ và $t-2$). **Tuyệt đối không dùng đội hình trận $t$**. Chỉ khả dụng khi cả $t-1$ và $t-2$ có Starting XI (Phase 3 crawl mẫu 40 trận). Khi thiếu, nhận `NaN`. |

---

## 6. Nhóm Đặc trưng Bối cảnh & Khác biệt Đối đầu (Contextual & Differential)

| Tên Đặc trưng | Kiểu Dữ liệu | Nguồn | Công thức / Quy tắc Tính toán | Cách Xử lý Missing & Giải thích |
| :--- | :---: | :--- | :--- | :--- |
| `stadium_capacity` | `integer` | Wikipedia (`team_seasons.csv`) | Sức chứa khán giả chính thức của sân vận động đội nhà. | Giá trị nguyên dương (VD: 74,879 Old Trafford, 62,062 Tottenham Hotspur Stadium). Không missing. |
| `is_promoted_home` / `is_promoted_away` | `integer` | Premier League Records | $1$ nếu câu lạc bộ vừa mới thăng hạng từ Championship mùa này, ngược lại $0$. | Nhị phân `0` hoặc `1`. Mỗi mùa có đúng 3 đội thăng hạng. Không missing. |
| `diff_points_avg_last_5` | `float` | Tính từ nhóm Form | $\text{home\_points\_avg\_last\_5} - \text{away\_points\_avg\_last\_5}$. | Phản ánh chênh lệch phong độ tương đối. `NaN` nếu 1 trong 2 đội chưa có điểm trung bình. |
| `diff_goal_diff_last_5` | `float` | Tính từ nhóm Form | $\text{home\_goal\_diff\_last\_5} - \text{away\_goal\_diff\_last\_5}$. | Chênh lệch hiệu số bàn thắng bại gần nhất. |
| `diff_days_rest` | `float` | Tính từ nhóm Rest | $\text{home\_days\_since\_last\_match} - \text{away\_days\_since\_last\_match}$. | Ưu thế thể lực/ngày nghỉ: dương nếu chủ nhà nghỉ nhiều ngày hơn đối thủ. |
