//DogPal is a smart vending machine system for canine medications developed by the Cool Pals Group, 
//Batch 2026 Computer Engineering (CPE) students. To support documentation, maintenance, and future development, 
//the project's source codes were uploaded to a GitHub repository for future developers, researchers, and CPE students who may continue or enhance the system.

// ==========================================
// MERGED ARDUINO CODE
// COIN SLOT + TB74 BILL ACCEPTOR
// 4 ALARM SWITCHES + 1 DRAWER LIGHT SWITCH
// MPU6050 SHAKE SENSOR
// 3 IR DROP SENSORS
// SUPPORTS: 20, 50, 100, 200, 500, 1000 BILLS
// ==========================================

#include <Wire.h>
#include <avr/interrupt.h>

// ==========================================
// PAYMENT INPUTS
// ==========================================
const byte coinPin = 2;
const byte billPin = 3;

// ==========================================
// SWITCHES
// switch1, switch2, switch3, switch5 = MAIN DOORS
// switch4 = DRAWER LIGHT SWITCH
// ==========================================
const byte switch1Pin = 4;
const byte switch2Pin = 5;
const byte switch3Pin = 6;
const byte switch4Pin = 7;   // drawer switch
const byte ledPin     = 8;
const byte switch5Pin = 12;  // NEW main door switch

bool lastSwitch1Closed = false;
bool lastSwitch2Closed = false;
bool lastSwitch3Closed = false;
bool lastSwitch4Closed = false;
bool lastSwitch5Closed = false;

unsigned long switchLastChangeMs = 0;
const unsigned long switchDebounceMs = 50;

// ==========================================
// IR SENSORS
// ==========================================
const byte irSensor1Pin = 9;   // PB1 / PCINT1
const byte irSensor2Pin = 10;  // PB2 / PCINT2
const byte irSensor3Pin = 11;  // PB3 / PCINT3

volatile bool ir1Blocked = false;
volatile bool ir2Blocked = false;
volatile bool ir3Blocked = false;

volatile bool ir1ChangedPending = false;
volatile bool ir2ChangedPending = false;
volatile bool ir3ChangedPending = false;

volatile bool dropEventPending = false;
volatile unsigned long pendingDropCount = 0;
volatile unsigned long dropCount = 0;

volatile unsigned long lastDropMicros = 0;
const unsigned long dropDebounceUs = 80000;

volatile uint8_t lastPortBState = 0;

// ==========================================
// MPU6050
// ==========================================
const byte MPU_ADDR = 0x68;
bool mpuReady = false;

int16_t ax, ay, az;
int16_t gx, gy, gz;
int16_t lastAx = 0;
int16_t lastAy = 0;
int16_t lastAz = 0;

unsigned long lastShakeCheckMs = 0;
const unsigned long shakeSampleIntervalMs = 50;
long shakeThreshold = 8000;
unsigned long lastShakeAlarmMs = 0;
const unsigned long shakeAlarmCooldownMs = 50;

// ==========================================
// COIN VARIABLES
// ==========================================
volatile byte coinPulseCount = 0;
volatile unsigned long coinLastPulseMillis = 0;
volatile unsigned long coinLastEdgeMicros = 0;

// ==========================================
// BILL VARIABLES
// ==========================================
volatile unsigned int billPulseCount = 0;
volatile unsigned long billLastPulseMicros = 0;
volatile unsigned long billLastPulseMillis = 0;

// ==========================================
// TIMING
// ==========================================
const unsigned long coinDebounceUs = 20000;
const unsigned long coinDoneTimeout = 400;

const unsigned long billDebounceUs = 8000;
const unsigned long billDoneMs = 1200;

// ==========================================
// MONEY
// ==========================================
int totalMoney = 0;

// ==========================================
// STARTUP FILTER
// ==========================================
unsigned long startupIgnoreMs = 1500;
unsigned long bootTimeMs = 0;

// ==========================================
// COIN ISR
// ==========================================
void coinISR() {
  unsigned long nowUs = micros();
  if (nowUs - coinLastEdgeMicros > coinDebounceUs) {
    coinPulseCount++;
    coinLastPulseMillis = millis();
  }
  coinLastEdgeMicros = nowUs;
}

// ==========================================
// BILL ISR
// ==========================================
void billISR() {
  unsigned long nowUs = micros();
  if (nowUs - billLastPulseMicros > billDebounceUs) {
    billPulseCount++;
    billLastPulseMicros = nowUs;
    billLastPulseMillis = millis();
  }
}

// ==========================================
// IR PIN CHANGE INTERRUPT ISR
// D9, D10, D11 on Uno/Nano = PB1, PB2, PB3
// LOW = blocked because INPUT_PULLUP
// ==========================================
ISR(PCINT0_vect) {
  uint8_t currentPortB = PINB;
  uint8_t changedBits = currentPortB ^ lastPortBState;
  unsigned long nowUs = micros();

  if (changedBits & _BV(PB1)) {
    bool blocked = !(currentPortB & _BV(PB1));
    ir1Blocked = blocked;
    ir1ChangedPending = true;

    if (blocked && (unsigned long)(nowUs - lastDropMicros) > dropDebounceUs) {
      dropCount++;
      pendingDropCount = dropCount;
      dropEventPending = true;
      lastDropMicros = nowUs;
    }
  }

  if (changedBits & _BV(PB2)) {
    bool blocked = !(currentPortB & _BV(PB2));
    ir2Blocked = blocked;
    ir2ChangedPending = true;

    if (blocked && (unsigned long)(nowUs - lastDropMicros) > dropDebounceUs) {
      dropCount++;
      pendingDropCount = dropCount;
      dropEventPending = true;
      lastDropMicros = nowUs;
    }
  }

  if (changedBits & _BV(PB3)) {
    bool blocked = !(currentPortB & _BV(PB3));
    ir3Blocked = blocked;
    ir3ChangedPending = true;

    if (blocked && (unsigned long)(nowUs - lastDropMicros) > dropDebounceUs) {
      dropCount++;
      pendingDropCount = dropCount;
      dropEventPending = true;
      lastDropMicros = nowUs;
    }
  }

  lastPortBState = currentPortB;
}

// ==========================================
// MONEY MAPPING
// ==========================================
int getCoinValue(byte count) {
  if (count == 1)  return 1;
  if (count == 5)  return 5;
  if (count == 10) return 10;
  if (count == 20) return 20;
  if (count >= 1 && count <= 3) return 1;
  if (count >= 4 && count <= 7) return 5;
  if (count >= 8 && count <= 17) return 10;
  if (count >= 18 && count <= 23) return 20;
  return 0;
}

int getBillValue(unsigned int count) {
  if (count == 2)   return 20;
  if (count == 5)   return 50;
  if (count == 10)  return 100;
  if (count == 20)  return 200;
  if (count == 50)  return 500;
  if (count >= 8 && count <= 17) return 100;
  if (count >= 18 && count <= 30) return 200;
  if (count >= 40 && count <= 60) return 500;
  if (count >= 70 && count <= 500) return 1000;
  return 0;
}

void sendPaymentUpdate(int insertedValue) {
  Serial.print("PAY:");
  Serial.print(insertedValue);
  Serial.print(":");
  Serial.println(totalMoney);
}

void resetMoney() {
  totalMoney = 0;
  noInterrupts();
  coinPulseCount = 0;
  billPulseCount = 0;
  interrupts();
  Serial.println("RESET:0");
}

void resetDropSystem() {
  noInterrupts();
  dropCount = 0;
  pendingDropCount = 0;
  dropEventPending = false;
  ir1ChangedPending = false;
  ir2ChangedPending = false;
  ir3ChangedPending = false;
  lastDropMicros = 0;
  interrupts();

  Serial.println("DROP_RESET:0");
}

// ==========================================
// SWITCH FUNCTIONS
// ==========================================
bool isSwitch1Closed() { return digitalRead(switch1Pin) == LOW; }
bool isSwitch2Closed() { return digitalRead(switch2Pin) == LOW; }
bool isSwitch3Closed() { return digitalRead(switch3Pin) == LOW; }
bool isSwitch4Closed() { return digitalRead(switch4Pin) == LOW; } // drawer
bool isSwitch5Closed() { return digitalRead(switch5Pin) == LOW; } // new main door

void updateDrawerLight() {
  if (isSwitch4Closed()) {
    digitalWrite(ledPin, LOW);
  } else {
    digitalWrite(ledPin, HIGH);
  }
}

void printSwitchStatus() {
  Serial.print("SW1:");
  Serial.print(isSwitch1Closed() ? "CLOSED" : "OPEN");
  Serial.print(" | SW2:");
  Serial.print(isSwitch2Closed() ? "CLOSED" : "OPEN");
  Serial.print(" | SW3:");
  Serial.print(isSwitch3Closed() ? "CLOSED" : "OPEN");
  Serial.print(" | SW4:");
  Serial.print(isSwitch4Closed() ? "CLOSED" : "OPEN");
  Serial.print(" | SW5:");
  Serial.println(isSwitch5Closed() ? "CLOSED" : "OPEN");
}

void handleSwitches() {
  bool currentSwitch1Closed = isSwitch1Closed();
  bool currentSwitch2Closed = isSwitch2Closed();
  bool currentSwitch3Closed = isSwitch3Closed();
  bool currentSwitch4Closed = isSwitch4Closed();
  bool currentSwitch5Closed = isSwitch5Closed();

  updateDrawerLight();

  if (
    currentSwitch1Closed != lastSwitch1Closed ||
    currentSwitch2Closed != lastSwitch2Closed ||
    currentSwitch3Closed != lastSwitch3Closed ||
    currentSwitch4Closed != lastSwitch4Closed ||
    currentSwitch5Closed != lastSwitch5Closed
  ) {
    if (millis() - switchLastChangeMs > switchDebounceMs) {
      switchLastChangeMs = millis();

      lastSwitch1Closed = currentSwitch1Closed;
      lastSwitch2Closed = currentSwitch2Closed;
      lastSwitch3Closed = currentSwitch3Closed;
      lastSwitch4Closed = currentSwitch4Closed;
      lastSwitch5Closed = currentSwitch5Closed;

      printSwitchStatus();

      // Main doors are switch1, switch2, switch3, switch5
      if (!currentSwitch1Closed || !currentSwitch2Closed || !currentSwitch3Closed || !currentSwitch5Closed) {
        Serial.println("ALARM:ONE_OR_MORE_MAIN_SWITCH_OPEN");
      } else {
        Serial.println("MAIN_SWITCHES_CLOSED");
      }

      // Drawer/light logic stays on switch4
      if (currentSwitch4Closed) {
        Serial.println("DRAWER:CLOSED LED:OFF");
      } else {
        Serial.println("DRAWER:OPEN LED:ON");
      }

      Serial.println("------------------");
    }
  }
}

// ==========================================
// MPU6050 FUNCTIONS
// ==========================================
void writeMPU(byte reg, byte data) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  Wire.write(data);
  Wire.endTransmission();
}

bool initMPU6050() {
  Wire.begin();

  writeMPU(0x6B, 0x00);

  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x75);
  if (Wire.endTransmission(false) != 0) {
    return false;
  }

  Wire.requestFrom(MPU_ADDR, (byte)1);
  if (Wire.available()) {
    byte whoAmI = Wire.read();
    return (whoAmI == 0x68);
  }

  return false;
}

bool readMPU6050() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  if (Wire.endTransmission(false) != 0) {
    return false;
  }

  Wire.requestFrom(MPU_ADDR, (byte)14);
  if (Wire.available() < 14) {
    return false;
  }

  ax = (Wire.read() << 8) | Wire.read();
  ay = (Wire.read() << 8) | Wire.read();
  az = (Wire.read() << 8) | Wire.read();

  Wire.read();
  Wire.read();

  gx = (Wire.read() << 8) | Wire.read();
  gy = (Wire.read() << 8) | Wire.read();
  gz = (Wire.read() << 8) | Wire.read();

  return true;
}

void handleShakeSensor() {
  if (!mpuReady) return;
  if (millis() - lastShakeCheckMs < shakeSampleIntervalMs) return;

  lastShakeCheckMs = millis();

  if (!readMPU6050()) {
    Serial.println("MPU_READ_ERROR");
    return;
  }

  long deltaX = abs(ax - lastAx);
  long deltaY = abs(ay - lastAy);
  long deltaZ = abs(az - lastAz);
  long shakeLevel = deltaX + deltaY + deltaZ;

  lastAx = ax;
  lastAy = ay;
  lastAz = az;

  if (millis() - bootTimeMs < 2000) return;

  if (shakeLevel > shakeThreshold) {
    if (millis() - lastShakeAlarmMs > shakeAlarmCooldownMs) {
      Serial.print("ALARM:SHAKING_DETECTED LEVEL=");
      Serial.println(shakeLevel);
      lastShakeAlarmMs = millis();
    }
  }
}

// ==========================================
// PROCESS IR EVENTS OUTSIDE ISR
// ==========================================
void processIRSerialEvents() {
  bool printIr1 = false;
  bool printIr2 = false;
  bool printIr3 = false;
  bool ir1State = false;
  bool ir2State = false;
  bool ir3State = false;
  bool printDrop = false;
  unsigned long dropValue = 0;

  noInterrupts();
  if (ir1ChangedPending) {
    printIr1 = true;
    ir1State = ir1Blocked;
    ir1ChangedPending = false;
  }
  if (ir2ChangedPending) {
    printIr2 = true;
    ir2State = ir2Blocked;
    ir2ChangedPending = false;
  }
  if (ir3ChangedPending) {
    printIr3 = true;
    ir3State = ir3Blocked;
    ir3ChangedPending = false;
  }
  if (dropEventPending) {
    printDrop = true;
    dropValue = pendingDropCount;
    dropEventPending = false;
  }
  interrupts();

  if (printIr1) {
    Serial.println(ir1State ? "IR1:BLOCKED" : "IR1:CLEAR");
  }
  if (printIr2) {
    Serial.println(ir2State ? "IR2:BLOCKED" : "IR2:CLEAR");
  }
  if (printIr3) {
    Serial.println(ir3State ? "IR3:BLOCKED" : "IR3:CLEAR");
  }
  if (printDrop) {
    Serial.print("DROP:");
    Serial.println(dropValue);
  }
}

// ==========================================
// PAYMENT PROCESSING
// ==========================================
void processCoins() {
  noInterrupts();
  byte count = coinPulseCount;
  unsigned long lastPulse = coinLastPulseMillis;
  interrupts();

  if (count > 0 && (millis() - lastPulse > coinDoneTimeout)) {
    noInterrupts();
    count = coinPulseCount;
    coinPulseCount = 0;
    interrupts();

    if (millis() - bootTimeMs < startupIgnoreMs) {
      Serial.println("Ignored startup coin pulse");
      return;
    }

    int coinValue = getCoinValue(count);

    Serial.print("Coin detected. Pulse count = ");
    Serial.println(count);

    if (coinValue > 0) {
      totalMoney += coinValue;

      Serial.print("Detected coin: PHP ");
      Serial.println(coinValue);

      Serial.print("Total money: PHP ");
      Serial.println(totalMoney);

      sendPaymentUpdate(coinValue);
    } else {
      Serial.println("Unknown coin / bad pulse read");
    }

    Serial.println("------------------");
  }
}

void processBills() {
  noInterrupts();
  unsigned int count = billPulseCount;
  unsigned long lastPulse = billLastPulseMillis;
  interrupts();

  if (count > 0 && (millis() - lastPulse > billDoneMs)) {
    noInterrupts();
    count = billPulseCount;
    billPulseCount = 0;
    interrupts();

    if (millis() - bootTimeMs < startupIgnoreMs) {
      Serial.println("Ignored startup bill pulse");
      return;
    }

    int billValue = getBillValue(count);

    Serial.print("Bill detected. Pulse count = ");
    Serial.println(count);

    if (billValue > 0) {
      totalMoney += billValue;

      Serial.print("Detected bill: PHP ");
      Serial.println(billValue);

      Serial.print("Total money: PHP ");
      Serial.println(totalMoney);

      sendPaymentUpdate(billValue);
    } else {
      Serial.println("Unknown bill mapping");
    }

    Serial.println("------------------");
  }
}

// ==========================================
// SERIAL COMMANDS FROM RASPBERRY PI
// ==========================================
void handleSerialCommands() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd == "RESET") {
      resetMoney();
    }
    else if (cmd == "RESET_DROP") {
      resetDropSystem();
    }
    else if (cmd == "STATUS") {
      Serial.print("TOTAL_MONEY:");
      Serial.println(totalMoney);

      Serial.print("DROP_COUNT:");
      Serial.println(dropCount);

      Serial.print("IR1:");
      Serial.println(ir1Blocked ? "BLOCKED" : "CLEAR");

      Serial.print("IR2:");
      Serial.println(ir2Blocked ? "BLOCKED" : "CLEAR");

      Serial.print("IR3:");
      Serial.println(ir3Blocked ? "BLOCKED" : "CLEAR");

      Serial.print("SW1:");
      Serial.println(isSwitch1Closed() ? "CLOSED" : "OPEN");

      Serial.print("SW2:");
      Serial.println(isSwitch2Closed() ? "CLOSED" : "OPEN");

      Serial.print("SW3:");
      Serial.println(isSwitch3Closed() ? "CLOSED" : "OPEN");

      Serial.print("SW4:");
      Serial.println(isSwitch4Closed() ? "CLOSED" : "OPEN");

      Serial.print("SW5:");
      Serial.println(isSwitch5Closed() ? "CLOSED" : "OPEN");
    }
  }
}

// ==========================================
// SETUP
// ==========================================
void setup() {
  Serial.begin(115200);

  pinMode(coinPin, INPUT_PULLUP);
  pinMode(billPin, INPUT_PULLUP);

  pinMode(switch1Pin, INPUT_PULLUP);
  pinMode(switch2Pin, INPUT_PULLUP);
  pinMode(switch3Pin, INPUT_PULLUP);
  pinMode(switch4Pin, INPUT_PULLUP);
  pinMode(switch5Pin, INPUT_PULLUP);

  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, LOW);

  pinMode(irSensor1Pin, INPUT_PULLUP);
  pinMode(irSensor2Pin, INPUT_PULLUP);
  pinMode(irSensor3Pin, INPUT_PULLUP);

  bootTimeMs = millis();

  attachInterrupt(digitalPinToInterrupt(coinPin), coinISR, FALLING);
  attachInterrupt(digitalPinToInterrupt(billPin), billISR, FALLING);

  // Initialize switch state
  lastSwitch1Closed = isSwitch1Closed();
  lastSwitch2Closed = isSwitch2Closed();
  lastSwitch3Closed = isSwitch3Closed();
  lastSwitch4Closed = isSwitch4Closed();
  lastSwitch5Closed = isSwitch5Closed();

  // Initialize IR state from actual pins
  ir1Blocked = (digitalRead(irSensor1Pin) == LOW);
  ir2Blocked = (digitalRead(irSensor2Pin) == LOW);
  ir3Blocked = (digitalRead(irSensor3Pin) == LOW);

  // Initialize pin change interrupt tracking
  lastPortBState = PINB;

  // Enable pin-change interrupt group for PORTB (D8-D13)
  PCICR |= _BV(PCIE0);

  // Enable D9, D10, D11 only
  PCMSK0 |= _BV(PCINT1);
  PCMSK0 |= _BV(PCINT2);
  PCMSK0 |= _BV(PCINT3);

  updateDrawerLight();
  printSwitchStatus();

  if (!lastSwitch1Closed || !lastSwitch2Closed || !lastSwitch3Closed || !lastSwitch5Closed) {
    Serial.println("ALARM:ONE_OR_MORE_MAIN_SWITCH_OPEN");
  } else {
    Serial.println("MAIN_SWITCHES_CLOSED");
  }

  if (lastSwitch4Closed) {
    Serial.println("DRAWER:CLOSED LED:OFF");
  } else {
    Serial.println("DRAWER:OPEN LED:ON");
  }

  Serial.print("IR1:");
  Serial.println(ir1Blocked ? "BLOCKED" : "CLEAR");

  Serial.print("IR2:");
  Serial.println(ir2Blocked ? "BLOCKED" : "CLEAR");

  Serial.print("IR3:");
  Serial.println(ir3Blocked ? "BLOCKED" : "CLEAR");

  mpuReady = initMPU6050();
  if (mpuReady) {
    Serial.println("MPU6050_READY");
    if (readMPU6050()) {
      lastAx = ax;
      lastAy = ay;
      lastAz = az;
    }
  } else {
    Serial.println("MPU6050_NOT_DETECTED");
  }

  Serial.println("SYSTEM_READY");
}

// ==========================================
// LOOP
// ==========================================
void loop() {
  handleSwitches();
  handleShakeSensor();
  processIRSerialEvents();
  processCoins();
  processBills();
  handleSerialCommands();
}