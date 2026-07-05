#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <time.h>
#include "ScioSense_ENS160.h"
#include <Adafruit_AHTX0.h>

/******** WIFI ********/
const char* ssid = "RBM_2.4GHz";
const char* password = "12112111";

/******** GOOGLE SHEET ********/
String GOOGLE_SCRIPT_ID = "AKfycbzS--H3jr-Dv4RLTXycEuvVX5lHAVGpeLk7yYb220mwcXGL9gNV_lVcy8XKKgrFLgPumA";

/******** PINS ********/
#define MQ135_PIN 34
#define MQ7_PIN   35
#define FAN_PIN   27
#define RX2_PIN   16
#define TX2_PIN   17

/******** SENSORS ********/
ScioSense_ENS160 ens160(ENS160_I2CADDR_1);
Adafruit_AHTX0 aht;

/******** VARIABLES ********/
float TVOC = 0;
float eCO2 = 0;
uint32_t rawR1_Ohm = 0;
uint32_t rawR4_Ohm = 0;
int rawMQ135 = 0;
int rawMQ7 = 0; 
float pm25 = 0;
float pm10 = 0;
float temp = 0.0;
float hum = 0.0; 

/******** LOCATION ********/
float latitude = 18.761778;
float longitude = 98.973028;

int lastMinuteExecuted = -1;

void setup() {
  Serial.begin(115200);
  pinMode(FAN_PIN, OUTPUT);
  digitalWrite(FAN_PIN, LOW);
  pinMode(MQ135_PIN, INPUT);
  pinMode(MQ7_PIN, INPUT);
  Serial2.begin(9600, SERIAL_8N1, RX2_PIN, TX2_PIN);
  Wire.begin(21, 22);

  if (!aht.begin()) Serial.println("Could not find AHT sensor!");
  ens160.begin();
  if (ens160.available()) ens160.setMode(ENS160_OPMODE_STD);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  configTime(7 * 3600, 0, "pool.ntp.org");
}

void loop() {
  readSDS011();
  struct tm timeinfo;
  if (getLocalTime(&timeinfo) && (timeinfo.tm_min % 5 == 0) && timeinfo.tm_sec == 0 && timeinfo.tm_min != lastMinuteExecuted) {
    lastMinuteExecuted = timeinfo.tm_min;
    runCycle();
  }
  delay(500);
}

void runCycle() {
  digitalWrite(FAN_PIN, HIGH);
  delay(10000);
  digitalWrite(FAN_PIN, LOW);
  readSensors();
  sendDataToGoogleSheets();
}

void readSensors() {
  sensors_event_t humidity, temperature;
  if (aht.getEvent(&humidity, &temperature)) {
    temp = temperature.temperature;
    hum = humidity.relative_humidity;
  }
  if (ens160.available()) {
    ens160.measure(true);
    TVOC = ens160.getTVOC();
    eCO2 = ens160.geteCO2();
    rawR1_Ohm = ens160.getHP0();
    rawR4_Ohm = ens160.getHP3();
  }
  rawMQ135 = analogRead(MQ135_PIN);
  rawMQ7 = analogRead(MQ7_PIN);
}

void readSDS011() {
  static uint8_t buffer[10], idx = 0;
  while (Serial2.available()) {
    uint8_t val = Serial2.read();
    if (idx == 0 && val != 0xAA) continue;
    if (idx == 1 && val != 0xC0) { idx = 0; continue; }
    buffer[idx++] = val;
    if (idx == 10) {
      uint8_t checksum = 0;
      for (int i = 2; i < 8; i++) checksum += buffer[i];
      if (checksum == buffer[8]) {
        pm25 = ((buffer[3] << 8) + buffer[2]) / 10.0;
        pm10 = ((buffer[5] << 8) + buffer[4]) / 10.0;
      }
      idx = 0;
    }
  }
}

void sendDataToGoogleSheets() {
  if (WiFi.status() != WL_CONNECTED) return;
  WiFiClientSecure client;
  client.setInsecure();
  HTTPClient http;

  // Reverted to 7 features to match your model's requirement
  String url = "https://script.google.com/macros/s/" + GOOGLE_SCRIPT_ID + "/exec?" +
               "tvoc=" + String(TVOC) +
               "&eco2=" + String(eCO2) +
               "&temp=" + String(temp, 1) +
               "&hum=" + String(hum, 1) +
               "&mq135=" + String(rawMQ135) +
               "&mq7=" + String(rawMQ7) +
               "&pm25=" + String(pm25);

  http.begin(client, url);
  http.GET();
  http.end();
}
