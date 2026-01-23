# Claude Code Status Display

ESP32-C6-LCD-1.47 보드를 사용한 Claude Code 상태 표시기

## 하드웨어

- **보드**: ESP32-C6-LCD-1.47 (172x320, ST7789V2)
- **연결**: USB-C (시리얼 통신)

## 설치

### 1. Arduino IDE 설정

1. **ESP32 보드 매니저 추가**
   - File → Preferences → Additional Board Manager URLs:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```

2. **ESP32 보드 설치**
   - Tools → Board → Boards Manager → "esp32" 검색 → 설치

3. **라이브러리 설치**
   - Tools → Manage Libraries:
     - `TFT_eSPI` by Bodmer
     - `ArduinoJson` by Benoit Blanchon

### 2. TFT_eSPI 설정

`User_Setup.h` 파일을 Arduino 라이브러리 폴더로 복사:

```bash
cp User_Setup.h ~/Documents/Arduino/libraries/TFT_eSPI/User_Setup.h
```

### 3. 업로드

1. **보드 선택**: Tools → Board → ESP32C6 Dev Module
2. **포트 선택**: Tools → Port → /dev/cu.usbmodem* (또는 해당 포트)
3. **업로드**: Upload 버튼 클릭

## Claude Code 설정

### 1. 환경 변수 설정

`~/.claude/.env.local` 파일 편집:

```bash
# USB 시리얼 포트 설정 (자동 감지도 가능)
export ESP32_SERIAL_PORT="/dev/cu.usbmodem1101"

# HTTP fallback (선택사항, WiFi 사용 시)
# export ESP32_HTTP_URL="http://192.168.1.100"
```

### 2. 시리얼 포트 확인

```bash
# macOS
ls /dev/cu.*

# Linux
ls /dev/ttyUSB* /dev/ttyACM*
```

## 상태 표시

| 상태 | 색상 | 설명 |
|------|------|------|
| `idle` | 🟢 녹색 | Ready - 대기 중 |
| `working` | 🔵 파란색 | Working - 작업 중 (애니메이션) |
| `notification` | 🟡 노란색 | Input - 입력 대기 |
| `session_start` | 🔵 시안 | Session - 세션 시작 |
| `tool_done` | 🟢 녹색 | Done - 도구 완료 |

## WiFi 모드 (선택사항)

USB 없이 WiFi로 사용하려면:

1. 코드에서 `#define USE_WIFI` 주석 해제
2. WiFi SSID/Password 설정
3. `ESP32_HTTP_URL` 환경 변수 설정

```cpp
#define USE_WIFI
const char* ssid = "YOUR_SSID";
const char* password = "YOUR_PASSWORD";
```

## 테스트

```bash
# USB 시리얼 테스트
echo '{"state":"working","event":"PreToolUse","tool":"Bash","project":"test"}' > /dev/cu.usbmodem1101

# HTTP 테스트 (WiFi 모드)
curl -X POST http://esp32.local/status \
  -H "Content-Type: application/json" \
  -d '{"state":"idle","event":"Stop","tool":"","project":"test"}'
```

## 트러블슈팅

### 화면이 안 나와요

- `User_Setup.h`가 올바른 위치에 있는지 확인
- 핀 설정이 보드와 맞는지 확인
- 백라이트 핀(TFT_BL) 확인

### 시리얼 연결 안 됨

```bash
# 포트 권한 확인 (Linux)
sudo chmod 666 /dev/ttyUSB0

# 시리얼 모니터로 테스트
screen /dev/cu.usbmodem1101 115200
```

### JSON 파싱 오류

시리얼 모니터에서 "JSON parse error" 메시지 확인
→ 줄바꿈 문자 확인 (LF만 사용)
