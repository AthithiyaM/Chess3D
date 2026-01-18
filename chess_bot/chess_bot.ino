#include <Servo.h>
#include <Stepper.h>

const int stepsPerRev = 2048;

Stepper z(stepsPerRev, 2, 7, 4, 12);

Servo x;
Servo y;

// --------- MOTOR STATE ----------
struct MotorState
{
  float posDeg;
};

MotorState mx, my, mz;

void moveMotorDegrees(Servo &motor, float startDeg, float endDeg, int speedDelayMs)
{
  Serial.print("Start Degree: ");
  Serial.print(startDeg);
  Serial.print(" End Degree: ");
  Serial.println(endDeg);
  int step = (endDeg >= startDeg) ? 1 : -1;

  for (int pos = (int)startDeg; pos != (int)endDeg; pos += step)
  {
    motor.write(pos);
    delay(speedDelayMs);
  }

  // Ensure exact final position
  motor.write(endDeg);
  Serial.println("DONE");
}

void resetMotorsToA1()
{
  float targetX = 11.25f;
  float targetY = 11.25f;
  float targetZ = 0.0f;

  applyMotorTarget('X', targetX);
  applyMotorTarget('Y', targetY);
  applyMotorTarget('Z', targetZ);

  mx.posDeg = targetX;
  my.posDeg = targetY;
  mz.posDeg = targetZ;
}

void applyMotorTarget(char axis, float targetDeg)
{
  // TODO: replace with actual motor control (servo.write, stepper steps, etc.)
  Serial.print("MOTOR ");
  Serial.print(axis);
  Serial.print(" -> ");
  Serial.print(targetDeg, 2);
  Serial.println(" deg");
  if (axis == 'X')
    moveMotorDegrees(x, mx.posDeg, targetDeg, 30);
  else if (axis == 'Y')
    moveMotorDegrees(y, my.posDeg, targetDeg, 30);
  else if (axis == 'Z')
  {
    if (targetDeg == 0.0)
      z.step(-512);
    if (targetDeg == 90.00)
      z.step(512);
  }
}

// --------- PARSING HELPERS ----------
bool parseRotCommand(const String &line, char &axisOut, float &deltaDegOut)
{
  // Accept: "ROT_X +11.25" (also works without sign, e.g. "ROT_Y 22.5")
  if (!line.startsWith("ROT_"))
    return false;
  if (line.length() < 6)
    return false; // "ROT_X " minimum

  char axis = line.charAt(4); // X/Y/Z in "ROT_X"
  if (!(axis == 'X' || axis == 'Y' || axis == 'Z'))
    return false;

  // Expect a space after axis, but be tolerant
  // Degrees start at index 5 or 6 depending on underscore formatting; here it's "ROT_X "
  int spaceIdx = line.indexOf(' ');
  if (spaceIdx < 0)
    return false;

  String numStr = line.substring(spaceIdx + 1);
  numStr.trim();
  if (numStr.length() == 0)
    return false;

  float delta = numStr.toFloat(); // handles "+11.25", "-33.75"
  axisOut = axis;
  deltaDegOut = delta;
  return true;
}

void handleRot(char axis, float deltaDeg)
{
  MotorState *m = nullptr;
  if (axis == 'X')
    m = &mx;
  else if (axis == 'Y')
    m = &my;
  else if (axis == 'Z')
    m = &mz;
  else
    return;

  float newTarget = m->posDeg + deltaDeg;

  applyMotorTarget(axis, newTarget);

  m->posDeg = newTarget;
}

void setup()
{
  Serial.begin(115200);
  while (!Serial)
  {
  }

  x.attach(9);
  y.attach(10);
  z.setSpeed(10);

  resetMotorsToA1();

  Serial.println("READY");
}

void loop()
{
  if (Serial.available())
  {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() == 0)
      return;

    // For now just echo so you can see it
    Serial.print("RX: ");
    Serial.println(line);

    char axis;
    float deltaDeg;

    if (parseRotCommand(line, axis, deltaDeg))
    {
      handleRot(axis, deltaDeg);
      return;
    }
  }
}
