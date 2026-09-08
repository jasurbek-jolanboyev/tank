# TANK — 8 KEYS passiv aniqlash va ogohlantirish platformasi

Bu repository mavjud `tank` loyihasining asosiy texnik qo‘llanmasi. Loyiha sakkizta
mustaqil kuzatuv moduli (`KEYS`), Ubuntu markaziy serveri, ikkita ESP32-S3 I/O node
va Flutter operator konsolidan tashkil topgan passiv prototipdir.

> **Xavfsizlik chegarasi:** loyiha faqat kamera kuzatuvi, obyekt aniqlash,
> klassifikatsiya, tracking, masofa o‘lchash, sektor biriktirish, oq/qizil vizual
> indikator, telemetry, health, recording va diagnostikani bajaradi. Unda qurol,
> nishonga olish, o‘t ochish, jamming, RF/GPS buzish yoki destruktiv boshqaruv yo‘q
> va bunday funksiyalar qo‘shilmasligi kerak.

## Mundarija

- [Hozirgi arxitektura](#hozirgi-arxitektura)
- [8 KEYS taqsimoti](#8-keys-taqsimoti)
- [Ishlash mantig‘i](#ishlash-mantigi)
- [Repository strukturasi](#repository-strukturasi)
- [Komponentlar va kod xaritasi](#komponentlar-va-kod-xaritasi)
- [Konfiguratsiya va rejimlar](#konfiguratsiya-va-rejimlar)
- [Ishga tushirish](#ishga-tushirish)
- [ESP32 firmware](#esp32-firmware)
- [AI modeli va training](#ai-modeli-va-training)
- [API, preview va Flutter](#api-preview-va-flutter)
- [Test va diagnostika](#test-va-diagnostika)
- [Yangi kod qo‘shish yoki olib tashlash](#yangi-kod-qoshish-yoki-olib-tashlash)
- [Hozirgi status va cheklovlar](#hozirgi-status-va-cheklovlar)
- [Keyingi hardware bosqichi](#keyingi-hardware-bosqichi)

## Hozirgi arxitektura

Oldingi markaziy qurilma Jetson Orin Nano edi. Hozirgi prototip markazi:

```text
Intel MacBook
    ↓
VMware
    ↓
Ubuntu Server 24.04 amd64
```

`jetson/` katalog nomi import va deployment bog‘lanishlarini buzmaslik uchun
saqlangan. Uning ichidagi Python dastur hozir platform-independent markaziy server
hisoblanadi. Kelajakda ayni business logic Jetson ARM64 + TensorRT backend bilan
ham ishlashi mumkin.

```text
8 × USB/RTSP kamera
          │
          ▼
Ubuntu CameraManager ──► ONNX detector ──► TrackManager
                                                 │
2 × ESP32-S3 ◄── serial/WebSocket ── Esp32Manager│
      │                                          ▼
8 × TF02-Pro ───────────────► fresh range ─► SensorFusionEngine
      │                                          │
8 × oq + 8 × qizil indikator ◄── sector command─┘

Ubuntu REST/JPEG/WebSocket ──► mavjud Flutter operator console
```

Mas’uliyatlar:

- **Ubuntu Server:** kamera capture, AI inference, tracking, temporal validation,
  range fusion, indicator qarori, event, recording, health, API va telemetry.
- **ESP32-S3:** I²C/UART/GPIO, TF02-Pro acquisition, indikator chiqishlari,
  hardware health, sector routing va timeout-safe `OFF`.
- **Flutter:** monitoring va ko‘rsatish. Flutter uzilishi markaziy processingni
  to‘xtatmaydi.
- **Jetson:** joriy prototip uchun talab qilinmaydi; kelajak backend.

Kameralar ESP32 orqali o‘tmaydi. RTSP kameralar PoE switch orqali Ubuntu VM’ga,
USB kameralar esa VMware USB passthrough orqali `/dev/videoX`ga keladi.

## 8 KEYS taqsimoti

Har bir `KEYS` — alohida fizik sektor:

```text
1 kamera
1 TF02-Pro LiDAR
1 oq indikator kanali
1 qizil indikator kanali
kelajak uchun aniq modeli tanlangan qo‘shimcha sensor/radar porti
```

| KEYS | Sektor | Kamera | ESP32 | LiDAR ID | I²C | Oq GPIO* | Qizil GPIO* |
|---|---|---|---|---|---:|---:|---:|
| KEYS-01 | FRONT_1 | CAM_FRONT_1 | NODE-01 | RANGE-FRONT-1 | 0x10 | 4 | 5 |
| KEYS-02 | FRONT_2 | CAM_FRONT_2 | NODE-01 | RANGE-FRONT-2 | 0x11 | 6 | 7 |
| KEYS-03 | RIGHT_1 | CAM_RIGHT_1 | NODE-01 | RANGE-RIGHT-1 | 0x12 | 8 | 9 |
| KEYS-04 | RIGHT_2 | CAM_RIGHT_2 | NODE-01 | RANGE-RIGHT-2 | 0x13 | 10 | 11 |
| KEYS-05 | REAR_1 | CAM_REAR_1 | NODE-02 | RANGE-REAR-1 | 0x10 | 4 | 5 |
| KEYS-06 | REAR_2 | CAM_REAR_2 | NODE-02 | RANGE-REAR-2 | 0x11 | 6 | 7 |
| KEYS-07 | LEFT_1 | CAM_LEFT_1 | NODE-02 | RANGE-LEFT-1 | 0x12 | 8 | 9 |
| KEYS-08 | LEFT_2 | CAM_LEFT_2 | NODE-02 | RANGE-LEFT-2 | 0x13 | 10 | 11 |

`*` GPIO qiymatlari **UNVERIFIED BOARD PROFILE**. Exact ESP32-S3 plata modeli,
flash/PSRAM/USB va strapping pinlari tekshirilmasdan fizik ulash mumkin emas.

Authoritative mapping ikki joyda bir xil saqlanishi kerak:

- server: `jetson/configs/ubuntu-vm-real.example.yaml`;
- firmware: `firmware/esp32_s3_node/main/config/node_config.h`.

Batafsil jadval: `docs/keys-layout.md`.

## Ishlash mantig‘i

Har bir KEYS faqat o‘z kamera va sensor ma’lumotiga javob beradi:

```text
CAM_LEFT_1 frame
      ↓
LEFT_1 detection/track
      ↓
faqat LEFT_1 sektoridagi fresh RANGE-LEFT-1
      ↓
OFF / WHITE / RED qarori
      ↓
NODE-02
      ↓
faqat KEYS-07 oq/qizil GPIO
```

Boshqa KEYS chiqishlari o‘zgarmaydi. Ubuntu transport kelgan `nodeId` va `sector`
egaliklarini tekshiradi; ESP32 ham o‘ziga tegishli bo‘lmagan sektor buyrug‘ini rad
etadi.

Indikator siyosati:

- tasdiqlangan drone yo‘q → `OFF`;
- tasdiqlangan drone bor, valid masofa near zonadan tashqarida → `WHITE`;
- tasdiqlangan drone `nearEnterMeters` ichida → `RED`;
- `RED` holatidan chiqish `nearExitMeters` bilan amalga oshadi;
- default hysteresis: 20 m enter, 22 m exit;
- range yo‘q/stale bo‘lsa exact metr uydirilmaydi;
- Ubuntu komandasi 2 soniya kelmasa har KEYS mustaqil `OFF`ga qaytadi.

TF02-Pro tor 3° nurli sensor. Kamera bbox va LiDAR bir sektorda bo‘lishi o‘lchov
aynan ko‘rilgan obyektga tegishli ekanini avtomatik isbotlamaydi. Kamera/LiDAR
geometriyasi fizik kalibrlanishi shart.

## Repository strukturasi

```text
tank/
├── README.md                         # ushbu authoritative loyiha qo‘llanmasi
├── jetson/                           # legacy nomli platform-independent server
│   ├── app/                          # Python runtime
│   ├── configs/                      # simulator, Ubuntu real, future Jetson config
│   ├── tests/                        # Python unit/integration-level testlar
│   ├── systemd/                      # Ubuntu service va eski legacy service
│   ├── recordings/                   # development JSONL yozuvlari
│   ├── requirements.txt              # minimal server dependency
│   ├── requirements-ubuntu.txt       # Ubuntu ONNX/camera/metrics dependency
│   └── requirements-vision-macos.txt # host vision development dependency
├── firmware/
│   └── esp32_s3_node/                # ESP-IDF target + portable C++ core
│       ├── main/                     # 4-KEYS firmware adapters
│       └── test/                     # hostda ishlaydigan portable core test
├── apps/
│   └── operator_console/             # mavjud Flutter ilova; yangi app yaratilmadi
├── ml/
│   ├── configs/                      # dataset/training/export config
│   ├── datasets/                     # raw/processed YOLO dataset
│   ├── models/                       # checkpoint, model status va training outputs
│   ├── exports/                      # ONNX artifacts
│   ├── reports/                      # dataset va benchmark hisobotlari
│   ├── scripts/                      # acquisition, verify, train, export
│   └── vendor/                       # saqlangan third-party/legacy source
├── shared/
│   ├── protocol/                     # wire protocol tavsifi
│   └── schemas/protocol-v1.json      # canonical JSON schema
├── tools/
│   ├── hardware_diagnostic.py        # camera/ESP32/LED/model isolated tests
│   ├── diagnostics/ws_probe.py       # WebSocket probe
│   └── vision_test/                  # host model inspection/inference tool
├── scripts/
│   ├── install_ubuntu_24_04.sh       # idempotentga yaqin Ubuntu installer
│   └── diagnose_ubuntu.sh            # secret chiqarmaydigan VM diagnostikasi
├── docs/                             # arxitektura, hardware, deployment va cheklovlar
└── build/                            # generated host CMake outputs; source emas
```

Generated/source bo‘lmagan kataloglar:

- `.venv/`, `.venv-train/`, `jetson/.venv/`, `.dart_tool/` — local environment;
- `build/` — CMake artifact;
- `__pycache__/`, `.DS_Store`, `.cache/` — local cache;
- `ml/models/detector/train-*` — training output;
- `ml/datasets/**/labels.cache` — Ultralytics cache.

Bu generated fayllarga feature logic yozilmaydi. Source o‘zgarishi tegishli `app/`,
`main/`, `lib/`, `scripts/`, `configs/` yoki `docs/` ichida qilinadi.

## Komponentlar va kod xaritasi

### Markaziy server

| Fayl/katalog | Vazifa | O‘zgartirganda tekshiriladi |
|---|---|---|
| `jetson/app/main.py` | CLI, config load, Uvicorn listenerlar | startup/shutdown, portlar |
| `jetson/app/engine.py` | komponent lifecycle va processing orchestration | simulator va real backend ajratilishi |
| `jetson/app/config/loader.py` | mode, env expansion, validation | real mode mock’ni rad etishi |
| `jetson/app/models.py` | canonical detection/range/track/sector turlari | protocol va Flutter parsing |
| `jetson/app/camera/base.py` | `CameraFrame`, source protocol, latest queue | normalized timestamp va queue semantics |
| `jetson/app/camera/manager.py` | mustaqil worker, health, JPEG preview | failure isolation, FPS va drop metric |
| `jetson/app/camera/opencv_source.py` | USB/RTSP/video/CSI adapter | Ubuntu’da CSI talab qilinmasligi |
| `jetson/app/camera/simulated.py` | simulator camera | faqat sim/dev rejim |
| `jetson/app/ai/base.py` | detector interface | barcha backendlar bir xil detection qaytaradi |
| `jetson/app/ai/mock.py` | repeatable simulated detection | real mode’da noqonuniy |
| `jetson/app/ai/onnx_detector.py` | letterbox, ORT CPU, YOLO decode, NMS | actual model output metadata |
| `jetson/app/ai/tensorrt_detector.py` | future Jetson skeleton | Ubuntu dependencyga aylantirmaslik |
| `jetson/app/tracking/manager.py` | IoU tracking, stable ID, confirmation | sticky confirm, expiration |
| `jetson/app/fusion/engine.py` | range freshness va hysteresis | cross-sector aralashmasligi |
| `jetson/app/esp32/transport.py` | mock/serial/WebSocket transports | reconnect, timeout, close |
| `jetson/app/esp32/manager.py` | multi-node lifecycle va sector ownership | node spoof/sector mismatch rejection |
| `jetson/app/esp32/protocol.py` | v1 decode va indicator message | shared schema + firmware |
| `jetson/app/network/api.py` | REST, JPEG preview, telemetry WS | bind/security va response contract |
| `jetson/app/health/monitor.py` | CPU/RAM/disk/process health | Jetson-only API ishlatmaslik |
| `jetson/app/events/store.py` | bounded event history | Flutter event parser |
| `jetson/app/recording/jsonl.py` | rotating JSONL va replay iterator | retention va disk limit |
| `jetson/app/telemetry/broker.py` | bounded subscriber queue | slow client latency |

### ESP32 firmware

| Fayl/katalog | Vazifa |
|---|---|
| `main/config/node_config.h` | NODE-01/NODE-02, 4 KEYS, pin va I²C mapping |
| `main/app_main.cpp` | 4 sensor loop, 4 indicator pair, per-KEYS timeout |
| `main/ranging/tf02_pro_i2c.*` | non-blocking TF02-Pro I²C request/read |
| `main/ranging/tf02_pro.*` | saqlangan legacy single UART adapter |
| `main/ranging/distance_filter.*` | sensor smoothing/outlier filter |
| `main/hardware/*` | GPIO logic-level output driver |
| `main/transport/*` | Ubuntu JSON Lines serial protocol |
| `main/core/*` | hardware’dan mustaqil temporal/sector/parser logic |
| `test/core_tests.cpp` | macOS/Linux host portable C++ tests |

Firmware bir sektor uchun to‘rtta alohida nusxaga bo‘linmaydi. Bitta universal
source `TANK_NODE_PROFILE=1` yoki `2` bilan ikki binary beradi.

### Flutter operator console

| Fayl | Vazifa |
|---|---|
| `lib/main.dart` | application entrypoint |
| `features/vision/models/vision_packet.dart` | protocol v1 parser va UI modellari |
| `features/vision/services/jetson_connection_service.dart` | WS reconnect/state va preview URI |
| `features/vision/presentation/vision_dashboard.dart` | 1/2/4/8 grid, overlay, health/events |

Preview JPEG/HTTP orqali, telemetry esa WebSocket JSON orqali keladi. Raw video
frame base64 JSON qilib yuborilmaydi.

## Konfiguratsiya va rejimlar

Canonical mode’lar:

| Mode | Maqsad | Mock holati |
|---|---|---|
| `SIMULATOR` | hardware’siz to‘liq development oqimi | ruxsat |
| `DEVELOPMENT` | explicit aralash test backendlari | configga bog‘liq |
| `UBUNTU_VM_REAL` | joriy fizik prototip | mock camera/detector/ESP32 taqiqlangan |
| `JETSON_FUTURE` | kelajak CSI/TensorRT deployment | mock taqiqlangan |

Asosiy configlar:

- `jetson/configs/dev.yaml` — bitta simulated kamera/range/ESP32;
- `jetson/configs/ubuntu-vm-real.example.yaml` — 8 kamera + 2 ESP32 real template;
- `jetson/configs/production.yaml` — future Jetson template.

Real config credential yoki device path’ni source ichiga hard-code qilmaydi.
Environment qiymatlari:

```text
TANK_SERVER_HOST
TANK_MODEL_PATH
TANK_ESP32_NODE_01_DEVICE
TANK_ESP32_NODE_02_DEVICE
TANK_CAM_FRONT_1_RTSP ... TANK_CAM_LEFT_2_RTSP
```

Real mode’da yechilmay qolgan `${...}` startup error beradi. Serial uchun imkon
qadar `/dev/serial/by-id/...` ishlatiladi, `/dev/ttyUSB0` qattiq yozilmaydi.

Config o‘zgartirish qoidasi:

1. `version: 1`ni protokol migratsiyasiz o‘zgartirmang.
2. Har kamera ID unique va sector canonical `SECTORS` ichida bo‘lsin.
3. Har sektor aynan bitta ESP32 node’ga tegishli bo‘lsin.
4. Firmware `node_config.h` mapping bilan server config bir xil bo‘lsin.
5. Secret’larni Git/README/logga yozmang.
6. Real rejimda fake range yoki mock backend bilan bypass qilmang.

## Ishga tushirish

### Simulator

```bash
cd ~/tank/jetson
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
PYTHONPATH=. .venv/bin/python -m app.main --config configs/dev.yaml
```

Endpointlar:

```text
GET  http://127.0.0.1:8080/health
GET  http://127.0.0.1:8080/cameras
GET  http://127.0.0.1:8080/preview/{cameraId}.jpg
WS   ws://127.0.0.1:8081/ws
```

WebSocket probe:

```bash
cd ~/tank/jetson
.venv/bin/python ../tools/diagnostics/ws_probe.py ws://127.0.0.1:8081/ws
```

### Ubuntu Server 24.04 VM

VM ichida:

```bash
git clone REPOSITORY_URL /opt/tank
cd /opt/tank
scripts/install_ubuntu_24_04.sh
scripts/diagnose_ubuntu.sh
```

Keyin:

1. Installer yaratgan `/etc/tank/tank.env` ichiga model va camera device qiymatlarini yozing.
2. Kerak bo‘lsa `/etc/tank/config.yaml`ga qo‘shimcha RTSP/USB kameralar va ESP32 node’larni qo‘shing.
3. Validated ONNX model path’ini kiriting.
4. Kamera va ESP32’larni diagnostic bilan alohida tekshiring.
5. `sudo systemctl start tank-detection` bilan serverni ishga tushiring.

Manual start:

```bash
cd ~/tank/jetson
PYTHONPATH=. .venv-ubuntu/bin/python -m app.main --config /etc/tank/config.yaml
```

Systemd fayli: `jetson/systemd/tank-detection.service`.

```bash
sudo systemctl start tank-detection
sudo systemctl stop tank-detection
sudo systemctl status tank-detection
sudo journalctl -u tank-detection -f
sudo systemctl enable tank-detection   # faqat HIL acceptance’dan keyin
sudo systemctl disable tank-detection
```

Eski `jetson/systemd/drone-detection.service` legacy template. Yangi deploymentda
`tank-detection.service` authoritative hisoblanadi; legacy fayl barcha reference
tekshirilgandan keyingina alohida cleanup commit’da olib tashlanishi mumkin.

## ESP32 firmware

Firmware ESP-IDF/CMake loyihasi, PlatformIO emas.

```bash
cd ~/tank/firmware/esp32_s3_node
TANK_NODE_PROFILE=1 idf.py fullclean build   # NODE-01 / KEYS-01..04
TANK_NODE_PROFILE=2 idf.py fullclean build   # NODE-02 / KEYS-05..08
```

Profil almashtirganda `fullclean` zarur: noto‘g‘ri node binary’sini flash qilish
sector routingni buzadi. Boot log `node`, `profile`, `keys` va firmware versionni
ko‘rsatadi.

Hozirgi placeholder pinlar:

```text
I2C SDA GPIO12, SCL GPIO13
Ubuntu UART2 RX GPIO16, TX GPIO15, 115200 8N1
KEYS LED pair: 4/5, 6/7, 8/9, 10/11
```

TF02-Pro sensorlari umumiy I²C bus’da 0x10–0x13 address bilan ishlaydi. Har sensor
bus’ga birgalikda qo‘shilishidan oldin bittadan ulanib I²C mode/address saqlanishi
kerak. Tashqi 3.3-V pull-up hisoblanadi. TF02-Pro quvvati 5–12 V; uni ESP32 GPIO
yoki 3.3-V pinidan quvvatlantirmang.

External kuchli lampa:

```text
ESP32 GPIO → 3.3-V-compatible driver/MOSFET/relay → fused external lamp supply
```

GPIO lampani bevosita quvvatlantirmaydi. Avval rezistorli kichik LED bilan test.

## AI modeli va training

### Mavjud holat

- `tiny-roi-classifier` — 96×96 legacy classifier; full-frame obyekt topmaydi.
- `cc0_yolo_v3` — YOLO bounding-box dataset; verifier `OK`.
- `ml/exports/smoke-e1-f002-s320/best.onnx` — faqat pipeline smoke artifact.
- production darajadagi validated detector — **mavjud emas**.

Smoke model natijasi:

```text
1 epoch, 2% train fraction, 320×320, Intel CPU
precision      0.000528
recall         0.170
mAP50          0.000472
mAP50-95       0.000145
validation ORT 38.4 ms/image
```

Bu model real detection/indikator qarori uchun yaroqsiz. Uning ONNX SHA256’i:

```text
501602f444ae7cc97062dba9aa59518c747c19fe847f2bf773760620148caede
```

Dataset verification:

```bash
cd ~/tank
.venv-train/bin/python ml/scripts/verify_dataset.py \
  --root ml/datasets/processed/cc0_yolo_v3
```

Training environment:

```bash
python3.11 -m venv .venv-train
.venv-train/bin/pip install -r ml/requirements.txt
```

Smoke pipeline misoli:

```bash
MPLCONFIGDIR=$PWD/.cache/matplotlib \
XDG_CACHE_HOME=$PWD/.cache \
YOLO_CONFIG_DIR=$PWD/.cache/ultralytics \
.venv-train/bin/python ml/scripts/train_detector.py \
  --config ml/configs/jetson_detector.yaml \
  --epochs 1 --batch 8 --fraction 0.02 --input-size 320
```

Production experiment `fraction=1.0`, full validation/test va o‘lchangan acceptance
threshold bilan bajariladi. Metric yetarli bo‘lmasa model deploy qilinmaydi.

ONNX export:

```bash
.venv-train/bin/python ml/scripts/export_jetson.py CHECKPOINT.pt \
  --output ml/exports/MODEL_VERSION
```

ONNX runtime faqat config’da aniq `format: yolo_v8` yoki `yolo_v5` va model class
tartibi ko‘rsatilganda ishlaydi. Output format taxmin qilinmaydi.

## API, preview va Flutter

Telemetry v1 JSON message’lar:

```text
ESP32 → range, node_health, heartbeat
Ubuntu → ESP32 indicator_state
Ubuntu → Flutter vision_detection, sector_state, camera_health,
                   system_health, event, range
```

Canonical schema: `shared/schemas/protocol-v1.json`.

Protocol field qo‘shish tartibi:

1. backward-compatible optional field tanlang;
2. Python model/parserni yangilang;
3. firmware encoder/decoderni yangilang;
4. shared schema va protocol docs’ni yangilang;
5. Flutter parserni yangilang;
6. Python + C++ + Flutter test qo‘shing.

Flutter simulator:

```bash
cd ~/tank/apps/operator_console
flutter run -d macos
```

Mac’dan VMware Ubuntu’ga:

```bash
flutter run -d macos --dart-define=TANK_SERVER_HOST=UBUNTU_VM_IP
```

Flutter hozir WebSocket port 8081 va preview REST port 8080dan foydalanadi. Portlar
o‘zgarsa server config bilan Flutter connection service ham birga yangilanadi.

## Test va diagnostika

### Python

```bash
cd ~/tank/jetson
PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -v
PYTHONPATH=. .venv/bin/python -m compileall -q app tests ../tools ../ml/scripts
```

Joriy natija: `12/12 PASS`.

### Portable ESP32 C++ core

```bash
cd ~/tank
cmake -S firmware/esp32_s3_node -B build/firmware-host
cmake --build build/firmware-host
ctest --test-dir build/firmware-host --output-on-failure
```

Joriy natija: `1/1 PASS`. Bu ESP-IDF target build yoki fizik I²C/GPIO test o‘rnini
bosmaydi.

### Flutter

```bash
cd ~/tank/apps/operator_console
flutter analyze
flutter test
```

Joriy natija: analyze `0 issues`, test `4/4 PASS`.

### Isolated hardware diagnostics

```bash
cd ~/tank
jetson/.venv-ubuntu/bin/python tools/hardware_diagnostic.py camera-list
jetson/.venv-ubuntu/bin/python tools/hardware_diagnostic.py camera-capture 0 \
  --seconds 5 --output /tmp/camera.jpg
jetson/.venv-ubuntu/bin/python tools/hardware_diagnostic.py esp32-read \
  /dev/serial/by-id/DEVICE --seconds 10
jetson/.venv-ubuntu/bin/python tools/hardware_diagnostic.py model-info MODEL.onnx
```

Fizik indikator testi deliberate opt-in:

```bash
jetson/.venv-ubuntu/bin/python tools/hardware_diagnostic.py indicator-test \
  /dev/serial/by-id/DEVICE FRONT_1 WHITE \
  --i-understand-this-changes-physical-outputs
```

Testdan keyin darhol `OFF` yuboring. Physical output test avtomatik test suite ichida
hech qachon ishlamasligi kerak.

Test darajalari:

- **UNIT:** hardware-independent Python/C++/Dart;
- **INTEGRATION:** simulator REST/WS va protocol;
- **SIMULATOR:** mock camera/detector/range/ESP32;
- **HIL:** real camera/ESP32/TF02/LED, explicit opt-in;
- **E2E:** real frame → detector → track → range → aniq KEYS LED → Flutter.

Hardware bo‘lmasa natija `SKIPPED/NOT RUN — HARDWARE REQUIRED`, `PASS` emas.

## Yangi kod qo‘shish yoki olib tashlash

### Yangi kamera source qo‘shish

1. `jetson/app/camera/base.py` interfeysiga rioya qiluvchi adapter yarating.
2. `CameraManager` factory’ga yangi `type` qo‘shing.
3. Bounded latest-frame queue’ni chetlab o‘tmang.
4. Reconnect, close va health’ni implement qiling.
5. Config validation va failure-isolation test qo‘shing.
6. Credential’ni config/env orqali oling.

### Yangi AI backend/model qo‘shish

1. `IObjectDetector` contract’ini saqlang.
2. `Detection` bbox’i normalized `[0,1]` bo‘lsin.
3. Model input/output metadata’ni tekshiring; formatni taxmin qilmang.
4. Class order, version va SHA256 log/metadata’da bo‘lsin.
5. Engine factory va mode legality’ni yangilang.
6. Recorded image va known tensor bilan preprocessing/decode/NMS test yozing.
7. Metric bo‘lmasa production deb belgilamang.

### Yangi sensor yoki radar qo‘shish

Radar hozir tanlanmagan va implement qilinmagan. Qo‘shishdan oldin exact model,
voltage, interface, protocol, FoV, update rate va regulatory holat hujjatlashtiriladi.

1. Firmware’da hardware adapter yarating.
2. Xabar `nodeId`, `sensorId`, `sector`, `valid`, `timestamp`ni olib yursin.
3. Shared schema va Python decoder’ni kengaytiring.
4. Node/sector ownershipni saqlang.
5. Fusion’da freshness va geometry limitation qo‘shing.
6. Boshqa KEYS bilan cross-fusion test yozing.
7. Flutter health/telemetry parserni yangilang.

### Yangi KEYS yoki mapping o‘zgartirish

1. `models.py`dagi sector ro‘yxatini tekshiring.
2. Ubuntu config camera va node ownershipni yangilang.
3. Firmware profile mappingni yangilang.
4. `docs/keys-layout.md` va ushbu jadvalni yangilang.
5. `test_eight_keys_are_uniquely_routed`ga mos yangi invariant yozing.
6. Bir sektor ikki node’ga yoki ikki kamera bir ID’ga tushmasin.

### Protocol version o‘zgartirish

Breaking o‘zgarishda v1’ni joyida buzmay, yangi version/parser migration yarating.
Server, firmware va Flutter bir vaqtda yangilanmaguncha eski version compatibility
saqlanadi.

### Fayl yoki legacy kod olib tashlash

Olib tashlashdan oldin:

```bash
rg -n "FileName|ClassName|config-key|service-name" . \
  -g '!build/**' -g '!.venv*/**' -g '!**/__pycache__/**'
```

Keyin:

1. import, CMake, pubspec, systemd, docs va test reference’larini tekshiring;
2. generated artifactni source bilan adashtirmang;
3. portable core’ni hardware adapter bilan birga tasodifan o‘chirmang;
4. future TensorRT/Jetson abstractionni Ubuntu uchun keraksiz deb birdan o‘chirmang;
5. barcha testlarni major phase’dan keyin qayta bajaring;
6. documentation statusini haqiqiy code bilan birga yangilang.

### Majburiy o‘zgartirish sikli

```text
audit/reference search
→ kichik scoped change
→ unit/config/protocol test
→ component build/analyze
→ simulator integration
→ docs/status update
→ hardware bo‘lsa isolated diagnostic
→ HIL/E2E
```

## Hozirgi status va cheklovlar

| Komponent | Status |
|---|---|
| Simulator camera/detector/range/ESP32 | WORKING |
| Python engine/tracking/hysteresis/protocol | WORKING, UNIT TESTED |
| 8 KEYS config va unique routing | WORKING, UNIT TESTED |
| USB/RTSP/video capture | IMPLEMENTED, HARDWARE TEST REQUIRED |
| Per-camera reconnect/FPS/drop health | IMPLEMENTED |
| 2-node ESP32 manager | IMPLEMENTED, HARDWARE TEST REQUIRED |
| Serial/WebSocket ESP32 transports | IMPLEMENTED, HARDWARE TEST REQUIRED |
| Real range → freshness fusion | IMPLEMENTED, HARDWARE TEST REQUIRED |
| Per-KEYS safe OFF | IMPLEMENTED, TARGET/HARDWARE TEST REQUIRED |
| 4 TF02-Pro I²C per ESP32 | IMPLEMENTED, ESP-IDF BUILD/HARDWARE TEST REQUIRED |
| 4 independent LED pairs per ESP32 | IMPLEMENTED, PIN/HARDWARE TEST REQUIRED |
| ONNX YOLOv5/v8 CPU adapter | IMPLEMENTED, SMOKE TESTED |
| Validated production detector | NOT AVAILABLE |
| TensorRT | FUTURE JETSON SKELETON |
| Flutter 8-camera grid/telemetry/JPEG | IMPLEMENTED, REAL STREAM TEST REQUIRED |
| JSONL rotation/replay iterator | WORKING, UI REPLAY PARTIAL |
| Radar | NOT SELECTED / NOT IMPLEMENTED |
| 8-camera real performance | NOT RUN — HARDWARE REQUIRED |
| ESP-IDF target build/flash | NOT RUN — TOOLCHAIN/HARDWARE REQUIRED |
| Physical TF02/LED/HIL/E2E | NOT RUN — HARDWARE REQUIRED |

Kod “hardware’ni ulash bilan kafolatli ishlaydi” deb qabul qilinmaydi. Unit testlar
logic regressiyasini ushlaydi, lekin pin, power, I²C electrical behavior, serial
passthrough, kamera latency va model aniqligini faqat real HIL/E2E tasdiqlaydi.

## Keyingi hardware bosqichi

Avval bitta KEYS:

```text
1 × exact modeli ma’lum ESP32-S3 board
1 × kamera
1 × TF02-Pro
1 × rezistorli oq test LED
1 × rezistorli qizil test LED
1 × 3.3-V USB–TTL adapter
1 × regulated 5-V TF02 supply
```

Acceptance tartibi:

```text
exact board pinout audit
→ ESP-IDF profile-1 build
→ flash/boot identity
→ VMware USB device detection
→ isolated camera capture
→ ESP32 JSON health
→ TF02 I²C address/read
→ WHITE maintenance test
→ RED maintenance test
→ ALL OFF / timeout
→ real detector validation
→ camera + range + exact KEYS indicator
→ Flutter telemetry/preview
→ disconnect/reconnect tests
```

Bitta KEYS o‘tgach NODE-01’da to‘rtta, so‘ng NODE-02’da qolgan to‘rtta KEYS
bosqichma-bosqich ulanadi. Sakkiztasini birinchi urinishda birdan quvvatlantirish
tavsiya etilmaydi.

## Qo‘shimcha hujjatlar

- `docs/architecture.md` — authoritative system authority va data flow;
- `docs/keys-layout.md` — 8 KEYS mapping;
- `docs/hardware-bom.md` — boshlang‘ich va 8-KEYS BOM;
- `docs/hardware-connections.md` — VMware, kamera, ESP32, I²C va LED ulanishi;
- `docs/deployment.md` — Ubuntu/systemd deployment;
- `docs/ai-model.md`, `ml/models/MODEL_STATUS.md` — model haqiqiy holati;
- `docs/protocol.md`, `shared/protocol/README.md` — wire protocol;
- `docs/testing.md`, `docs/troubleshooting.md` — test va muammo yechish;
- `docs/hardware-boundaries.md` — elektr va passive-scope chegaralari.
