// Ohmni Stack-chan USB firmware.
//
// Line-delimited JSON over the CoreS3's USB serial port. One command per line,
// one JSON reply per command. See ../README.md for the protocol.
//
// Hardware facts come from M5Stack's open-source StackChan firmware
// (github.com/m5stack/StackChan, firmware/main/hal):
//   - Feetech SCS bus servos on UART1 @ 1 Mbaud, TX=GPIO6, RX=GPIO7
//     id 1 = yaw (head turn), id 2 = pitch (head tilt), 0.3125 deg per raw step
//   - PY32 IO expander at 0x6F on the internal I2C bus:
//     pin 0 = servo power enable, pin 13 = 12 RGB LEDs
//   - per-robot servo zero positions in NVS namespace "servo"
#include <Arduino.h>
#include <ArduinoJson.h>
#include <M5Unified.h>
#include <Preferences.h>
#include <mbedtls/base64.h>

#include "SCSCL.h"

static const char* kFirmware = "ohmni-stackchan";
static const char* kVersion  = "0.3.0";

// ---------------------------------------------------------------- IO expander

namespace ioe {

constexpr uint8_t kAddr = 0x6F;
constexpr uint32_t kFreq = 100000;
constexpr uint8_t REG_VERSION = 0x02, REG_GPIO_M_L = 0x03, REG_GPIO_O_L = 0x05,
                  REG_GPIO_PU_L = 0x09, REG_GPIO_PD_L = 0x0B, REG_GPIO_DRV_L = 0x13,
                  REG_LED_CFG = 0x24, REG_LED_RAM = 0x30;
constexpr uint8_t kServoPowerPin = 0, kLedPin = 13, kLedCount = 12;

bool ok = false;

uint8_t read8(uint8_t reg) { return M5.In_I2C.readRegister8(kAddr, reg, kFreq); }
void write8(uint8_t reg, uint8_t v) { M5.In_I2C.writeRegister8(kAddr, reg, v, kFreq); }

void writeBit(uint8_t reg_l, uint8_t pin, bool value)
{
    uint8_t reg  = pin < 8 ? reg_l : reg_l + 1;
    uint8_t mask = 1 << (pin & 7);
    uint8_t v    = read8(reg);
    write8(reg, value ? (v | mask) : (v & ~mask));
}

void setOutputPullUp(uint8_t pin)
{
    writeBit(REG_GPIO_M_L, pin, true);
    writeBit(REG_GPIO_PD_L, pin, false);
    writeBit(REG_GPIO_PU_L, pin, true);
}

bool begin()
{
    // The expander can boot slower than the ESP32; the factory firmware waits up to 1.2 s.
    for (int i = 0; i < 8 && !ok; i++) {
        delay(200);
        uint8_t v = read8(REG_VERSION);
        ok        = v != 0 && v != 0xFF;
    }
    if (!ok) return false;
    setOutputPullUp(kServoPowerPin);
    setOutputPullUp(kLedPin);
    writeBit(REG_GPIO_DRV_L, kLedPin, false);  // push-pull
    write8(REG_LED_CFG, kLedCount & 0x3F);
    return true;
}

void setServoPower(bool on)
{
    if (ok) writeBit(REG_GPIO_O_L, kServoPowerPin, on);
}

void setLed(uint8_t i, uint8_t r, uint8_t g, uint8_t b)
{
    if (!ok || i >= kLedCount) return;
    uint16_t c      = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3);
    uint8_t data[2] = {uint8_t(c & 0xFF), uint8_t(c >> 8)};
    M5.In_I2C.writeRegister(kAddr, REG_LED_RAM + i * 2, data, 2, kFreq);
}

void showLeds()
{
    if (ok) write8(REG_LED_CFG, read8(REG_LED_CFG) | (1 << 6));
}

void fillLeds(uint8_t r, uint8_t g, uint8_t b)
{
    for (uint8_t i = 0; i < kLedCount; i++) setLed(i, r, g, b);
    showLeds();
}

}  // namespace ioe

// --------------------------------------------------------------------- servos

static void sendJson(JsonDocument& doc);

namespace servo {

struct Axis {
    const char* name;
    uint8_t id;
    const char* nvsKey;
    int defaultZero;
    float minDeg, maxDeg;  // factory angle limits
    int zero;
    // Runtime raw limits; a stall narrows them so we stop pushing into the obstacle.
    int rawMin = 0, rawMax = 1000;
    // Current move, for stall detection.
    bool moving = false;
    int target = 0, startRaw = 0;
    uint32_t startMs = 0, durMs = 0;
    // Stall detector state (mirrors the factory firmware's ScsServo).
    uint32_t lastCheck = 0;
    int lastRaw = 0, lastCurrent = 0, lastLoad = 0, lastDir = 0, confirm = 0;
    bool lastValid = false;
};

// Factory limits: yaw -128..128 deg, pitch 3..87 deg (firmware/main/hal/hal_servo.cpp).
Axis yaw   = {"yaw", 1, "zero_pos_1", 460, -128.0f, 128.0f, 460};
Axis pitch = {"pitch", 2, "zero_pos_2", 620, 3.0f, 87.0f, 620};

SCSCL bus;
bool torque = false;

// Factory thresholds (hal_servo.cpp). Raw units: position steps, current and load as reported by the servo.
constexpr uint32_t kStallIntervalMs  = 50;
constexpr int kStallMinTargetDelta   = 8;
constexpr int kStallMaxPositionDelta = 1;
constexpr int kStallCurrentRise = 80, kStallLoadRise = 150;
constexpr int kStallCurrentAbs = 350, kStallLoadAbs = 650;
constexpr int kStallConfirmSamples = 2;
// Ours: only judge "stuck" when the planned move is at least this fast (raw steps per sample),
// because our servos get the final target at once instead of a smoothly moving one.
constexpr int kStallMinPlannedStep = 3;
constexpr uint32_t kMoveGraceMs    = 2000;

int degToRaw(const Axis& a, float deg)
{
    deg = constrain(deg, a.minDeg, a.maxDeg);
    return constrain(a.zero + int(lroundf(deg / 0.3125f)), a.rawMin, a.rawMax);
}

float rawToDeg(const Axis& a, int raw) { return (raw - a.zero) * 0.3125f; }

bool rawValid(int raw) { return raw >= 0 && raw <= 1000; }

void loadZero(Axis& a, Preferences& prefs)
{
    int v  = prefs.getInt(a.nvsKey, -1);
    a.zero = (v >= 0 && v <= 1000) ? v : a.defaultZero;
}

void begin()
{
    Preferences prefs;
    // Read-only: reuse the calibration the factory firmware stored, never overwrite it.
    if (prefs.begin("servo", true)) {
        loadZero(yaw, prefs);
        loadZero(pitch, prefs);
        prefs.end();
    }
    bus.begin(UART_NUM_1, 1000000, 6, 7);
}

void resetStallDetection(Axis& a)
{
    a.lastValid = false;
    a.lastDir   = 0;
    a.confirm   = 0;
}

void resetLimits()
{
    for (Axis* a : {&yaw, &pitch}) {
        a->rawMin = 0;
        a->rawMax = 1000;
        resetStallDetection(*a);
    }
}

void setTorque(bool on)
{
    bus.EnableTorque(yaw.id, on);
    bus.EnableTorque(pitch.id, on);
    torque = on;
    if (!on) {
        // The head may be repositioned by hand; forget obstacles found so far.
        yaw.moving = pitch.moving = false;
        resetLimits();
    }
}

void move(Axis& a, float deg, int ms)
{
    if (!torque) setTorque(true);
    ms = constrain(ms, 0, 10000);
    int startRaw = bus.ReadPos(a.id);
    a.target     = degToRaw(a, deg);
    a.startRaw   = rawValid(startRaw) ? startRaw : a.target;
    a.startMs    = millis();
    a.durMs      = ms;
    a.moving     = true;
    resetStallDetection(a);
    bus.WritePos(a.id, a.target, ms, 0);
}

// Returns NAN when the servo does not answer.
float read(const Axis& a)
{
    int raw = bus.ReadPos(a.id);
    return rawValid(raw) ? rawToDeg(a, raw) : NAN;
}

void handleStall(Axis& a, int raw, int dir, int current, int load)
{
    if (dir > 0)
        a.rawMax = min(a.rawMax, raw);
    else
        a.rawMin = max(a.rawMin, raw);
    a.moving = false;
    resetStallDetection(a);
    bus.WritePos(a.id, raw, 20, 0);  // hold where it stopped

    JsonDocument ev;
    ev["event"]   = "stall";
    ev["axis"]    = a.name;
    ev["deg"]     = roundf(rawToDeg(a, raw) * 10) / 10;
    ev["dir"]     = dir;
    ev["current"] = current;
    ev["load"]    = load;
    sendJson(ev);
}

void monitor(Axis& a)
{
    if (!a.moving || !torque) return;
    uint32_t now = millis();
    if (now - a.lastCheck < kStallIntervalMs) return;
    a.lastCheck = now;

    if (bus.FeedBack(a.id) < 0) {
        resetStallDetection(a);
        return;
    }
    int raw     = bus.ReadPos(-1);  // -1: decode the FeedBack buffer instead of a new bus read
    int current = abs(bus.ReadCurrent(-1));
    int load    = abs(bus.ReadLoad(-1));
    if (!rawValid(raw)) {
        resetStallDetection(a);
        return;
    }

    int delta = a.target - raw;
    if (abs(delta) < kStallMinTargetDelta || now - a.startMs > a.durMs + kMoveGraceMs) {
        a.moving = false;  // arrived, or close enough that the servo is just settling
        resetStallDetection(a);
        return;
    }

    uint32_t elapsed  = now - a.startMs;
    int plannedStep   = abs(a.target - a.startRaw) * int(kStallIntervalMs) / int(max<uint32_t>(a.durMs, 1));
    bool shouldMove   = elapsed >= a.durMs || plannedStep >= kStallMinPlannedStep;
    int dir           = delta > 0 ? 1 : -1;

    if (a.lastValid && dir == a.lastDir && shouldMove) {
        int posDelta       = abs(raw - a.lastRaw);
        bool stuck         = posDelta <= kStallMaxPositionDelta;
        bool currentSpike  = current >= kStallCurrentAbs || current - a.lastCurrent >= kStallCurrentRise;
        bool loadSpike     = load >= kStallLoadAbs || load - a.lastLoad >= kStallLoadRise;
        if (stuck && (currentSpike || loadSpike))
            a.confirm++;
        else if (!stuck)
            a.confirm = 0;
    } else {
        a.confirm = 0;
    }
    a.lastRaw     = raw;
    a.lastCurrent = current;
    a.lastLoad    = load;
    a.lastDir     = dir;
    a.lastValid   = true;

    if (a.confirm >= kStallConfirmSamples) handleStall(a, raw, dir, current, load);
}

void monitor()
{
    monitor(yaw);
    monitor(pitch);
}

}  // namespace servo

// --------------------------------------------------------------------- avatar

namespace face {

M5Canvas canvas(&M5.Display);
String expr     = "neutral";
float mouthOpen = 0.0f;  // 0..1, for speech
uint32_t nextBlink = 0, blinkUntil = 0;
bool dirty = true;
bool spriteOk = false;

const char* kExprs[] = {"neutral", "happy", "sad", "angry", "surprised", "sleepy", "thinking", "listening"};

bool valid(const String& e)
{
    for (auto* k : kExprs)
        if (e == k) return true;
    return false;
}

void drawEye(int cx, int cy, bool left, bool blinking)
{
    auto& c = canvas;
    const uint16_t W = TFT_WHITE;
    if (blinking || expr == "sleepy") {
        c.fillRect(cx - 18, cy - 2, 36, 5, W);
    } else if (expr == "happy") {
        c.fillArc(cx, cy + 6, 18, 12, 200, 340, W);
    } else if (expr == "surprised") {
        c.fillCircle(cx, cy, 20, W);
        c.fillCircle(cx, cy, 8, TFT_BLACK);
    } else if (expr == "listening") {  // big attentive eyes with a highlight
        c.fillCircle(cx, cy, 18, W);
        c.fillCircle(cx + 6, cy - 6, 5, TFT_BLACK);
    } else {
        c.fillCircle(cx, cy, 14, W);
    }
    if (expr == "angry") {  // slanted brows
        int dir = left ? 1 : -1;
        c.drawWideLine(cx - 22, cy - 30 - 8 * dir, cx + 22, cy - 30 + 8 * dir, 5, W);
    } else if (expr == "sad") {
        int dir = left ? -1 : 1;
        c.drawWideLine(cx - 22, cy - 28 - 6 * dir, cx + 22, cy - 28 + 6 * dir, 5, W);
    } else if (expr == "thinking" && !left) {
        c.drawWideLine(cx - 20, cy - 32, cx + 20, cy - 36, 5, W);
    }
}

void render()
{
    bool blinking = millis() < blinkUntil;
    auto& c       = canvas;
    c.fillSprite(TFT_BLACK);
    drawEye(90, 95, true, blinking);
    drawEye(230, 95, false, blinking);

    const int mx = 160, my = 168;
    const uint16_t W = TFT_WHITE;
    if (mouthOpen > 0.05f) {
        int h = 4 + int(mouthOpen * 26);
        c.fillEllipse(mx, my, 22, h, W);
    } else if (expr == "happy") {
        c.fillArc(mx, my - 12, 30, 24, 20, 160, W);
    } else if (expr == "sad") {
        c.fillArc(mx, my + 18, 30, 24, 200, 340, W);
    } else if (expr == "surprised") {
        c.fillEllipse(mx, my, 14, 18, W);
        c.fillEllipse(mx, my, 8, 12, TFT_BLACK);
    } else if (expr == "thinking") {
        c.drawWideLine(mx - 20, my + 4, mx + 20, my - 4, 5, W);
    } else if (expr == "listening") {
        c.fillCircle(mx, my, 9, W);
        c.fillCircle(mx, my, 5, TFT_BLACK);
        // "ear" arcs either side of the face
        c.fillArc(22, 120, 22, 18, 120, 240, 0x07FF);
        c.fillArc(298, 120, 22, 18, 300, 60, 0x07FF);
    } else {
        c.fillRect(mx - 24, my - 2, 48, 5, W);
    }
    c.pushSprite(0, 0);
}

void begin()
{
    M5.Display.setRotation(1);
    M5.Display.setBrightness(160);
    // 320x240x16bit = 150 KB: too big for internal RAM next to everything else.
    canvas.setPsram(true);
    canvas.setColorDepth(16);
    spriteOk = canvas.createSprite(M5.Display.width(), M5.Display.height()) != nullptr;
    nextBlink = millis() + 2500;
}

void tick()
{
    uint32_t now = millis();
    if (now >= nextBlink && expr != "sleepy") {
        blinkUntil = now + 140;
        nextBlink  = now + 2500 + random(0, 3500);
        dirty      = true;
    }
    if (blinkUntil && now >= blinkUntil) {
        blinkUntil = 0;
        dirty      = true;
    }
    if (dirty) {
        render();
        dirty = false;
    }
}

}  // namespace face

// ---------------------------------------------------------------- head touch

// Si12T capacitive touch controller with three pads along the top of the head
// (register sequence from m5stack/StackChan firmware/main/hal/drivers/Si12T).
namespace touch {

constexpr uint8_t kAddr = 0x68;
constexpr uint32_t kFreq = 100000;
constexpr uint32_t kPollMs = 25, kTapMaxMs = 350, kDoubleTapGapMs = 450;
constexpr int kSwipeThreshold = 40;  // position units, -100 (front) .. 100 (back)

bool ok = false;
void (*onDoubleTap)() = nullptr;

uint32_t lastPoll = 0, pressStart = 0, lastTapEnd = 0;
bool pressed = false, swiped = false;
int pressPos = 0;

void write8(uint8_t reg, uint8_t v) { M5.In_I2C.writeRegister8(kAddr, reg, v, kFreq); }

bool begin()
{
    ok = M5.In_I2C.writeRegister8(kAddr, 0x0A, 0x00, kFreq);  // probe + ref calibration ch1-8
    if (!ok) return false;
    write8(0x0B, 0x00);  // ref calibration ch9
    write8(0x0C, 0x00);  // channel hold off (enable) ch1-8
    write8(0x0D, 0x00);  // ch9
    write8(0x0E, 0x00);  // calibration hold off ch1-8
    write8(0x0F, 0x00);  // ch9
    write8(0x09, 0x0F);  // CTRL2: software reset
    write8(0x09, 0x07);
    write8(0x08, 0x22);  // CTRL1
    for (uint8_t reg = 0x02; reg <= 0x06; reg++) write8(reg, 0x33);  // sensitivity: low type, level 3 (factory)
    return true;
}

void emit(const char* gesture)
{
    JsonDocument ev;
    ev["event"]   = "touch";
    ev["gesture"] = gesture;
    sendJson(ev);
}

void tick()
{
    if (!ok) return;
    uint32_t now = millis();
    if (now - lastPoll < kPollMs) return;
    lastPoll = now;

    uint8_t v = M5.In_I2C.readRegister8(kAddr, 0x10, kFreq);
    uint8_t a = v & 3, b = (v >> 2) & 3, c = (v >> 4) & 3;  // intensity per pad, 0..3
    int total = a + b + c;
    bool touched = total > 0;
    int pos      = touched ? (c * 100 - a * 100) / total : 0;

    if (touched && !pressed) {
        pressed    = true;
        swiped     = false;
        pressStart = now;
        pressPos   = pos;
    } else if (touched && pressed && !swiped) {
        int delta = pos - pressPos;
        if (abs(delta) > kSwipeThreshold) {
            swiped = true;
            emit(delta > 0 ? "swipe_backward" : "swipe_forward");
        }
    } else if (!touched && pressed) {
        pressed = false;
        if (!swiped && now - pressStart <= kTapMaxMs) {
            if (lastTapEnd && now - lastTapEnd <= kDoubleTapGapMs) {
                lastTapEnd = 0;
                emit("double_tap");
                if (onDoubleTap) onDoubleTap();
            } else {
                lastTapEnd = now;
            }
        }
    }
}

}  // namespace touch

// --------------------------------------------------------------------- audio

namespace audio {

constexpr uint32_t kRate = 16000;
constexpr size_t kRecLen = 512;     // 32 ms per microphone chunk
constexpr int kRecBufs = 6;
constexpr size_t kPlayMax = 4096;   // samples per play command (256 ms)
constexpr int kPlayBufs = 4;        // > 2 in flight (playing + queued), so a refilled one is free
constexpr uint32_t kListenMaxMs = 15000;
constexpr uint8_t kPlayChannel = 0;

int16_t* rec[kRecBufs];
QueueHandle_t recReady;
int recNext = 0, recFree = kRecBufs;
int16_t* play[kPlayBufs];
int playNext = 0;

bool listening = false, audioMouth = false;
uint32_t listenStart = 0, seq = 0, drops = 0;
String prevExpr;
char line[1500];

void onRecDone(void*, void* data, size_t)
{
    for (int i = 0; i < kRecBufs; i++)
        if (rec[i] == data) {
            xQueueSend(recReady, &i, 0);
            return;
        }
}

void begin()
{
    for (auto& b : rec) b = (int16_t*)heap_caps_malloc(kRecLen * 2, MALLOC_CAP_8BIT);
    for (auto& b : play) b = (int16_t*)heap_caps_malloc(kPlayMax * 2, MALLOC_CAP_8BIT);
    recReady = xQueueCreate(kRecBufs, sizeof(int));
    M5.Mic.setBufferReleaseCallback(nullptr, onRecDone);
}

void sendEvent(const char* kind, const char* key, const char* value)
{
    JsonDocument ev;
    ev["event"] = "listen";
    ev["on"]    = strcmp(kind, "on") == 0;
    ev[key]     = value;
    if (!ev["on"]) {
        ev["chunks"] = seq;
        ev["drops"]  = drops;
    }
    sendJson(ev);
}

bool startListening(const char* source)
{
    if (listening) return true;
    M5.Speaker.stop();
    M5.Speaker.end();
    if (!M5.Mic.begin()) {
        M5.Speaker.begin();
        return false;
    }
    xQueueReset(recReady);
    listening   = true;
    listenStart = millis();
    seq = drops = 0;
    recNext     = 0;
    recFree     = kRecBufs;
    audioMouth  = false;
    prevExpr    = face::expr;
    face::expr      = "listening";
    face::mouthOpen = 0;
    face::dirty     = true;
    ioe::fillLeds(0, 160, 200);
    sendEvent("on", "source", source);
    return true;
}

void stopListening(const char* reason)
{
    if (!listening) return;
    M5.Mic.end();  // drops queued requests; their buffers are reusable afterwards
    listening = false;
    M5.Speaker.begin();
    face::expr  = prevExpr;
    face::dirty = true;
    ioe::fillLeds(0, 0, 0);
    sendEvent("off", "reason", reason);
}

void sendChunk(const int16_t* pcm)
{
    size_t n = snprintf(line, sizeof(line), "{\"event\":\"audio\",\"seq\":%u,\"pcm\":\"", (unsigned)seq++);
    size_t b64 = 0;
    mbedtls_base64_encode((unsigned char*)line + n, sizeof(line) - n - 4, &b64, (const unsigned char*)pcm, kRecLen * 2);
    n += b64;
    memcpy(line + n, "\"}\n", 3);
    n += 3;
    // Never block the loop on a slow host: drop the chunk if it doesn't fit.
    if ((size_t)Serial.availableForWrite() >= n)
        Serial.write((const uint8_t*)line, n);
    else
        drops++;
}

void tick()
{
    if (listening) {
        int idx;
        while (xQueueReceive(recReady, &idx, 0) == pdTRUE) {
            sendChunk(rec[idx]);
            recFree++;
        }
        while (recFree > 0 && M5.Mic.isRecording() < 2) {
            if (!M5.Mic.record(rec[recNext], kRecLen, kRate)) break;
            recNext = (recNext + 1) % kRecBufs;
            recFree--;
        }
        if (millis() - listenStart > kListenMaxMs) stopListening("timeout");
    } else if (audioMouth && !M5.Speaker.isPlaying(kPlayChannel)) {
        audioMouth      = false;
        face::mouthOpen = 0;
        face::dirty     = true;
    }
}

// Queue one chunk of 16 kHz mono int16 PCM (base64). Returns an error string or nullptr.
const char* playChunk(const char* b64, size_t b64len)
{
    if (listening) return "listening";
    int16_t* buf = play[playNext];
    size_t bytes = 0;
    if (mbedtls_base64_decode((unsigned char*)buf, kPlayMax * 2, &bytes, (const unsigned char*)b64, b64len) != 0)
        return "bad pcm";
    size_t samples = bytes / 2;
    if (!samples) return nullptr;

    // Wait for a queue slot (the host waits for our reply: that is the flow control).
    uint32_t t0 = millis();
    while (M5.Speaker.isPlaying(kPlayChannel) >= 2) {
        if (millis() - t0 > 1000) return "speaker busy";
        delay(2);
    }
    if (!M5.Speaker.playRaw(buf, samples, kRate, false, 1, kPlayChannel, false)) return "speaker refused";
    playNext = (playNext + 1) % kPlayBufs;

    double sum = 0;
    for (size_t i = 0; i < samples; i++) sum += double(buf[i]) * buf[i];
    face::mouthOpen = constrain(sqrt(sum / samples) / 5000.0, 0.0, 1.0);
    face::dirty     = true;
    audioMouth      = true;
    return nullptr;
}

}  // namespace audio

// ------------------------------------------------------------------- protocol

static void sendJson(JsonDocument& doc)
{
    serializeJson(doc, Serial);
    Serial.print('\n');
}

static void handle(JsonDocument& in)
{
    JsonDocument out;
    if (!in["id"].isNull()) out["id"] = in["id"];
    String cmd = in["cmd"] | "";
    out["ok"]  = true;

    if (cmd == "ping") {
        out["fw"]      = kFirmware;
        out["version"] = kVersion;
        out["ioe"]     = ioe::ok;
    } else if (cmd == "pose") {
        int ms = in["ms"] | 300;
        if (in["yaw"].is<float>()) servo::move(servo::yaw, in["yaw"].as<float>(), ms);
        if (in["pitch"].is<float>()) servo::move(servo::pitch, in["pitch"].as<float>(), ms);
    } else if (cmd == "state") {
        float y = servo::read(servo::yaw), p = servo::read(servo::pitch);
        if (isnan(y)) out["yaw"] = nullptr; else out["yaw"] = roundf(y * 10) / 10;
        if (isnan(p)) out["pitch"] = nullptr; else out["pitch"] = roundf(p * 10) / 10;
        out["torque"] = servo::torque;
        JsonObject lim = out["limits"].to<JsonObject>();
        for (servo::Axis* a : {&servo::yaw, &servo::pitch}) {
            JsonArray r = lim[a->name].to<JsonArray>();
            r.add(roundf(max(servo::rawToDeg(*a, a->rawMin), a->minDeg) * 10) / 10);
            r.add(roundf(min(servo::rawToDeg(*a, a->rawMax), a->maxDeg) * 10) / 10);
        }
        out["face"]   = face::expr;
        out["battery"] = M5.Power.getBatteryLevel();
    } else if (cmd == "torque") {
        servo::setTorque(in["on"] | false);
    } else if (cmd == "reset_limits") {
        servo::resetLimits();
    } else if (cmd == "face") {
        String e = in["expr"] | "";
        if (!e.isEmpty()) {
            if (!face::valid(e)) {
                out["ok"]    = false;
                out["error"] = "unknown expr";
            } else {
                face::expr = e;
            }
        }
        if (in["mouth"].is<float>()) face::mouthOpen = constrain(in["mouth"].as<float>(), 0.0f, 1.0f);
        face::dirty = true;
    } else if (cmd == "led") {
        // {"rgb":[r,g,b]} for all LEDs, or {"leds":[[r,g,b], ...]} for each of the 12.
        JsonArray all  = in["rgb"].as<JsonArray>();
        JsonArray each = in["leds"].as<JsonArray>();
        for (uint8_t i = 0; i < ioe::kLedCount; i++) {
            JsonArray c = !each.isNull() ? each[i].as<JsonArray>() : all;
            if (!c.isNull()) ioe::setLed(i, c[0] | 0, c[1] | 0, c[2] | 0);
        }
        ioe::showLeds();
    } else if (cmd == "diag") {
        out["board"]      = int(M5.getBoard());
        out["psram"]      = psramFound();
        out["psram_free"] = ESP.getFreePsram();
        out["heap_free"]  = ESP.getFreeHeap();
        out["display"]    = String(M5.Display.width()) + "x" + String(M5.Display.height());
        out["sprite"]     = face::spriteOk;
        out["speaker"]    = M5.Speaker.isEnabled();
        out["mic"]        = M5.Mic.isEnabled();
        out["touch"]      = touch::ok;
        out["volume"]     = M5.Speaker.getVolume();
        if (ioe::ok) {
            out["ioe_version"] = ioe::read8(ioe::REG_VERSION);
            out["ioe_mode_h"]  = ioe::read8(ioe::REG_GPIO_M_L + 1);
            out["ioe_out_l"]   = ioe::read8(ioe::REG_GPIO_O_L);
            out["led_cfg"]     = ioe::read8(ioe::REG_LED_CFG);
            uint8_t ram[4]     = {};
            M5.In_I2C.readRegister(ioe::kAddr, ioe::REG_LED_RAM, ram, sizeof(ram), ioe::kFreq);
            JsonArray r = out["led_ram"].to<JsonArray>();
            for (uint8_t v : ram) r.add(v);
        }
    } else if (cmd == "tone") {
        if (audio::listening) {
            out["ok"]    = false;
            out["error"] = "listening";
        } else {
            M5.Speaker.tone(in["hz"] | 880, in["ms"] | 100);
        }
    } else if (cmd == "play") {
        // {"pcm": base64 int16 LE mono @ 16 kHz, <= 4096 samples}. Replies once queued.
        const char* pcm = in["pcm"] | "";
        if (const char* err = audio::playChunk(pcm, strlen(pcm))) {
            out["ok"]    = false;
            out["error"] = err;
        }
    } else if (cmd == "play_stop") {
        M5.Speaker.stop(audio::kPlayChannel);
    } else if (cmd == "listen") {
        if (in["on"] | false) {
            if (!audio::startListening("host")) {
                out["ok"]    = false;
                out["error"] = "mic failed";
            }
        } else {
            audio::stopListening("host");
        }
        out["listening"] = audio::listening;
    } else {
        out["ok"]    = false;
        out["error"] = "unknown cmd";
    }
    sendJson(out);
}

static char rxLine[16384];  // a 4096-sample play chunk is ~11 KB of base64
static size_t rxLen       = 0;
static bool rxOverflow    = false;
static bool hostSeen      = false;  // a host has talked to us since boot

static void pollSerial()
{
    while (Serial.available()) {
        char ch = Serial.read();
        if (ch == '\r') continue;
        if (ch != '\n') {
            if (rxLen < sizeof(rxLine) - 1) rxLine[rxLen++] = ch;
            else rxOverflow = true;
            continue;
        }
        if (rxLen && !rxOverflow) {
            rxLine[rxLen] = 0;
            hostSeen      = true;
            JsonDocument in;
            if (deserializeJson(in, rxLine, rxLen)) {
                JsonDocument out;
                out["ok"]    = false;
                out["error"] = "bad json";
                sendJson(out);
            } else {
                handle(in);
            }
        } else if (rxOverflow) {
            JsonDocument out;
            out["ok"]    = false;
            out["error"] = "line too long";
            sendJson(out);
        }
        rxLen      = 0;
        rxOverflow = false;
    }
}

static void onDoubleTap()
{
    if (audio::listening) {
        audio::stopListening("touch");
    } else if (hostSeen) {
        audio::startListening("touch");
    } else {
        // Nobody to hear us: just react.
        face::expr  = "surprised";
        face::dirty = true;
    }
}

// ----------------------------------------------------------------------- main

void setup()
{
    Serial.setRxBufferSize(16384);
    Serial.setTxBufferSize(16384);
    Serial.begin(115200);
    Serial.setTxTimeoutMs(0);  // never block when no host is reading

    auto cfg = M5.config();
    M5.begin(cfg);
    M5.Speaker.setVolume(96);

    face::begin();
    face::render();

    ioe::begin();
    ioe::setServoPower(true);
    servo::begin();
    touch::begin();
    touch::onDoubleTap = onDoubleTap;
    audio::begin();

    JsonDocument ready;
    ready["event"]   = "ready";
    ready["fw"]      = kFirmware;
    ready["version"] = kVersion;
    ready["ioe"]     = ioe::ok;
    ready["touch"]   = touch::ok;
    sendJson(ready);
}

void loop()
{
    M5.update();
    pollSerial();
    servo::monitor();
    touch::tick();
    audio::tick();
    face::tick();
    delay(audio::listening ? 1 : 5);
}
