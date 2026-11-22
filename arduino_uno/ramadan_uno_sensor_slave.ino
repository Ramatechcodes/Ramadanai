#include <Wire.h>

// RAMADAN HOME AI secondary sensor controller.
// HC-SR04: TRIG D9, ECHO D10
// Soil module: AO A0, DO D2
// IR obstacle module OUT D3 (verify the OUT label on your board)
// I2C slave address 0x12: SDA A4, SCL A5
// IMPORTANT: I2C pull-ups must remain at 3.3V. Do not power the LCD backpack at 5V.

const byte TRIG_PIN = 9;
const byte ECHO_PIN = 10;
const byte SOIL_PIN = A0;
const byte SOIL_DO_PIN = 2;
const byte IR_PIN = 3;
const byte I2C_ADDRESS = 0x12;

volatile float distanceCm = -1.0f;
volatile int soilRaw = 0;
volatile int irState = 1;
char responseBuffer[24] = "-1.0,0,1";
unsigned long lastSample = 0;

void onRequest() {
  Wire.write((const uint8_t*)responseBuffer, strlen(responseBuffer));
}

void setup() {
  Serial.begin(9600);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(SOIL_DO_PIN, INPUT);
  pinMode(IR_PIN, INPUT);
  Wire.begin(I2C_ADDRESS);
  Wire.onRequest(onRequest);
  Serial.println(F("RAMADAN UNO SENSOR SLAVE READY"));
  Serial.println(F("I2C address: 0x12"));
}

void loop() {
  if (millis() - lastSample < 250) return;
  lastSample = millis();

  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(3);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  unsigned long duration = pulseIn(ECHO_PIN, HIGH, 25000UL);
  distanceCm = duration ? (duration * 0.0343f / 2.0f) : -1.0f;
  soilRaw = analogRead(SOIL_PIN);
  irState = digitalRead(IR_PIN);

  // Short comma-separated payload to the ESP32 master.
  dtostrf(distanceCm, 4, 1, responseBuffer);
  char tail[16];
  snprintf(tail, sizeof(tail), ",%d,%d", soilRaw, irState);
  strncat(responseBuffer, tail, sizeof(responseBuffer) - strlen(responseBuffer) - 1);

  Serial.print(F("Distance cm: ")); Serial.print(distanceCm);
  Serial.print(F(" | Soil raw: ")); Serial.print(soilRaw);
  Serial.print(F(" | IR: ")); Serial.println(irState);
}
