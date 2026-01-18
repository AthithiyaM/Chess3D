// --------- MOTOR STATE ----------
struct MotorState {
  float posDeg;
};

MotorState mx, my, mz;

void resetMotorsToA1() {
  mx.posDeg = -90+11.25;
  my.posDeg = -90+11.25;
  mz.posDeg = 0.0f;

  // Replace these with real motor commands later:
  applyMotorTarget('X', mx.posDeg);
  applyMotorTarget('Y', my.posDeg);
  applyMotorTarget('Z', mz.posDeg);
}

void applyMotorTarget(char axis, float targetDeg) {
  // TODO: replace with actual motor control (servo.write, stepper steps, etc.)
  Serial.print("MOTOR ");
  Serial.print(axis);
  Serial.print(" -> ");
  Serial.print(targetDeg, 2);
  Serial.println(" deg");
}

// --------- PARSING HELPERS ----------
bool parseRotCommand(const String& line, char &axisOut, float &deltaDegOut) {
  // Accept: "ROT_X +11.25" (also works without sign, e.g. "ROT_Y 22.5")
  if (!line.startsWith("ROT_")) return false;
  if (line.length() < 6) return false; // "ROT_X " minimum

  char axis = line.charAt(4); // X/Y/Z in "ROT_X"
  if (!(axis == 'X' || axis == 'Y' || axis == 'Z')) return false;

  // Expect a space after axis, but be tolerant
  // Degrees start at index 5 or 6 depending on underscore formatting; here it's "ROT_X "
  int spaceIdx = line.indexOf(' ');
  if (spaceIdx < 0) return false;

  String numStr = line.substring(spaceIdx + 1);
  numStr.trim();
  if (numStr.length() == 0) return false;

  float delta = numStr.toFloat(); // handles "+11.25", "-33.75"
  axisOut = axis;
  deltaDegOut = delta;
  return true;
}

void handleRot(char axis, float deltaDeg) {
  MotorState *m = nullptr;
  if (axis == 'X') m = &mx;
  else if (axis == 'Y') m = &my;
  else if (axis == 'Z') m = &mz;
  else return;

  float newTarget = m->posDeg + deltaDeg;
  m->posDeg = newTarget;

  applyMotorTarget(axis, newTarget);

  // // Optional: acknowledge back to Python
  // Serial.print("OK ROT_");
  // Serial.print(axis);
  // Serial.print(" ");
  // Serial.println(deltaDeg, 2);
}

void setup() {
  Serial.begin(115200);
  while (!Serial) {}

  resetMotorsToA1();

  Serial.println("READY");
}

void loop() {
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() == 0) return;

    // For now just echo so you can see it
    Serial.print("RX: ");
    Serial.println(line);

    char axis;
    float deltaDeg;

    if (parseRotCommand(line, axis, deltaDeg)) {
      handleRot(axis, deltaDeg);
      return;
    }

    // Later:
    // - parse "DX +2" / "DY -1"
    // - move motors accordingly
    // - send "DONE" after ENDLEG
  }
}

