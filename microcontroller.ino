/* KivyHw demo project
 *
 * This is a small demonstration of using Kivy on a single-board computer
 * to interact with an external microcontroller on a serial port connection.
 *
 * This code drives a small ring of neopixels, reads from a potentiometer,
 * and reads from a DHT11 temp/humidity sensor.
 *
 * It uses these libraries: FastLED, Adafruit_Sensor, DHT, which can be
 * installed via the Arduino library manager.
 *
 * Customizations:
 * 1. Change the PIN_* defines to match your actual connections
 * 2. Change NUM_LEDS for different sizes of neopixel strands
 * 3. Update code to reflect actual sensors used (if needed)
 *
 * This code expects to receive a single byte containing the desired LED
 * hue value (raw binary, not ASCII). It transmits an ASCII string that
 * looks like ":pot,temp,hue\r\n" with regular base-10 integer values.
 */

#include <FastLED.h>
#define NUM_LEDS 16
#define PIN_LED 19

CRGBArray<NUM_LEDS> leds;

#include <Adafruit_Sensor.h>
#include <DHT.h>
#include <DHT_U.h>
#define PIN_DHT 7
#define DHTTYPE DHT11

DHT_Unified dht(PIN_DHT, DHTTYPE);
uint32_t dhtDelayMS;
unsigned nextDhtReadingTime;
unsigned temp = -1;
unsigned hum = -1;

#define PIN_POT A0

void setup() {
  Serial.begin(115200);
  
  FastLED.addLeds<NEOPIXEL, PIN_LED>(leds, NUM_LEDS);
  setHue(0);
  
  pinMode(PIN_POT, INPUT);

  dht.begin();
  sensor_t sensor;
  dht.temperature().getSensor(&sensor);
  /*
  Serial.println(F("------------------------------------"));
  Serial.println(F("Temperature Sensor"));
  Serial.print  (F("Sensor Type: ")); Serial.println(sensor.name);
  Serial.print  (F("Driver Ver:  ")); Serial.println(sensor.version);
  Serial.print  (F("Unique ID:   ")); Serial.println(sensor.sensor_id);
  Serial.print  (F("Max Value:   ")); Serial.print(sensor.max_value); Serial.println(F("°C"));
  Serial.print  (F("Min Value:   ")); Serial.print(sensor.min_value); Serial.println(F("°C"));
  Serial.print  (F("Resolution:  ")); Serial.print(sensor.resolution); Serial.println(F("°C"));
  Serial.println(F("------------------------------------"));
  */
  // Print humidity sensor details.
  dht.humidity().getSensor(&sensor);
  /*
  Serial.println(F("Humidity Sensor"));
  Serial.print  (F("Sensor Type: ")); Serial.println(sensor.name);
  Serial.print  (F("Driver Ver:  ")); Serial.println(sensor.version);
  Serial.print  (F("Unique ID:   ")); Serial.println(sensor.sensor_id);
  Serial.print  (F("Max Value:   ")); Serial.print(sensor.max_value); Serial.println(F("%"));
  Serial.print  (F("Min Value:   ")); Serial.print(sensor.min_value); Serial.println(F("%"));
  Serial.print  (F("Resolution:  ")); Serial.print(sensor.resolution); Serial.println(F("%"));
  Serial.println(F("------------------------------------"));
  */
  // Set delay between sensor readings based on sensor details.
  dhtDelayMS = sensor.min_delay / 1000;
  nextDhtReadingTime = 0;
}

void setHue(unsigned hue)
{
  for(int i = 0; i < NUM_LEDS; i++) {  
    leds[i] = CHSV(hue, 255, 50);
  }
  FastLED.show();
}

unsigned long nextPrintTime = 0;

void loop() {
  // Update LED if commanded to
  if (Serial.available() > 0) {
    setHue(Serial.read());
  }

  // Read from potentiometer
  unsigned pot = analogRead(PIN_POT);

  // Read from Temperature / Humidity sensor, if it's time 
  if (millis() >= nextDhtReadingTime) {
    sensors_event_t event;
    dht.temperature().getEvent(&event);
    if (!isnan(event.temperature)) {
      temp = event.temperature;
    }
    dht.humidity().getEvent(&event);
    if (!isnan(event.relative_humidity)) {
      hum = event.relative_humidity;
    }
    nextDhtReadingTime = millis() + dhtDelayMS;
  }

  if (millis() >= nextPrintTime) {
    // Transmit the current state
    Serial.print(":");
    Serial.print(pot);
    Serial.print(",");
    Serial.print(temp);
    Serial.print(",");
    Serial.print(hum);
    Serial.println("");
    nextPrintTime = millis() + 10;
  }
}
