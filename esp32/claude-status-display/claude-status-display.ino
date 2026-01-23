/*
 * Claude Code Status Display
 * ESP32-C6-LCD-1.47 (172x320, ST7789V2)
 *
 * USB Serial + HTTP 지원
 */

#include <TFT_eSPI.h>
#include <ArduinoJson.h>

// WiFi (HTTP fallback용, 선택사항)
#ifdef USE_WIFI
#include <WiFi.h>
#include <WebServer.h>
const char* ssid = "YOUR_SSID";
const char* password = "YOUR_PASSWORD";
WebServer server(80);
#endif

TFT_eSPI tft = TFT_eSPI();

// 화면 크기
#define SCREEN_WIDTH  172
#define SCREEN_HEIGHT 320

// 색상 정의
#define COLOR_BG        TFT_BLACK
#define COLOR_IDLE      0x07E0  // 녹색
#define COLOR_WORKING   0x001F  // 파란색
#define COLOR_NOTIFY    0xFFE0  // 노란색
#define COLOR_SESSION   0x07FF  // 시안
#define COLOR_TEXT      TFT_WHITE
#define COLOR_DIM       0x7BEF  // 회색

// 상태
String currentState = "idle";
String currentProject = "";
String currentTool = "";
unsigned long lastUpdate = 0;
int animFrame = 0;

// 아이콘 (16x16 비트맵)
const uint16_t ICON_IDLE[] PROGMEM = {
  // 체크마크 아이콘
  0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x07E0, 0x0000, 0x0000, 0x0000,
  0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x07E0, 0x07E0, 0x0000, 0x0000, 0x0000,
  0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x07E0, 0x07E0, 0x0000, 0x0000, 0x0000, 0x0000,
  0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x07E0, 0x07E0, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000,
  0x0000, 0x07E0, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x07E0, 0x07E0, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000,
  0x0000, 0x07E0, 0x07E0, 0x0000, 0x0000, 0x0000, 0x0000, 0x07E0, 0x07E0, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000,
  0x0000, 0x0000, 0x07E0, 0x07E0, 0x0000, 0x0000, 0x07E0, 0x07E0, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000,
  0x0000, 0x0000, 0x0000, 0x07E0, 0x07E0, 0x07E0, 0x07E0, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000,
};

void setup() {
  Serial.begin(115200);

  // TFT 초기화
  tft.init();
  tft.setRotation(0);  // 세로 모드
  tft.fillScreen(COLOR_BG);

  // 시작 화면
  drawStartScreen();

#ifdef USE_WIFI
  setupWiFi();
#endif
}

void loop() {
  // USB 시리얼 체크
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    processInput(input);
  }

#ifdef USE_WIFI
  server.handleClient();
#endif

  // 애니메이션 업데이트
  if (millis() - lastUpdate > 100) {
    lastUpdate = millis();
    updateAnimation();
  }
}

void processInput(String input) {
  JsonDocument doc;
  DeserializationError error = deserializeJson(doc, input);

  if (error) {
    Serial.println("JSON parse error");
    return;
  }

  currentState = doc["state"].as<String>();
  currentProject = doc["project"].as<String>();
  currentTool = doc["tool"].as<String>();

  drawStatus();
}

void drawStartScreen() {
  tft.fillScreen(COLOR_BG);
  tft.setTextColor(COLOR_TEXT);
  tft.setTextSize(2);

  // 로고/타이틀
  tft.setCursor(20, 120);
  tft.println("Claude Code");

  tft.setTextSize(1);
  tft.setTextColor(COLOR_DIM);
  tft.setCursor(30, 160);
  tft.println("Status Display");

  tft.setCursor(20, 200);
  tft.println("Waiting for");
  tft.setCursor(20, 215);
  tft.println("connection...");
}

void drawStatus() {
  tft.fillScreen(COLOR_BG);

  // 상태별 색상 및 아이콘
  uint16_t statusColor;
  String statusText;
  String statusIcon;

  if (currentState == "idle") {
    statusColor = COLOR_IDLE;
    statusText = "Ready";
    statusIcon = "OK";
  } else if (currentState == "working") {
    statusColor = COLOR_WORKING;
    statusText = "Working";
    statusIcon = "...";
  } else if (currentState == "notification") {
    statusColor = COLOR_NOTIFY;
    statusText = "Input";
    statusIcon = "?";
  } else if (currentState == "session_start") {
    statusColor = COLOR_SESSION;
    statusText = "Session";
    statusIcon = ">";
  } else if (currentState == "tool_done") {
    statusColor = COLOR_IDLE;
    statusText = "Done";
    statusIcon = "v";
  } else {
    statusColor = COLOR_DIM;
    statusText = currentState;
    statusIcon = "-";
  }

  // 상단 상태 원
  int centerX = SCREEN_WIDTH / 2;
  int centerY = 80;
  int radius = 50;

  // 원 그리기 (채우기 + 테두리)
  tft.fillCircle(centerX, centerY, radius, statusColor);
  tft.drawCircle(centerX, centerY, radius + 2, COLOR_TEXT);

  // 아이콘 텍스트
  tft.setTextColor(COLOR_BG);
  tft.setTextSize(4);
  int iconWidth = statusIcon.length() * 24;
  tft.setCursor(centerX - iconWidth / 2 + 5, centerY - 15);
  tft.println(statusIcon);

  // 상태 텍스트
  tft.setTextColor(statusColor);
  tft.setTextSize(3);
  int textWidth = statusText.length() * 18;
  tft.setCursor(centerX - textWidth / 2, 160);
  tft.println(statusText);

  // 프로젝트명
  if (currentProject.length() > 0) {
    tft.setTextColor(COLOR_TEXT);
    tft.setTextSize(1);
    tft.setCursor(10, 210);
    tft.print("Project: ");
    tft.setTextColor(COLOR_DIM);

    // 긴 이름 자르기
    String displayProject = currentProject;
    if (displayProject.length() > 18) {
      displayProject = displayProject.substring(0, 15) + "...";
    }
    tft.println(displayProject);
  }

  // 현재 도구
  if (currentTool.length() > 0 && currentState == "working") {
    tft.setTextColor(COLOR_TEXT);
    tft.setTextSize(1);
    tft.setCursor(10, 230);
    tft.print("Tool: ");
    tft.setTextColor(COLOR_WORKING);
    tft.println(currentTool);
  }

  // 하단 정보
  tft.setTextColor(COLOR_DIM);
  tft.setTextSize(1);
  tft.setCursor(10, 300);
  tft.println("Claude Code Monitor");
}

void updateAnimation() {
  if (currentState != "working") return;

  animFrame = (animFrame + 1) % 8;

  int centerX = SCREEN_WIDTH / 2;
  int centerY = 80;

  // 회전 점 애니메이션
  for (int i = 0; i < 8; i++) {
    float angle = (i * 45 + animFrame * 45) * PI / 180;
    int x = centerX + cos(angle) * 60;
    int y = centerY + sin(angle) * 60;

    uint16_t dotColor = (i == 0) ? COLOR_TEXT : COLOR_DIM;
    tft.fillCircle(x, y, 3, dotColor);
  }
}

#ifdef USE_WIFI
void setupWiFi() {
  WiFi.begin(ssid, password);

  tft.setCursor(20, 250);
  tft.setTextColor(COLOR_DIM);
  tft.setTextSize(1);
  tft.print("WiFi: ");

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    tft.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    tft.println("OK");
    tft.setCursor(20, 265);
    tft.print("IP: ");
    tft.println(WiFi.localIP());

    // HTTP 서버 설정
    server.on("/status", HTTP_POST, handleStatus);
    server.begin();
  } else {
    tft.println("Failed");
  }
}

void handleStatus() {
  if (server.hasArg("plain")) {
    processInput(server.arg("plain"));
    server.send(200, "application/json", "{\"ok\":true}");
  } else {
    server.send(400, "application/json", "{\"error\":\"no body\"}");
  }
}
#endif
