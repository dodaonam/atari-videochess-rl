# Kế hoạch tổng thể: Xây dựng Reinforcement Learning Agent cho Atari Video Chess

Dự án: [atari-videochess-rl](https://github.com/dodaonam/atari-videochess-rl) Môi trường đích: `ALE/VideoChess-v5` Framework: PyTorch, Gymnasium, ALE, python-chess Định hướng: Supervised Pretraining → Reinforcement Learning → Evaluation → Iterative Improvement

## I. Định hướng và mục tiêu của dự án

### 1. Bài toán chúng ta thực sự muốn giải quyết

Mục tiêu không chỉ là tạo ra một chương trình có thể thắng Atari Video Chess, mà là:

Thiết kế, huấn luyện và đánh giá một RL agent có khả năng học chiến lược chơi cờ vua, sử dụng kiến thức từ một chess engine mạnh trong quá trình huấn luyện nhưng có khả năng tự đưa ra quyết định khi triển khai.

Các ràng buộc đã xác định:

| Hạng mục                        | Yêu cầu                                                       |
| ------------------------------- | ------------------------------------------------------------- |
| Môi trường đích                 | `ALE/VideoChess-v5`                                           |
| Sử dụng board-state extraction  | Được phép                                                     |
| Sử dụng action wrapper          | Được phép                                                     |
| Sử dụng Stockfish khi training  | Được phép                                                     |
| Sử dụng Stockfish khi inference | Không được phép                                               |
| Dùng Stable-Baselines           | Không                                                         |
| Dùng Ray RLlib                  | Không                                                         |
| Tự triển khai thuật toán RL     | Có, bằng PyTorch                                              |
| Tài nguyên                      | Colab T4 Free, CPU local                                      |
| Tiêu chí học thuật              | Kết quả tốt và giải thích được thuật toán                     |
| Mục tiêu sức chơi               | Hướng tới \~1500 Elo, nhưng không bắt buộc                    |
| Thời gian thực hiện             | Khoảng 3 tuần; không gắn lịch ngày cố định cho từng giai đoạn |

### 2. Định nghĩa thành công

Tôi đề xuất ba mức kết quả, từ yêu cầu tối thiểu đến tham vọng.

Mức 1 — Hoàn thành kỹ thuật

Agent có thể đọc bàn cờ, lựa chọn và thực hiện nước đi hợp lệ, chơi hết ván, lưu checkpoint, chạy evaluation và tái lập thực nghiệm.

Đây là mức bắt buộc.

Mức 2 — Có kết quả RL đáng tin cậy

Model thể hiện kiến thức chơi cờ, tốt hơn baseline đơn giản, và thực nghiệm có thể xác định được phần đóng góp của pretraining và phần cải thiện do RL.

Đây là mục tiêu học thuật chính.

Mức 3 — Sức chơi cạnh tranh

Đánh tốt trước Atari Video Chess, có khả năng đấu với người chơi đã biết chơi cờ và hướng tới mức 1500 Elo theo một hệ thống đo được xác định rõ.

Đây là mục tiêu mở rộng, không phải kết quả có thể cam kết.

### 3. Nguyên tắc thiết kế xuyên suốt

Tôi đề xuất tuân thủ năm nguyên tắc.

1. Start simple, then improve: Luôn bắt đầu với hệ thống nhỏ nhất có thể kiểm chứng, chỉ bổ sung độ phức tạp khi có kết quả cho thấy nó cần thiết.
2. Separate responsibilities: Tách riêng phần điều khiển Atari, luật cờ, lựa chọn nước đi, neural network và training.
3. Learning must be measurable: Không mặc định RL làm model mạnh hơn. Mọi cải tiến phải được đo so với phiên bản trước.
4. No teacher leakage: Stockfish và nhãn chuyên gia chỉ xuất hiện ở pipeline huấn luyện hoặc công cụ benchmark độc lập, tuyệt đối không nằm trong đường đi inference của agent.
5. Reproducibility: Mỗi thí nghiệm cần lưu cấu hình, seed, phiên bản thư viện, dataset, checkpoint và kết quả.

## II. Phương án kỹ thuật chủ đạo

### 1. Lựa chọn kiến trúc RL

Tôi đề xuất:

Engine-guided Pretraining + Action-conditioned Double DQN, sử dụng biểu diễn trạng thái bàn cờ và tập nước đi hợp lệ.

Thay vì nhận ảnh Atari rồi dự đoán joystick action, model sẽ nhận trạng thái bàn cờ \\(s\\) và đánh giá các nước đi hợp lệ \\(a\\).

\\[ Q\_\theta(s,a)\approx \text{giá trị kỳ vọng khi thực hiện nước }a \\]

Khi inference:

\\[ a^\*=\arg\max\_{a\in\mathcal A\_{\mathrm{legal}}(s)}Q\_\theta(s,a) \\]

Trong đó:

- \\(s\\): trạng thái bàn cờ, bao gồm các thông tin cần thiết cho luật chơi.
- \\(a\\): nước đi ứng viên.
- \\(\mathcal A\_{\mathrm{legal}}(s)\\): tập nước đi hợp lệ.
- \\(Q\_\theta\\): neural network tự huấn luyện.

Tôi ưu tiên dùng một mạng đánh giá trạng thái sau nước đi, hay afterstate network, để tránh phải tạo output cố định rất lớn cho mọi nước cờ có thể có.

Ví dụ:

Candidate A

## e2e4

Neural score

### +0.63

Candidate B

## d2d4

Neural score

### +0.57

Candidate C

## g1f3

Neural score

### +0.48

Candidate D

## a2a3

Neural score

### +0.12

Ví dụ minh họa giả định về điểm do neural network dự đoán, không phải kết quả model đã huấn luyện.

Model đánh giá tất cả những nước hợp lệ, sau đó chọn nước có điểm cao nhất. Không cần gọi Stockfish khi inference.

### 2. Tổng quan hệ thống

Chess Data

FEN, PGN, positions

Stockfish

Training only

Expert Dataset + Label Processing

State encoding, position values, legal moves

Supervised Pretraining

Initialize the Q-value network

Double DQN Fine-tuning

Replay buffer, TD targets, online/target networks

Simulator gameplay and reward feedback

Trained RL Agent

PyTorch model + legal move generation

No Stockfish at inference

ALE Wrapper → Atari Video Chess

Board extraction, cursor control, outcome detection

Kiến trúc này chia thành hai phần độc lập nhưng có liên kết:

- Chess learning pipeline: Huấn luyện model với tốc độ cao bằng trạng thái bàn cờ có cấu trúc, trước hết sử dụng chess simulator.
- Atari integration pipeline: Đưa agent đã huấn luyện vào game thật, xác nhận rằng nó có thể thực hiện đúng những nước đi đã chọn.

Tuy nhiên, không được coi `python-chess` và Atari Video Chess là hai môi trường hoàn toàn tương đương. Cần kiểm tra luật, điều kiện kết thúc ván, hành vi của đối thủ và khả năng điều khiển trước khi dùng kết quả simulator để kết luận về hiệu năng trên ALE.

## III. Khảo sát và xác minh môi trường ALE

Trước khi xây dựng model, phải hiểu rõ những dữ liệu mà VideoChess thực sự cung cấp.

### 1. Các đặc điểm đã xác minh

| Thành phần                | Thông tin           |
| ------------------------- | ------------------- |
| Environment               | `ALE/VideoChess-v5` |
| RGB observation           | `210 × 160 × 3`     |
| RAM observation           | 128 bytes           |
| Action space              | 10 hành động        |
| Frameskip mặc định        | 4                   |
| Sticky-action probability | 0.25                |
| Game modes hỗ trợ         | 0, 1, 2, 3, 4       |
| Game difficulty qua ALE   | 0                   |

[image](https://www.google.com/s2/favicons?domain=https://ale.farama.org\&sz=32)

Arcade Learning Environment Documentation

### 2. Phát hiện quan trọng từ mã nguồn ALE

Tôi đã kiểm tra trực tiếp file [VideoChess.cpp](https://github.com/Farama-Foundation/Arcade-Learning-Environment/blob/main/src/ale/games/supported/VideoChess.cpp) trong repository chính thức của ALE.

Mã nguồn xác định:

| Địa chỉ / thành phần | Chức năng                   |
| -------------------- | --------------------------- |
| RAM `0xE1`           | Theo dõi lượt chơi          |
| RAM `0xEE`           | Trạng thái checkmate        |
| RAM `0xE4`           | Đếm số nước đi của quân đen |
| `m_reward`           | Reward do ALE tính          |
| `m_terminal`         | Cờ báo kết thúc game        |

Đặc biệt: VideoChess có reward thắng/thua được định nghĩa trong ALE.

Mã nguồn đặt reward `+1` khi quân đen bị checkmate và `-1` khi quân trắng bị checkmate, sau đó đánh dấu terminal. Điều này có nghĩa là game có tín hiệu thưởng cuối ván, không phải bài toán hoàn toàn thiếu reward.

Nhưng reward này được tính theo kết quả của quân trắng. Khi agent chơi quân đen, phải quy đổi dấu để reward luôn phản ánh kết quả từ góc nhìn của agent.

Một chi tiết khác: mã nguồn còn ghi rõ Atari AI có thể mô phỏng các nước đi trong bộ nhớ khi đang tìm kiếm. Vì thế, không được đọc RAM một cách tùy tiện trong lúc máy đang suy nghĩ rồi coi đó là trạng thái bàn cờ thật.

Đây là một trong những nguyên nhân có thể làm hỏng hoàn toàn hệ thống state extraction nếu không phát hiện sớm.

### 3. Các nội dung cần khảo sát thực nghiệm

| Nội dung cần kiểm tra | Phương pháp                                | Kết quả cần đạt                       |
| --------------------- | ------------------------------------------ | ------------------------------------- |
| Game initialization   | Reset nhiều lần, lưu RGB/RAM               | Xác nhận trạng thái khởi đầu          |
| Cursor movement       | Gửi từng joystick action                   | Biết chính xác cách con trỏ di chuyển |
| Piece selection       | Chọn và bỏ chọn quân                       | Điều khiển được `FIRE`                |
| Move execution        | Thử e2e4, d2d4, g1f3                       | Thực hiện đúng nước đi                |
| Turn detection        | So sánh RAM và hình ảnh                    | Phân biệt lượt agent / lượt Atari     |
| Thinking detection    | Theo dõi RAM trong lúc Atari suy nghĩ      | Không đọc nhầm trạng thái tạm         |
| State extraction      | Đọc board từ RGB/RAM                       | Khôi phục đúng vị trí quân cờ         |
| Win/loss detection    | Đối chiếu RAM, reward và hình ảnh          | Xác định đúng kết quả                 |
| Game modes            | Kiểm tra từng mode được hỗ trợ             | Hiểu mức khó và thời gian phản hồi    |
| Special moves         | Kiểm tra nhập thành, en passant, phong cấp | Đồng bộ đúng với luật Atari           |

Tiêu chí hoàn thành giai đoạn này: Có một tài liệu `environment_analysis.md` mô tả rõ từng thành phần, kèm log và bằng chứng chạy thực tế. Chưa cần bất kỳ model học máy nào.

## IV. Giai đoạn 1 — Xây dựng nền tảng phần mềm và kiểm chứng môi trường

### 1.1. Thiết lập project

Ở giai đoạn đầu, repository cần có một cấu trúc đủ rõ để phát triển thành nhiều module mà không phải viết lại toàn bộ.

Cấu trúc đích được đề xuất:

```
atari-videochess-rl/
│
├── configs/
│   ├── environment.yaml
│   ├── pretrain.yaml
│   ├── dqn.yaml
│   └── evaluation.yaml
│
├── src/
│   └── videochess_rl/
│       ├── environments/
│       │   ├── chess_simulator.py
│       │   ├── atari_adapter.py
│       │   ├── board_extractor.py
│       │   ├── move_controller.py
│       │   └── reward.py
│       │
│       ├── agents/
│       │   ├── random_agent.py
│       │   ├── heuristic_agent.py
│       │   └── dqn_agent.py
│       │
│       ├── models/
│       │   ├── encoder.py
│       │   └── q_network.py
│       │
│       ├── training/
│       │   ├── replay_buffer.py
│       │   ├── pretrainer.py
│       │   └── dqn_trainer.py
│       │
│       ├── data/
│       │   ├── pgn_loader.py
│       │   ├── teacher_labeler.py
│       │   └── dataset.py
│       │
│       └── evaluation/
│           ├── arena.py
│           ├── metrics.py
│           └── tournament.py
│
├── scripts/
│   ├── smoke_test.py
│   ├── test_atari_moves.py
│   ├── generate_dataset.py
│   ├── pretrain.py
│   ├── train_rl.py
│   ├── evaluate.py
│   └── play_atari.py
│
├── tests/
├── notebooks/
├── docs/
├── reports/
├── requirements.txt
├── pyproject.toml
├── .gitignore
└── README.md
```

Đây là cấu trúc đích, không phải tất cả các file cần tạo ngay. Ban đầu chỉ tạo những module thực sự đang sử dụng.

### 1.2. Các thư viện chính

| Thư viện     | Chức năng                               |
| ------------ | --------------------------------------- |
| PyTorch      | Xây dựng và huấn luyện neural network   |
| Gymnasium    | API tương tác với environment           |
| ale-py       | Atari emulator và ALE                   |
| python-chess | Quản lý bàn cờ, luật cờ, nước đi hợp lệ |
| Stockfish    | Tạo nhãn chuyên gia trong training      |
| NumPy        | Xử lý dữ liệu và state representation   |
| OpenCV       | Phân tích frame Atari nếu cần           |
| TensorBoard  | Theo dõi training                       |
| Pytest       | Kiểm thử module                         |
| PyYAML       | Quản lý cấu hình                        |

`python-chess` có sẵn chức năng xác định legal moves, tạo FEN, kiểm tra checkmate, stalemate và các tình huống kết thúc ván. Không cần tự viết toàn bộ luật cờ.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://python-chess.readthedocs.io\&sz=32)

python-chess 1.11.2 documentation



### 1.3. Thiết lập hai loại environment

Tôi đề xuất triển khai hai interface có cùng phương thức:

```
class ChessEnvironment:    def reset(self):        ...    def get_legal_moves(self):        ...    def step(self, move):        ...    def get_board(self):        ...    def get_result(self):        ...
```

Environment A — Chess simulator

- Dùng `python-chess`.
- State là FEN hoặc `chess.Board`.
- Agent chọn nước đi hợp lệ.
- Environment thực hiện nước đi và trả lại trạng thái.
- Một opponent policy tạo nước đáp trả.
- Mỗi lần gọi `step()` tương ứng với một quyết định của agent và, nếu game chưa kết thúc, nước đáp trả của đối thủ.

Environment B — Atari wrapper

- Game chạy bằng `ALE/VideoChess-v5`.
- Board extractor đọc trạng thái hiện tại từ Atari.
- Agent chọn nước đi.
- Move controller chuyển nước đi thành các lệnh joystick.
- Environment chờ Atari xử lý, đọc trạng thái và reward.

Điều này giúp giữ nguyên một thuật toán training và một policy interface, trong khi có thể thay đổi backend.

### 1.4. Xây dựng Atari action wrapper

Đề xuất tách thành ba thành phần:

A. Board extractor

```
board = board_extractor.extract(observation, ram)
```

Kết quả cần bao gồm:

- Vị trí từng quân cờ.
- Lượt chơi.
- Vị trí con trỏ.
- Trạng thái chọn quân.
- Quyền nhập thành và en passant, được duy trì từ lịch sử nếu không thể đọc trực tiếp.
- Trạng thái đang suy nghĩ, đã thực hiện xong nước, hoặc kết thúc ván.

B. Move controller

```
move_controller.execute("e2e4")
```

Nó phải chuyển thành một chuỗi:

```
Move cursor to e2
→ Press FIRE
→ Move cursor to e4
→ Press FIRE
→ Verify board
```

C. State synchronizer

So sánh bàn cờ kỳ vọng với trạng thái thực tế của Atari.

Ví dụ:

```
Expected board after e2e4
             vs.
Observed board extracted from Atari

          Match?
       /          \
     Yes           No
      |             |
   Continue    Retry / recover
```

Bản thân `move_controller` không nên mặc định một lệnh joystick sẽ di chuyển đúng một ô. Cần hiệu chuẩn số frame, tốc độ di chuyển, hành vi giữ nút và sticky actions.

### 1.5. Kiểm thử wrapper

Tôi đề xuất kiểm thử theo mức độ tăng dần:

| Level | Bài kiểm thử                    | Tiêu chí                        |
| ----- | ------------------------------- | ------------------------------- |
| 1     | Điều khiển con trỏ              | Đi đến được ô mục tiêu          |
| 2     | Chọn và bỏ chọn quân            | Không bị kẹt trạng thái         |
| 3     | Thực hiện e2e4                  | Đúng bàn cờ kỳ vọng             |
| 4     | Thực hiện g1f3                  | Điều khiển đúng quân mã         |
| 5     | Thực hiện capture               | Quân bị bắt biến mất            |
| 6     | Chờ Atari đáp trả               | Nhận diện đúng nước của đối thủ |
| 7     | Chơi nhiều lượt liên tục        | Không lệch state                |
| 8     | Castling, en passant, promotion | Đúng luật thực tế               |
| 9     | Game kết thúc                   | Kết quả và reward chính xác     |
| 10    | Kiểm thử lặp lại qua nhiều seed | Hoạt động ổn định               |

Nên dùng cơ chế closed-loop control: thực hiện một phần thao tác, quan sát lại, rồi mới tiếp tục. Cách này an toàn hơn thực hiện một chuỗi hành động dài mà không kiểm tra.

Một điểm cần đặc biệt lưu ý: RAM API trả về 128 byte, trong khi mã nguồn ALE sử dụng các địa chỉ như `0xE1`. Không nên giả định có thể truy cập trực tiếp `observation[0xE1]`; cần xác minh cách ánh xạ địa chỉ RAM của emulator.

Điều kiện để chuyển giai đoạn: Wrapper có thể chơi nhiều lượt ổn định, phát hiện sai lệch thay vì âm thầm tiếp tục, và kết quả của các nước đi được xác thực từ trạng thái Atari.

## V. Giai đoạn 2 — Xác định chính xác MDP và thiết kế Chess RL Environment

Đây là phần học thuật nền tảng. Không nên bắt đầu huấn luyện khi chưa giải thích được state, action, transition và reward.

### 2.1. State space

Trạng thái không nên chỉ chứa một ma trận 8×8 biểu diễn vị trí quân.

Hai bàn cờ có cùng vị trí quân nhưng khác quyền nhập thành hoặc en passant có thể có các nước đi hợp lệ khác nhau.

Vì vậy, state tối thiểu phải bao gồm:

\\[ s=(B,t,c,e,h) \\]

Với:

- \\(B\\): vị trí các quân cờ.
- \\(t\\): bên đến lượt đi.
- \\(c\\): quyền nhập thành.
- \\(e\\): thông tin en passant.
- \\(h\\): thông tin lịch sử cần thiết cho quy tắc hòa hoặc điều kiện kết thúc.

Có thể bổ sung halfmove clock, repetition history và các thông tin phục vụ training.

### 2.2. Action space

Action ở mức chess move:

\\[ \mathcal A(s)=\\{\text{all legal chess moves at }s\\} \\]

Không sử dụng action space cố định gồm 10 joystick actions cho model chiến thuật.

Tập hành động thay đổi theo từng trạng thái, nhưng model có thể đánh giá từng nước ứng viên bằng cùng một Q-network.

### 2.3. Transition function

Một RL step nên được định nghĩa là:

\\(s_t\\) — Agent đến lượt

Agent chọn \\(a_t\\)

Thực hiện nước đi của agent

Nếu chưa kết thúc, opponent thực hiện nước đáp trả

\\(s\_{t+1},r_t,\text{done}\\)

Agent lại đến lượt, hoặc game kết thúc

Định nghĩa này có hai lợi ích:

- Q-learning có một góc nhìn nhất quán: mỗi state đầu bước đều đến lượt agent.
- Bellman update không nhầm lẫn giữa hành động của agent và hành động của đối thủ.

Nếu thay đổi đối thủ trong quá trình training, phân phối transition sẽ thay đổi. Đó là một đặc điểm quan trọng cần kiểm soát khi thiết kế curriculum và self-play.

### 2.4. Reward function

Tôi đề xuất bắt đầu từ reward đơn giản nhất:

\\[ r_t = \begin{cases} +1 & \text{Agent thắng}\\\ 0 & \text{Hòa hoặc đang chơi}\\\ -1 & \text{Agent thua} \end{cases} \\]

Đây là phiên bản terminal-reward-only.

Không thêm material reward ngay từ đầu. Lý do là chúng ta cần một baseline rõ ràng để biết thuật toán có khả năng học từ kết quả ván cờ hay không.

Sau này, nếu reward quá thưa, có thể thử reward shaping dựa trên:

\\[ r'\_t=r_t+\lambda\left(\gamma\Phi(s\_{t+1})-\Phi(s_t)\right) \\]

Trong đó \\(\Phi\\) là một hàm potential, chẳng hạn material advantage đã chuẩn hóa.

Dạng potential-based shaping này có cơ sở lý thuyết rõ ràng hơn so với cộng thưởng tùy ý cho mỗi lần bắt quân. Nó giúp giảm nguy cơ agent học cách tối đa hóa material reward nhưng lại bỏ qua mục tiêu thắng ván.

Reward gốc của Atari, reward của simulator và shaped reward phải được log riêng.

### 2.5. Những yếu tố cần tránh

- Không để model quan sát được nước đi tương lai của đối thủ.
- Không đưa đánh giá Stockfish vào observation khi inference.
- Không sử dụng FEN giả định mà bỏ qua việc xác minh trạng thái ALE.
- Không cho phép agent chơi nước bất hợp lệ rồi tự sửa âm thầm trong evaluation.
- Không dùng reward shaping trong training làm thước đo sức chơi cuối cùng.
- Không được mặc định `terminated=False` nghĩa là ván cờ vẫn đang diễn ra đúng luật nếu Atari đang ở một trạng thái UI chưa được xử lý.

Sản phẩm giai đoạn: Tài liệu `mdp_design.md`, simulator có interface ổn định, test cho luật cờ, reward và các transition.

## VI. Giai đoạn 3 — Xây dựng các baseline trước khi dùng neural network

Baseline là thành phần bắt buộc nếu muốn chứng minh thuật toán học được điều gì.

### 3.1. Baseline A — Random Legal Agent

Agent chọn ngẫu nhiên một nước trong tập legal moves:

\\[ \pi(a\mid s)=\frac{1}{|\mathcal A(s)|} \\]

Mục đích không phải tạo ra một agent mạnh, mà là kiểm thử toàn bộ chu trình:

`reset → observation → legal moves → action → opponent → reward → done`.

Khi random agent có thể hoàn thành ván cờ trong simulator, ta biết rằng môi trường huấn luyện đã có nền tảng hoạt động.

### 3.2. Baseline B — Material-based Heuristic Agent

Dùng một hàm đánh giá rất đơn giản:

\\[ H(s)=\sum\_{p\in \mathrm{ours}}v(p)-\sum\_{p\in\mathrm{theirs}}v(p) \\]

Với giá trị quân cờ minh họa:

| Quân   | Giá trị |
| ------ | ------- |
| Pawn   | 1       |
| Knight | 3       |
| Bishop | 3       |
| Rook   | 5       |
| Queen  | 9       |

King không được xử lý như một quân có thể đánh đổi thông thường; checkmate phải được ưu tiên tuyệt đối.

Agent thử từng nước hợp lệ, tính material balance ở trạng thái kế tiếp và chọn nước tốt nhất theo heuristic này.

Đây là một baseline chiến thuật một bước, không sử dụng Stockfish.

### 3.3. Baseline C — Material + King Safety + Mobility

Mở rộng heuristic bằng:

\\[ H(s)=w_m M(s)+w_k K(s)+w_b B(s) \\]

Trong đó:

- \\(M(s)\\): material balance.
- \\(K(s)\\): king safety.
- \\(B(s)\\): mobility hoặc mức độ kiểm soát trung tâm.

Không cần xây một chess engine phức tạp. Mục đích của baseline này là xác định liệu neural network có học được gì vượt qua một vài quy tắc chơi cờ thủ công hay không.

### 3.4. Benchmark ban đầu

Dùng các baseline đấu với nhau và với nhiều opponent policies:

| Agent                 | Random opponent | Heuristic opponent | Atari |
| --------------------- | --------------- | ------------------ | ----- |
| Random legal          | Đo              | Đo                 | Đo    |
| Material-based        | Đo              | Đo                 | Đo    |
| Material + positional | Đo              | Đo                 | Đo    |

Ở lần đánh giá đầu, chưa cần số ván quá lớn. Sau khi pipeline ổn định, tăng số ván để có khoảng tin cậy có ý nghĩa.

Cần đo thêm tỷ lệ thực hiện nước thành công trên ALE. Nếu heuristic agent chơi tốt trong simulator nhưng thất bại trên Atari vì wrapper, đó là lỗi tích hợp, không phải lỗi thuật toán.

Điều kiện chuyển giai đoạn: Baseline chạy được, kết quả được lưu, các phép đo phân biệt rõ hiệu năng chiến thuật và độ tin cậy của wrapper.

## VII. Giai đoạn 4 — Thiết kế state representation và neural network

### 4.1. Không huấn luyện trực tiếp trên RGB ngay từ đầu

Việc sử dụng ảnh Atari có thể trở thành một thí nghiệm bổ sung, nhưng không nên là phương án chính.

Chúng ta đã được phép trích xuất bàn cờ, do đó nên biểu diễn dữ liệu ở dạng tensor có cấu trúc.

Một vị trí cờ có thể mã hóa thành:

\\[ X\in\mathbb R^{C\times8\times8} \\]

Với \\(C\\) là số lượng feature planes.

### 4.2. Các feature planes được đề xuất

| Nhóm                   | Số planes đề xuất | Ý nghĩa                                 |
| ---------------------- | ----------------- | --------------------------------------- |
| White pieces           | 6                 | Pawn, knight, bishop, rook, queen, king |
| Black pieces           | 6                 | Sáu loại quân đen                       |
| Castling rights        | 4                 | K, Q, k, q                              |
| Side to move           | 1                 | Lượt trắng hoặc đen                     |
| En passant             | 1                 | Ô en passant khả dụng                   |
| Player perspective     | 1                 | Bên mà model đang đánh giá              |
| Halfmove clock         | 1                 | Giá trị chuẩn hóa                       |
| Repetition information | 1                 | Thông tin lặp vị trí, nếu có            |
| Tổng ban đầu           | 21                | Có thể điều chỉnh                       |

Đây là cấu hình đề xuất để thử nghiệm, không phải số channels cố định đã được chứng minh là tối ưu.

Cần chú ý rằng thông tin repetition có thể đòi hỏi lịch sử trạng thái. Nếu chỉ có FEN hiện tại thì không luôn xác định được số lần lặp.

### 4.3. Kiến trúc neural network

Bắt đầu với một CNN nhỏ:

```
Input tensor (C × 8 × 8)
          │
          ▼
   Conv2D + ReLU
          │
          ▼
   Conv2D + ReLU
          │
          ▼
   Conv2D + ReLU
          │
          ▼
  Global Pooling / Flatten
          │
          ▼
    Fully Connected
          │
          ▼
     Scalar Q-value
```

Cấu hình khởi đầu để benchmark:

| Thành phần             | Giá trị đề xuất                        |
| ---------------------- | -------------------------------------- |
| Convolution layers     | 3                                      |
| Hidden channels        | 64                                     |
| Kernel size            | 3×3                                    |
| Activation             | ReLU                                   |
| Hidden fully connected | 128                                    |
| Output                 | 1 scalar                               |
| Optimizer              | Adam hoặc AdamW                        |
| Initial learning rate  | \\(10^{-3}\\) để thử nghiệm supervised |
| Loss                   | Huber hoặc MSE                         |

Các giá trị trên là cấu hình ban đầu. Cần dựa vào throughput và validation results để quyết định thay đổi.

Tôi chưa đề xuất ResNet lớn, Transformer hay mạng policy-value kiểu AlphaZero, vì lợi ích của chúng chưa chắc bù được chi phí trong bối cảnh hiện tại.

### 4.4. Đánh giá từng nước đi bằng afterstate

Ví dụ state hiện tại có 20 nước hợp lệ.

Với mỗi nước \\(a_i\\):

1. Sao chép hoặc tạm áp dụng nước đi lên bàn cờ.
2. Tạo tensor biểu diễn trạng thái sau nước đi.
3. Giữ nguyên góc nhìn của player đang ra quyết định.
4. Đưa tensor vào neural network.
5. Nhận \\(Q\_\theta(s,a_i)\\).

Có thể xử lý toàn bộ candidate tensors trong cùng một batch để giảm overhead.

Pseudo-code:

```
def select_move(board, model):    moves = list(board.legal_moves)    player = board.turn    candidates = []    for move in moves:        board.push(move)        candidates.append(            encode_afterstate(board, player)        )        board.pop()    q_values = model(batch(candidates))    best_index = q_values.argmax()    return moves[best_index]
```

Điểm mạnh của cách này là không cần định nghĩa một output neuron riêng cho mọi nước đi UCI có thể tồn tại.

Điểm yếu là phải đánh giá nhiều trạng thái ứng viên. Tuy nhiên, với mạng CNN nhỏ và batch inference, đây là mức độ phức tạp chấp nhận được để thử nghiệm.

### 4.5. Kiểm thử neural network

Trước khi training, cần xác nhận:

- Encoder tạo đúng tensor cho initial position.
- Sau `e2e4`, tensor có đúng vị trí quân tốt.
- Các trạng thái khác quyền nhập thành tạo ra encoding khác nhau.
- Góc nhìn trắng/đen không bị đảo dấu đánh giá.
- Model xử lý được các batch có số nước ứng viên khác nhau.
- Output không xuất hiện `NaN` hoặc `Inf`.
- Gradient có thể truyền qua toàn bộ model.
- Lưu và tải checkpoint cho kết quả inference giống nhau.

Một sanity test quan trọng là overfit một tập cực nhỏ. Nếu model không thể học thuộc vài chục mẫu có nhãn, chưa nên chuyển sang dataset lớn.

Sản phẩm giai đoạn: `encoder.py`, `q_network.py`, unit tests và một model có thể forward/backward thành công.

## VIII. Giai đoạn 5 — Xây dựng dữ liệu chuyên gia bằng Stockfish

Đây là giai đoạn tạo lợi thế lớn nhất về tốc độ học.

### 5.1. Vì sao phải pretrain?

Một Q-network khởi tạo ngẫu nhiên chưa hiểu bất cứ điều gì về cờ vua.

Ví dụ, nó không biết:

- Queen thường có giá trị cao hơn pawn.
- Để vua bị checkmate là thua.
- Một nước ăn quân có thể dẫn đến mất quân lớn hơn.
- Các vị trí có khả năng bị chiếu hết cần được ưu tiên hoặc tránh.

Học những kiến thức này chỉ thông qua thắng/thua cuối ván sẽ rất chậm.

Stockfish cung cấp một nguồn tín hiệu dày đặc hơn: đánh giá sức mạnh của nhiều trạng thái và nước đi, nhờ đó model có một điểm khởi đầu tốt hơn.

### 5.2. Nguồn dữ liệu

Tôi đề xuất ba nguồn:

Nguồn A — Các ván cờ PGN

Sử dụng những ván cờ có chất lượng tương đối tốt để tạo các trạng thái từ khai cuộc, trung cuộc đến tàn cuộc.

Nguồn B — Các thế cờ chiến thuật

Tập trung vào những tình huống:

- Ăn quân và tránh mất quân.
- Chiếu hết trong vài nước.
- Đối phó với đe dọa trực tiếp.
- Phong cấp tốt.
- Đổi quân khi đang hơn hoặc kém material.

Nguồn C — Trạng thái sinh từ chính agent

Sau khi có model sơ bộ, dùng những ván do agent chơi để tìm những vị trí mà model thường đánh giá sai.

Nguồn C giúp giảm hiện tượng distribution shift: model chỉ quen những vị trí từ ván đấu chất lượng cao nhưng không biết xử lý trạng thái kỳ lạ do chính nó tạo ra.

### 5.3. Tạo nhãn

Không chỉ lấy `bestmove` của Stockfish. Chúng ta nên có nhãn cho nhiều nước ứng viên để huấn luyện mạng \\(Q(s,a)\\).

Ví dụ:

```
State: FEN position S

Candidate 1: e2e4
Candidate 2: d2d4
Candidate 3: g1f3
Candidate 4: a2a3
```

Với mỗi candidate, tạo trạng thái sau nước đi và phân tích bằng Stockfish.

Không nhất thiết phải đánh giá toàn bộ legal moves của mọi position ngay từ đầu, vì sẽ tốn rất nhiều CPU.

Chiến lược lấy mẫu ban đầu:

- Nước tốt nhất do Stockfish đề xuất.
- Một vài nước thay thế tương đối tốt.
- Một số nước ngẫu nhiên.
- Một số nước có khả năng gây sai lầm chiến thuật.

Với cách này, mạng được tiếp xúc với cả nước tốt và nước kém, thay vì chỉ học những thế cờ sau nước chuyên gia.

### 5.4. Chuyển Stockfish evaluation thành training target

Stockfish có thể trả về centipawn score hoặc mate score.

Ta cần chuẩn hóa điểm về một khoảng giá trị ổn định, chẳng hạn:

\\[ q\_{\mathrm{teacher}} =\tanh\left(\frac{c}{\tau}\right) \\]

Trong đó \\(c\\) là đánh giá centipawn quy về góc nhìn của agent, còn \\(\tau\\) là hệ số chuẩn hóa cần chọn.

Ví dụ có thể bắt đầu với \\(\tau=400\\), sau đó kiểm tra phân phối nhãn.

Đối với mate score, cần xử lý riêng thay vì coi `mate in 3` là một centipawn score thông thường.

Một chi tiết rất quan trọng: Stockfish đánh giá vị trí từ một góc nhìn cụ thể, thường theo side-to-move trong kết quả UCI. Sau khi agent đi quân, side-to-move đổi sang đối thủ. Phải chuyển điểm về đúng bên đang được model đánh giá, nếu không model có thể học ngược mục tiêu.

Tài liệu Stockfish cũng cho biết centipawn hiện đại không đơn giản là số phần trăm của một quân tốt và có hệ thống hiệu chuẩn riêng. Vì vậy, phép biến đổi trên nên được coi là thiết kế nhãn huấn luyện, không phải xác suất thắng đã được hiệu chuẩn.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 5.5. Cấu trúc dataset

Mỗi mẫu nên chứa:

```
position_id
source_game_id
source_fen
candidate_move_uci
afterstate_fen
player_color
teacher_score
teacher_depth
teacher_nodes
is_best_move
game_phase
```

Tùy thí nghiệm có thể thêm teacher move rank và thông tin terminal.

Để tránh data leakage, phải chia train/validation/test theo game hoặc nhóm vị trí gốc, không chia ngẫu nhiên từng candidate row. Nếu cùng một trạng thái có nhiều candidate và xuất hiện ở cả train lẫn test, kết quả đánh giá có thể bị thổi phồng.

### 5.6. Quy mô thử nghiệm

Không nên sinh ngay hàng triệu mẫu.

| Mức                  | Quy mô đề xuất           | Mục đích                     |
| -------------------- | ------------------------ | ---------------------------- |
| Prototype            | 1.000 positions          | Kiểm tra pipeline            |
| Initial training     | 10.000–30.000 positions  | Đánh giá khả năng học        |
| Expanded training    | 50.000–100.000 positions | Chỉ mở rộng nếu có lợi ích   |
| Hard-position mining | Theo lỗi model           | Tập trung cải thiện điểm yếu |

Một position có thể tạo ra nhiều candidate samples. Các con số là quy mô khảo sát, không phải cam kết rằng chừng đó dữ liệu đủ đạt Elo mục tiêu.

Quan trọng hơn số mẫu là sự đa dạng của trạng thái, chất lượng teacher labels và khả năng tránh overfitting.

Sản phẩm giai đoạn: Dataset có thể tái tạo, tập validation/test độc lập, thống kê phân phối và mã nguồn sinh nhãn.

## IX. Giai đoạn 6 — Supervised Pretraining

Đây là giai đoạn biến mạng ngẫu nhiên thành một model đã học được kiến thức cờ vua từ Stockfish.

### 6.1. Mục tiêu

Huấn luyện:

\\[ Q\_\theta(s,a)\approx q\_{\mathrm{teacher}}(s,a) \\]

Bằng cách tối thiểu hóa:

\\[ \mathcal L\_{\mathrm{sup}} =\frac{1}{N}\sum\_{i=1}^N \operatorname{Huber} \left(Q\_\theta(s_i,a_i)-q_i^{\mathrm{teacher}}\right) \\]

Với afterstate network, \\(Q\_\theta(s,a)\\) chính là giá trị dự đoán khi đưa trạng thái sau nước \\(a\\) vào mạng, kèm thông tin góc nhìn của player.

Đây là supervised learning, chưa phải reinforcement learning.

### 6.2. Training pipeline

```
Load expert dataset
       │
       ▼
Encode candidate afterstates
       │
       ▼
Split train / validation / test
       │
       ▼
Initialize Q-network
       │
       ▼
Forward pass
       │
       ▼
Compute supervised loss
       │
       ▼
Backpropagation
       │
       ▼
Optimizer step
       │
       ▼
Validation + checkpoint
```

Lưu checkpoint tốt nhất theo validation performance, không chỉ checkpoint của epoch cuối cùng.

### 6.3. Metrics để đánh giá pretraining

Không chỉ theo dõi train loss.

| Metric                         | Mục đích                                     |
| ------------------------------ | -------------------------------------------- |
| Validation loss                | Kiểm tra khả năng khái quát                  |
| MAE trên normalized evaluation | Độ chính xác đánh giá trạng thái             |
| Teacher top-1 agreement        | Model chọn trùng nước tốt nhất bao nhiêu lần |
| Top-k agreement                | Nước model chọn có thuộc nhóm nước tốt không |
| Move ranking correlation       | Model có xếp hạng nước đúng tương đối không  |
| Tactical puzzle accuracy       | Có nhận ra chiến thuật cơ bản không          |
| Gameplay win/draw/loss         | Kiểm tra sức chơi thực tế                    |

Move ranking quan trọng hơn chỉ số regression loss.

Một model có thể dự đoán các giá trị trạng thái tương đối chính xác nhưng vẫn chọn sai nước tốt nhất khi hai candidate có điểm gần nhau.

Vì thế, sau khi xây dựng regression baseline, có thể cải tiến bằng một ranking loss.

Ví dụ, nếu Stockfish đánh giá nước \\(a_i\\) tốt hơn \\(a_j\\), ta muốn:

\\[ Q\_\theta(s,a_i)>Q\_\theta(s,a_j) \\]

Có thể bổ sung pairwise ranking loss hoặc softmax ranking loss. Đây là cải tiến tùy chọn, chỉ thực hiện nếu bài toán chọn nước còn kém trong khi regression đã hội tụ.

### 6.4. Kiểm thử sức chơi của model pretrain

Sau pretraining:

- Tắt hoàn toàn Stockfish trong agent process.
- Load neural network từ checkpoint.
- Dùng legal-move generation của `python-chess`.
- Chọn nước bằng neural scores.
- Đấu với random, heuristic và các opponent đã định nghĩa.

Kết quả này là supervised-only baseline.

Phải lưu nó độc lập, vì đây sẽ là mốc so sánh để chứng minh RL có cải thiện hay không.

### 6.5. Các cải tiến pretraining theo thứ tự

| Mức | Cải tiến                   | Khi nào thực hiện                        |
| --- | -------------------------- | ---------------------------------------- |
| P0  | Value regression           | Luôn thực hiện                           |
| P1  | Tăng độ đa dạng trạng thái | Khi validation cho thấy overfitting      |
| P2  | Bổ sung tactical positions | Khi model dễ mắc lỗi chiến thuật         |
| P3  | Pairwise ranking loss      | Khi xếp hạng nước kém                    |
| P4  | Hard-negative mining       | Khi model có những sai lầm lặp lại       |
| P5  | Mạng lớn hơn               | Chỉ khi model nhỏ thật sự thiếu capacity |

Không nên mặc định tăng số layer hay số parameters sẽ làm agent chơi tốt hơn.

Điều kiện chuyển giai đoạn: Model pretrain có thể tự chơi mà không dùng Stockfish, có sức chơi đo được, và checkpoint được lưu để so sánh với RL fine-tuning.

## X. Giai đoạn 7 — Reinforcement Learning với Double DQN

Đây là thành phần cốt lõi của assignment.

### 7.1. Mục tiêu RL

Sau supervised pretraining, neural network học cách bắt chước đánh giá của Stockfish.

Nhưng chúng ta muốn nó tiếp tục học dựa trên reward nhận được khi tự chơi.

Vì vậy, chuyển sang Double DQN.

Ở giai đoạn này, model cập nhật giá trị hành động từ các transition:

\\[ (s_t,a_t,r_t,s\_{t+1},d_t) \\]

Trong đó \\(s\_{t+1}\\) là trạng thái khi agent đến lượt tiếp theo, sau khi đã xử lý nước đáp trả của đối thủ; \\(d_t\\) là tín hiệu kết thúc ván.

### 7.2. Các thành phần bắt buộc

Online Q-network \\(Q\_\theta\\)

Mạng dùng để chọn hành động trong training và được cập nhật bằng gradient descent.

Target Q-network \\(Q\_{\theta^-}\\)

Bản sao cập nhật chậm hơn của online network, giúp Bellman targets ổn định hơn.

Experience replay buffer

Lưu các transition đã trải nghiệm và lấy mini-batch ngẫu nhiên để giảm tương quan giữa những update liên tiếp.

Exploration policy

Sử dụng ε-greedy để agent vẫn khám phá những nước đi khác thay vì chỉ chọn nước có Q-value cao nhất.

### 7.3. Double DQN update

Với transition chưa kết thúc:

\\[ a^\*\_{t+1}= \arg\max\_{a'\in\mathcal A(s\_{t+1})} Q\_\theta(s\_{t+1},a') \\]

\\[ y_t=r_t+\gamma Q\_{\theta^-}(s\_{t+1},a^\*\_{t+1}) \\]

Với transition kết thúc:

\\[ y_t=r_t \\]

Sau đó:

\\[ \mathcal L\_{\mathrm{TD}} = \operatorname{Huber} \left(Q\_\theta(s_t,a_t)-y_t\right) \\]

Điểm khác biệt so với DQN thường là:

- Online network chọn nước tốt nhất ở trạng thái tiếp theo.
- Target network đánh giá nước được chọn.

Cơ chế này giúp giảm maximization bias.

Một điều kiện quan trọng: hai mạng phải sử dụng cùng một định nghĩa \\(Q(s,a)\\), cùng encoding, cùng góc nhìn player và cùng hệ reward.

### 7.4. Replay buffer

Mỗi transition nên lưu:

```
Transition(    state,    action,    reward,    next_state,    terminated,    truncated,    player_color)
```

Ngoài ra, có thể lưu `opponent_id`, `game_id` và `episode_step` để phục vụ phân tích.

Đặc biệt cần phân biệt:

- `terminated`: Ván cờ thật sự kết thúc.
- `truncated`: Episode bị dừng do giới hạn bước hoặc giới hạn tính toán.

Không được vô tình áp dụng terminal Bellman target cho mọi trường hợp truncation. Cách xử lý bootstrap phải nhất quán với định nghĩa horizon và dữ liệu trạng thái.

### 7.5. Exploration policy

Bắt đầu bằng ε-greedy:

\\[ a_t= \begin{cases} \text{random legal move}, & \text{với xác suất }\epsilon\\\ \arg\max_a Q\_\theta(s_t,a), & \text{ngược lại} \end{cases} \\]

Vì model đã qua pretraining, không nên bắt đầu với ε quá lớn như một DQN khởi tạo ngẫu nhiên.

Có thể thử:

- Initial epsilon: 0.20.
- Final epsilon: 0.05.
- Giảm dần theo số decision steps.

Đây là cấu hình khởi đầu để tuning, không phải giá trị mặc định tối ưu.

### 7.6. Cấu hình Double DQN thử nghiệm

| Hyperparameter               | Điểm khởi đầu                           |
| ---------------------------- | --------------------------------------- |
| Discount factor \\(\gamma\\) | 0.99                                    |
| Learning rate                | \\(10^{-4}\\)                           |
| Batch size                   | 64                                      |
| Replay buffer capacity       | 50.000–100.000 transitions              |
| Replay warm-up               | Khoảng 2.000 transitions                |
| Initial epsilon              | 0.20                                    |
| Minimum epsilon              | 0.05                                    |
| Target update                | Mỗi 1.000 learner updates để thử nghiệm |
| Loss                         | Huber                                   |
| Gradient clipping            | Norm 10                                 |
| Optimizer                    | Adam hoặc AdamW                         |

Nếu nguồn dữ liệu quá hạn chế, có thể giảm batch size và buffer size. Nếu update không ổn định, thử giảm learning rate, tăng target update interval hoặc dùng soft target updates.

Không được thay đổi đồng thời quá nhiều hyperparameters, vì sẽ rất khó xác định thay đổi nào gây ra tác động.

### 7.7. Quy trình training

Load pretrained Q-network

Initialize target network + replay buffer

Reset chess environment

Training loop

Select move → Execute → Observe reward → Store transition → Sample batch → Double DQN update

Periodic target network update

Evaluation → Save best checkpoint

Pseudo-code đơn giản:

```
online_q.load_state_dict(pretrained_weights)target_q.load_state_dict(online_q.state_dict())for episode in range(num_episodes):    state = env.reset()    while not env.is_done():        legal_moves = env.get_legal_moves()        action = epsilon_greedy(            online_q, state, legal_moves        )        next_state, reward, done, info = env.step(action)        replay_buffer.add(            state, action, reward, next_state,            info["terminated"], info["truncated"]        )        if len(replay_buffer) >= warmup_size:            batch = replay_buffer.sample(batch_size)            loss = double_dqn_update(                online_q, target_q, batch            )        if learner_steps % target_interval == 0:            target_q.load_state_dict(                online_q.state_dict()            )        state = next_state    evaluate_and_checkpoint()
```

Đây là pseudo-code kiến trúc. Trong implementation thật, việc sampling next-state legal moves, tính target với `torch.no_grad()`, xử lý terminal và cập nhật optimizer cần được triển khai đầy đủ.

### 7.8. Một khác biệt quan trọng giữa simulator và Atari

Trong simulator, một bước học có thể tương ứng với một nước của agent và một nước đáp trả của đối thủ.

Trong Atari, cùng một quyết định có thể phải trải qua rất nhiều lệnh joystick.

Tôi đề xuất định nghĩa discount factor theo agent decision steps, thay vì theo từng raw ALE frame, để nhất quán với simulator.

Nếu sau này muốn mô hình hóa chi tiết thời lượng macro-action, có thể nghiên cứu Semi-MDP discounting với \\(\gamma^k\\), trong đó \\(k\\) là thời lượng của macro-action theo đơn vị thời gian đã chọn.

Không nên trộn hai định nghĩa discounting trong cùng một replay buffer.

## XI. Giai đoạn 8 — Curriculum Learning và Opponent Design

Đây là giai đoạn rất đáng đầu tư vì agent đang chơi cờ vua, không phải một môi trường Atari ngắn với phần thưởng liên tục.

### 8.1. Vì sao không nên chỉ self-play từ đầu?

Một model mới pretrain chưa chắc có đủ khả năng tạo ra những ván cờ chất lượng.

Nếu cho hai bản sao yếu của model đấu với nhau liên tục, có thể xảy ra:

- Cả hai thực hiện những nước sai giống nhau.
- Agent không học cách trừng phạt sai lầm chiến thuật.
- Dữ liệu tập trung vào một số dạng ván cờ nhất định.
- Model cải thiện khả năng đấu với chính nó nhưng không cải thiện với đối thủ bên ngoài.

Vì vậy, tôi ưu tiên opponent pool.

### 8.2. Các đối thủ trong training

| Opponent                    | Vai trò                                 |
| --------------------------- | --------------------------------------- |
| Random legal                | Kiểm tra khả năng khai thác sai lầm dễ  |
| Material heuristic          | Học giữ quân và tránh mất quân đơn giản |
| Positional heuristic        | Tạo đối thủ có hành vi tốt hơn          |
| Stockfish giới hạn sức mạnh | Tạo thử thách khó hơn trong training    |
| Frozen snapshots của model  | Self-play với các phiên bản trước       |
| Atari Video Chess           | Fine-tuning trên môi trường đích        |

Stockfish được phép đóng vai trò đối thủ trong training, theo ràng buộc đã xác định. Khi inference, đối thủ của agent trong demo là Atari hoặc người chơi, không phải một thành phần của policy.

### 8.3. Curriculum theo sức mạnh

Level A — Easy

Random / weak heuristic

Level B — Intermediate

Heuristics / past models

Level C — Stronger Opponents

Limited-strength Stockfish during training

Mixed Opponent Pool

Trộn nhiều đối thủ thay vì chỉ một mức cố định

Điều kiện nâng độ khó không nên dựa vào số episode cố định. Hãy dựa vào evaluation:

- Tỷ lệ thắng trước đối thủ hiện tại đã đạt ngưỡng đề ra.
- Không còn cải thiện rõ sau một số đợt kiểm thử.
- Model vẫn giữ được hiệu năng trước các đối thủ dễ hơn.

Một agent chỉ cần thắng random và heuristic không chứng minh được nó đã chơi cờ tốt. Cần tiếp tục mở rộng đánh giá.

### 8.4. Tránh catastrophic forgetting

Khi fine-tune với reward cuối ván, model có thể mất một phần kiến thức từ pretraining.

Các phương án cải tiến theo thứ tự:

1. Giảm learning rate.
2. Sử dụng early stopping theo gameplay evaluation.
3. Kết hợp replay từ các đối thủ khác nhau.
4. Trộn một lượng nhỏ expert samples vào training với auxiliary supervised loss.
5. Thử cố định một phần encoder trong giai đoạn đầu rồi unfreeze.

Nếu chọn phương án 4, phải báo cáo rõ rằng training không còn là Double DQN thuần, mà là một hybrid objective gồm supervised và TD losses:

\\[ \mathcal L= \mathcal L\_{\mathrm{TD}} +\beta\mathcal L\_{\mathrm{sup}} \\]

Đây là một mở rộng hợp lệ, nhưng cần kiểm tra riêng liệu phần supervised regularization có thực sự cải thiện kết quả không.

### 8.5. Kết quả bắt buộc của giai đoạn RL

Phải giữ được ít nhất ba checkpoints:

- `random_init` hoặc baseline network chưa pretrain, nếu triển khai so sánh.
- `pretrained_best` — Kết quả tốt nhất sau supervised learning.
- `rl_best` — Kết quả tốt nhất sau RL fine-tuning.

Không ghi đè lên checkpoint tốt nhất chỉ vì bước huấn luyện sau đã chạy xong.

Điều kiện chuyển giai đoạn: Có learning curves, có checkpoint trước và sau RL, có đánh giá trên cùng benchmark, và giải thích được liệu RL có đem lại cải thiện hay không.

## XII. Giai đoạn 9 — Tích hợp RL Agent với Atari Video Chess

Đến đây, model đã học chơi cờ trong simulator. Bây giờ cần xác minh liệu kiến thức đó có chuyển sang Atari được không.

### 9.1. Quy trình inference hoàn chỉnh

ALE/VideoChess-v5

RGB + RAM observation

Board Extraction + State Validation

Legal Move Generation

Trained Q-network

Evaluate candidates → argmax Q

Move Controller

Execute Atari Actions + Verify

Điều kiện đặc biệt quan trọng: trạng thái đầu vào phải thực sự bắt nguồn từ game Atari.

Không được tạo một ván cờ riêng trong `python-chess`, để model chơi trên đó rồi chỉ hiển thị hình Atari mang tính minh họa.

Một shadow board bằng `python-chess` có thể được sử dụng để theo dõi lịch sử các nước, nhưng phải được đồng bộ và đối chiếu với trạng thái thật từ emulator.

### 9.2. Ba lớp đánh giá tích hợp

Integration Level 1 — Open-loop demonstration

Đưa một trạng thái đã biết vào network, chọn nước và yêu cầu Atari thực hiện.

Mục đích: chứng minh các module có thể kết nối với nhau.

Integration Level 2 — Closed-loop gameplay

Mỗi nước đi đều đi qua quy trình:

`observe → validate → decide → execute → verify`.

Không phụ thuộc vào một chuỗi thao tác Atari được hard-code sẵn.

Integration Level 3 — Full-game evaluation

Chạy các ván hoàn chỉnh:

- Có nước đi của Atari.
- Có checkmate và các tình huống kết thúc.
- Có thống kê thắng/hòa/thua.
- Có thể replay lại các ván.
- Không sử dụng dữ liệu Stockfish trong lúc agent chọn nước.

### 9.3. Kiểm thử trên cấu hình mặc định

Trong giai đoạn debug, có thể thử giảm sự ngẫu nhiên của emulator để dễ tìm lỗi.

Nhưng evaluation chính thức cần sử dụng lại những tham số đã định nghĩa của `ALE/VideoChess-v5`, trong đó có `frameskip=4` và `repeat_action_probability=0.25`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ale.farama.org\&sz=32)

Arcade Learning Environment Documentation



Cũng cần đánh giá các mode được hỗ trợ. Mã nguồn ALE lưu ý những level cao hơn có thể gặp lỗi game khiến máy đi nhiều nước liên tiếp, nên chỉ hỗ trợ năm game modes đầu tiên. Không nên tự suy ra mapping từ mode index sang các level trên giao diện nếu chưa kiểm tra.

### 9.4. Fine-tuning trên Atari

Đây là bước tùy chọn sau khi integration đã ổn định.

Có thể cho model tiếp tục chơi với Atari và đưa các transition vào replay buffer.

Lợi ích:

- Thích nghi với chính opponent policy của Atari.
- Giảm khoảng cách giữa simulator và môi trường đích.
- Có thêm bằng chứng về khả năng học trực tiếp qua tương tác ALE.

Hạn chế lớn nhất là tốc độ tạo trải nghiệm: mỗi nước cờ có thể yêu cầu nhiều bước điều khiển và thời gian suy nghĩ của Atari.

Vì vậy, tôi không đề xuất lấy ALE làm nguồn trải nghiệm chính trong toàn bộ training. Hãy dùng simulator để học chiến lược, sau đó cân nhắc Atari fine-tuning nếu throughput đủ tốt.

## XIII. Giai đoạn 10 — Evaluation và Experimental Design

Đây là giai đoạn quyết định chất lượng học thuật của assignment.

Một model có thể chơi một ván trông tương đối tốt, nhưng điều đó chưa đủ để khẳng định nó có sức chơi mạnh hoặc RL thật sự hiệu quả.

### 10.1. Bộ metrics chính

| Nhóm              | Metrics                                   |
| ----------------- | ----------------------------------------- |
| Gameplay          | Win rate, draw rate, loss rate            |
| Playing strength  | Match score, estimated relative Elo       |
| Model quality     | Teacher agreement, tactical accuracy      |
| RL learning       | TD loss, reward curve, Q-value statistics |
| Atari integration | Move execution success, desync rate       |
| Efficiency        | Time per move, training throughput        |
| Reliability       | Kết quả theo nhiều random seeds           |

### 10.2. Gameplay evaluation

Điểm số trong một trận đấu:

\\[ S=\frac{W+0.5D}{N} \\]

Trong đó:

- \\(W\\): số ván thắng.
- \\(D\\): số ván hòa.
- \\(N\\): tổng số ván.

Ví dụ, 40 thắng, 20 hòa và 40 thua cho match score bằng 0,50.

Nên đánh giá nhiều ván với seed và đối thủ được cố định từ trước, đổi màu quân khi backend cho phép và báo cáo khoảng tin cậy.

Không chỉ báo cáo một ván thắng đẹp nhất.

### 10.3. Đánh giá mục tiêu 1500 Elo

Cần lựa chọn một chuẩn Elo rõ ràng.

Có thể sử dụng match results với một pool đối thủ được hiệu chuẩn để ước lượng relative rating. Tuy nhiên, rating chỉ có ý nghĩa trong phạm vi pool và điều kiện thi đấu đó.

Tôi đề xuất ưu tiên hai loại benchmark:

Benchmark A — Sức chơi trong simulator

Dùng các opponent policies cố định, cùng giới hạn tính toán và tập test games, để so sánh các checkpoints.

Benchmark B — Hiệu năng thực tế trên Atari

Đo tỷ lệ thắng/hòa/thua ở các modes, số nước đi hoàn thành, lỗi điều khiển và thời gian kết thúc ván.

Nếu được phép dùng Stockfish như một đối thủ hoặc công cụ chấm điểm offline độc lập, có thể bổ sung kiểm định sức chơi. Stockfish không được tham gia chọn nước thay agent. Nếu quy định cấm mọi hình thức chạy engine ngoài training, chỉ sử dụng benchmark không có Stockfish.

### 10.4. Ablation study

Tôi đề xuất có ít nhất bốn thực nghiệm:

| ID | Phương pháp                      | Điều cần chứng minh         |
| -- | -------------------------------- | --------------------------- |
| E0 | Heuristic agent                  | Mức chất lượng không học    |
| E1 | Double DQN from scratch          | RL thuần học được bao nhiêu |
| E2 | Stockfish supervised pretraining | Pretraining mang lại gì     |
| E3 | Pretraining + Double DQN         | RL có cải thiện E2 không    |

Nếu còn khả năng, bổ sung:

| ID | Phương pháp            | Điều cần chứng minh                                  |
| -- | ---------------------- | ---------------------------------------------------- |
| E4 | E3 + reward shaping    | Reward shaping có hữu ích không                      |
| E5 | E3 + curriculum        | Opponent curriculum có cải thiện không               |
| E6 | E3 + ranking loss      | Ranking objective có nâng chất lượng chọn nước không |
| E7 | E3 + Atari fine-tuning | Adaptation vào môi trường đích có hữu ích không      |

Đối với từng so sánh, giữ các điều kiện khác càng nhất quán càng tốt.

Nếu E3 yếu hơn E2, không nên che giấu kết quả. Đây là thông tin học thuật quan trọng về giới hạn của RL fine-tuning, có thể giải thích bằng reward sparsity, instability, insufficient interactions hoặc catastrophic forgetting.

### 10.5. Những biểu đồ cần có

Biểu đồ 1 — Learning curve

RL agentPretrained baseline

00.250.50.751020k40k60k80k100k

Dữ liệu minh họa, không phải kết quả thí nghiệm.

Minh họa cách so sánh match score của RL agent với pretrained-only checkpoint theo training steps. Các giá trị là giả định.

Biểu đồ 2 — So sánh giữa các model

00.250.50.751HeuristicDQN scratchPretrainedPretrain + RL

Dữ liệu giả định để minh họa báo cáo.

Minh họa bảng kết quả ablation đối với cùng một opponent pool. Không phải dự báo kết quả thực tế.

Các biểu đồ khác có giá trị:

- Supervised train/validation loss.
- TD loss theo learner updates.
- Phân phối Q-values.
- Tactical accuracy theo nhóm bài toán.
- Win rate theo Atari mode.
- Move execution failure rate.

Lưu cả dữ liệu số gốc thay vì chỉ lưu hình biểu đồ.

## XIV. Giai đoạn 11 — Quy trình cải tiến có kiểm soát

Không nên tối ưu tất cả cùng lúc. Tôi đề xuất một chuỗi cải tiến dựa trên triệu chứng quan sát được.

| Vấn đề phát hiện                                      | Kiểm tra trước                               | Cải tiến ưu tiên                        |
| ----------------------------------------------------- | -------------------------------------------- | --------------------------------------- |
| Model thường đi mất hậu miễn phí                      | Encoding, teacher labels, tactical dataset   | Hard-negative samples                   |
| Model dự đoán evaluation khá đúng nhưng chọn sai nước | Move ranking metrics                         | Ranking loss                            |
| Model overfit                                         | Train/validation gap                         | Data diversity, regularization          |
| Pretrained model tốt nhưng RL làm yếu đi              | TD targets, reward, Q scale                  | Giảm LR, teacher regularization         |
| RL không tiến bộ                                      | Replay samples, exploration, reward sparsity | Opponent curriculum, shaping            |
| RL không ổn định                                      | Target network, gradient, Q distribution     | Gradient clipping, target update tuning |
| Đánh tốt với random nhưng thua heuristic              | Training opponent distribution               | Mixed opponent pool                     |
| Đánh tốt trong simulator nhưng kém trên Atari         | Wrapper, rules, state extraction             | Sửa integration, không vội đổi model    |
| Inference quá chậm                                    | Candidate enumeration, batch size            | Batching, caching, model nhỏ hơn        |
| Agent yếu trong tàn cuộc                              | Data distribution                            | Bổ sung endgame positions               |
| Agent chỉ giỏi một số khai cuộc                       | Dataset và đối thủ                           | Đa dạng initial positions               |

### Thứ tự cải tiến tôi khuyên dùng

P0

Độ đúng của environment và pipeline

State, action, reward, terminal, wrapper, data labels, Bellman targets.

P1 — Hiệu quả học thực tế

Pretraining quality, data coverage, exploration, curriculum, stable TD updates.

P2 — Các phương pháp nâng cao

Prioritized replay, multi-step returns, ranking objectives, reward shaping, representation improvements.

P3 — Kiến trúc phức tạp

Dueling architecture, actor–critic, search-based training và các nghiên cứu mở rộng.

Tôi không ưu tiên Dueling DQN ngay. Với afterstate network trả về một scalar cho từng candidate, Dueling cần thiết kế lại cách tách state value và action advantage, cũng như chuẩn hóa advantage trên tập legal actions biến thiên. Đây không phải sự thay đổi nhỏ chỉ bằng cách thêm hai output heads.

## XV. Tổ chức tính toán trên Colab T4

Tài nguyên hiện tại đủ để thử nghiệm network nhỏ, nhưng nên tối ưu chi phí huấn luyện.

| Công việc                    | Nơi thực hiện ưu tiên     |
| ---------------------------- | ------------------------- |
| ALE smoke test               | Máy local                 |
| Atari wrapper debugging      | Máy local                 |
| PGN processing               | CPU local                 |
| Stockfish labeling           | CPU local hoặc cloud CPU  |
| Neural network pretraining   | Colab T4                  |
| Double DQN optimizer updates | Colab T4                  |
| Simulator self-play          | CPU, có thể song song hóa |
| Tournament evaluation        | CPU local/cloud           |
| Video demo Atari             | Local                     |

Google không cam kết một hạn mức GPU cố định cho Colab Free; giới hạn phiên và mức khả dụng thay đổi theo thời điểm. Vì vậy, không nên xây pipeline yêu cầu một lần chạy liên tục rất dài.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://research.google.com\&sz=32)

research.google.com



### Cơ chế checkpoint và resume

Mỗi training checkpoint nên lưu:

```
model_state_dict
target_model_state_dict
optimizer_state_dict
global_step
episode
epsilon
random_number_generator_states
experiment_config
```

Nếu muốn resume gần chính xác trạng thái trước khi ngắt, cần phục hồi cả replay buffer hoặc có cơ chế nạp lại dữ liệu tương ứng.

Lưu checkpoints ra persistent storage, không chỉ trong filesystem tạm của Colab.

### Tối ưu throughput

Đo riêng:

- Stockfish positions/second.
- Simulator decision steps/second.
- Neural network updates/second.
- Agent inference latency.
- Atari decisions/second.

Nếu Stockfish labeling là nút thắt, tối ưu việc sinh dữ liệu. Nếu simulator self-play là nút thắt, tối ưu environment workers. Nếu neural updates quá chậm, kiểm tra batching và GPU utilization.

Không nên dành toàn bộ tài nguyên để tăng kích thước mạng khi nghẽn thực sự nằm ở tốc độ tạo transitions.

## XVI. Những điểm có thể khiến dự án thất bại và phương án dự phòng

| Rủi ro                                          | Mức nghiêm trọng | Phương án xử lý                                                                         |
| ----------------------------------------------- | ---------------- | --------------------------------------------------------------------------------------- |
| Không giải mã được RAM/RGB thành bàn cờ ổn định | Rất cao          | Dùng temporal extraction, shadow board có xác minh                                      |
| Atari wrapper bị lệch trạng thái                | Rất cao          | Closed-loop verification và recovery                                                    |
| Không đồng nhất luật giữa simulator và Atari    | Cao              | Kiểm thử đặc biệt, hạn chế suy luận từ simulator sang ALE                               |
| Sinh dữ liệu Stockfish quá chậm                 | Trung bình–cao   | Giảm nodes/depth, chọn candidate có trọng tâm                                           |
| Pretraining không tạo được sức chơi hữu ích     | Cao              | Tập trung vào ranking, tactical positions                                               |
| RL làm suy giảm model                           | Cao              | Lưu checkpoint E2, giảm LR, curriculum, regularization                                  |
| Không đạt mục tiêu Elo                          | Trung bình       | Báo cáo sức chơi theo benchmark thực, không gán Elo tùy ý                               |
| Colab ngắt phiên                                | Trung bình       | Checkpoint/resume                                                                       |
| Không hoàn thành được Atari integration         | Rất cao          | Giữ simulator demo làm kết quả kỹ thuật, nhưng phải nêu rõ giới hạn đối với yêu cầu ALE |

Hai rủi ro lớn nhất là Atari wrapper và sự suy giảm hiệu suất sau RL fine-tuning.

Tôi cũng đề xuất một quy tắc quan trọng: nếu phát hiện sai lệch giữa Atari state và shadow board, phải dừng episode hoặc chạy quy trình khôi phục đã kiểm thử. Không được tiếp tục tạo dữ liệu training từ trạng thái không đáng tin cậy.

## XVII. Chuẩn bị audit với giảng viên

Ngoài chạy được code, bạn cần giải thích rõ mỗi quyết định thiết kế.

Tôi đề xuất chuẩn bị nội dung audit theo năm nhóm:

| Nhóm                   | Những câu hỏi phải trả lời được                              |
| ---------------------- | ------------------------------------------------------------ |
| Problem formulation    | Vì sao dùng move-level RL? MDP được định nghĩa ra sao?       |
| Supervised pretraining | Stockfish cung cấp thông tin gì? Vì sao nhãn phải chuẩn hóa? |
| RL algorithm           | Vì sao Double DQN? Double DQN khác DQN thế nào?              |
| Engineering            | Wrapper hoạt động thế nào? Làm sao phát hiện mất đồng bộ?    |
| Experiments            | RL có làm model tốt hơn không? Cải tiến nào có bằng chứng?   |

Các câu hỏi học thuật cụ thể cần nắm:

1. Q-learning là off-policy vì sao?
2. Vai trò của discount factor \\(\gamma\\) là gì?
3. Bootstrapping và Temporal-Difference Learning hoạt động thế nào?
4. Vì sao dùng experience replay?
5. Vì sao target network giúp training ổn định hơn?
6. Double DQN giải quyết maximization bias như thế nào?
7. Vì sao không sử dụng trực tiếp 10 joystick actions?
8. Làm sao mạng xử lý tập nước đi có kích thước thay đổi?
9. Vì sao dùng Stockfish pretraining không đồng nghĩa với đã thực hiện Reinforcement Learning?
10. Làm sao chứng minh improvement đến từ RL thay vì Stockfish?
11. Khi opponent policy thay đổi, điều gì xảy ra với transition distribution?
12. Vì sao reward shaping có thể làm agent học sai mục tiêu?

Đây là những câu hỏi có thể trả lời từ chính implementation, training logs và các thí nghiệm.

### Nội dung báo cáo nên có

- Introduction và problem motivation.
- Related foundations: MDP, Q-learning, DQN, Double DQN.
- Environment analysis và action abstraction.
- Architecture và state representation.
- Stockfish pretraining methodology.
- Double DQN fine-tuning.
- Experimental setup.
- Results, ablation studies và failure analysis.
- Limitations và future work.

Nếu có kết quả không mong muốn, nên đưa chúng vào phần failure analysis thay vì chỉ trình bày phiên bản tốt nhất.

## XVIII. Tổng kết toàn bộ quy trình và các mốc nghiệm thu

1. Environment Research

   Hiểu rõ ALE, RAM, action semantics, reward và terminal condition.

   Deliverable: environment_analysis.md
2. Atari Interface Prototype

   Board extraction, move control và state synchronization.

   Deliverable: chơi được nhiều lượt bằng chess moves
3. MDP and Simulator

   State/action/reward/transition chính xác, simulator ổn định.

   Deliverable: chess_simulator.py + tests
4. Baseline Agents

   Random legal, material heuristic và positional heuristic.

   Deliverable: baseline tournament results
5. Model Architecture

   State encoding, CNN Q-network, batch inference.

   Deliverable: q_network.py + model tests
6. Expert Dataset

   PGN processing, Stockfish labeling, training targets và dataset splits.

   Deliverable: expert dataset + dataset report
7. Supervised Pretraining

   Huấn luyện mạng đánh giá các nước đi và kiểm chứng sức chơi.

   Deliverable: pretrained_best checkpoint
8. Double DQN Fine-tuning

   Replay buffer, TD targets, online/target networks, exploration và opponents.

   Deliverable: rl_best checkpoint + learning curves
9. Evaluation and Improvements

   Ablation experiments, tournaments, tactical evaluation và error analysis.

   Deliverable: experimental results + tables/plots
10. Atari Integration and Final Demo

    Inference không có Stockfish, chơi trên ALE, xác thực toàn bộ ván đấu.

    Deliverable: demo, reproducibility instructions, final report

## XIX. Phương án triển khai thực tế tôi chốt

Dù kế hoạch có nhiều thành phần, tôi không khuyên triển khai tất cả ngay từ đầu.

Chúng ta nên đi qua bốn phiên bản tăng dần:

| Phiên bản                         | Phạm vi                                                   | Điều kiện để chuyển tiếp                 |
| --------------------------------- | --------------------------------------------------------- | ---------------------------------------- |
| V0 — Functional system            | Atari wrapper + chess simulator + random/heuristic agents | Điều khiển và quan sát đúng              |
| V1 — Learned chess agent          | CNN + Stockfish supervised pretraining                    | Model tốt hơn các baseline cơ bản        |
| V2 — Reinforcement learning agent | V1 + Double DQN + replay + curriculum                     | Có kết quả RL đo được và so sánh với V1  |
| V3 — Optimized Atari agent        | V2 + reward shaping/ranking/Atari fine-tuning nếu cần     | Cải thiện có ý nghĩa trên benchmark thực |

V2 là mốc hoàn thành học thuật chính của assignment. V3 là phần nâng cao theo kết quả thực nghiệm.

Về kiến trúc, tôi vẫn ưu tiên một afterstate Q-network nhỏ và Double DQN, nhưng giữ khả năng điều chỉnh nếu các thử nghiệm chứng minh cách này không phù hợp. Không nên để lựa chọn thuật toán ban đầu trở thành một ràng buộc bất biến.

### Bước đầu tiên cần thực hiện

Công việc đầu tiên nên là một ALE Technical Feasibility Prototype gồm:

1. Chạy environment, ghi và phân tích RGB/RAM.
2. Điều khiển chính xác con trỏ và thực hiện `e2e4`.
3. Xác định thời điểm Atari hoàn thành nước đáp trả.
4. Khôi phục bàn cờ mới và kiểm tra với `python-chess`.
5. Xác nhận tín hiệu reward và terminal bằng test có kiểm soát.
6. Tài liệu hóa các sai lệch hoặc giới hạn phát hiện được.

Khi hoàn thành prototype này, chúng ta có thể bắt đầu xây dựng phần learning với mức rủi ro thấp hơn đáng kể.

Kết luận: Hướng `Stockfish-assisted Pretraining → Double DQN → Atari Evaluation` là phương án nghiên cứu đáng ưu tiên với những điều kiện hiện tại. Nó sử dụng RL thực sự, tận dụng được dữ liệu chuyên gia để giảm độ khó của bài toán cờ vua, không phụ thuộc engine khi inference, và cho phép đánh giá rõ ràng từng đóng góp kỹ thuật. Mục tiêu khoảng 1500 Elo vẫn cần thực nghiệm xác nhận, nhưng toàn bộ pipeline được thiết kế để ưu tiên sức chơi thực tế mà không làm mất khả năng giải thích thuật toán khi audit.