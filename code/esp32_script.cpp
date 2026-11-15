#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ILI9341.h>
#include <Adafruit_ADS1X15.h>

const int TFT_CS  = 5;
const int TFT_DC  = 2;
const int TFT_RST = 4;
Adafruit_ILI9341 tft = Adafruit_ILI9341(TFT_CS, TFT_DC, TFT_RST);
Adafruit_ADS1115 ads;

const int NUM_SAMPLES = 64;  // Fast & low noise at 860 SPS (~18 ms total)
const int MAX_STEPS = 4000;
const float PLOT_MIN_MV = 0.0;
const float PLOT_MAX_MV = 38.0;

int current_step = 0;
int prev_x = -1;
int prev_y = -1;
int fit_prev_x = -1;
int fit_prev_y = -1;

void drawGrid() {
  tft.fillScreen(ILI9341_WHITE);
  tft.drawRect(10, 10, 300, 220, ILI9341_BLACK);
  tft.setCursor(20, 18);
  tft.setTextColor(ILI9341_GREEN, ILI9341_WHITE);
  tft.setTextSize(2);
  tft.print("Power Distribution");
}

void resetPlot() {
  drawGrid();
  current_step = 0;
  prev_x = -1;
  prev_y = -1;
  fit_prev_x = -1;
  fit_prev_y = -1;
}

float readPhotodiodeVoltage() {
  float sum_volts = 0.0;
  for (int i = 0; i < NUM_SAMPLES; i++) {
    int16_t raw_adc = ads.readADC_SingleEnded(0);
    sum_volts += ads.computeVolts(raw_adc);
  }
  return sum_volts / NUM_SAMPLES;
}

void plotMeasurement(float pd_mv) {
  int plot_x = map(current_step, 0, MAX_STEPS, 15, 305);
  int plot_y = map((int)pd_mv, (int)PLOT_MIN_MV, (int)PLOT_MAX_MV, 220, 20);
  plot_y = constrain(plot_y, 20, 220);

  if (prev_x != -1 && prev_y != -1) {
    tft.drawLine(prev_x, prev_y, plot_x, plot_y, ILI9341_CYAN);
  }
  tft.fillCircle(plot_x, plot_y, 2, ILI9341_BLACK);
  prev_x = plot_x;
  prev_y = plot_y;
  current_step++;
}

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);

  if (!ads.begin(0x48)) {
    while (1) { delay(1000); }
  }

  ads.setGain(GAIN_SIXTEEN);             // +/- 0.256 V range
  ads.setDataRate(RATE_ADS1115_860SPS);

  tft.begin();
  tft.setRotation(1);
  resetPlot();
  // DO NOT add Serial.println here
}

void loop() {
  if (Serial.available() <= 0) return;

  String command = Serial.readStringUntil('\n');
  command.trim();

  if (command == "RESET") {
    resetPlot();
    Serial.println("OK");
    return;
  }

  if (command == "READ") {
    float pd_voltage = readPhotodiodeVoltage();
    plotMeasurement(pd_voltage * 1000.0);
    Serial.println(pd_voltage, 6);
    return;
  }

  if (command.startsWith("FIT_LINE:")) {
    int commaIndex = command.indexOf(',');
    if (commaIndex > 0) {
      int fx = command.substring(9, commaIndex).toInt();
      int fy = command.substring(commaIndex + 1).toInt();
      if (fit_prev_x != -1 && fit_prev_y != -1) {
        tft.drawLine(fit_prev_x, fit_prev_y, fx, fy, ILI9341_RED);
      }
      fit_prev_x = fx;
      fit_prev_y = fy;
    }
    return;
  }

  if (command.startsWith("FIT:")) {
    String w0_str = command.substring(4);
    tft.setCursor(180, 18);
    tft.setTextColor(ILI9341_YELLOW, ILI9341_WHITE);
    tft.setTextSize(1);
    tft.print("w0: " + w0_str + " um");
    return;
  }

  Serial.println("ERROR");
}
