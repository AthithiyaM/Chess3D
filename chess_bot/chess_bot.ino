struct AiMove {
  String from;
  String to;
  bool valid = false;
};

AiMove lastAiMove;
lastAiMove.from = a0;
AiMove pendingAiMove;

void setup() {
  Serial.begin(115200);
  while (!Serial) {}
  Serial.println("READY");
}

void loop() {
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();

    if (line.startsWith("MOVE:")) {
      handleAiMove(line.substring(5));  // strip "MOVE:"
    }
  }
}

void handleAiMove(String uci) {
  if (uci.length() != 4) {
    Serial.println("ERR:bad_uci");
    return;
  }

  // Parse UCI
  pendingAiMove.from = uci.substring(0, 2);
  pendingAiMove.to   = uci.substring(2, 4);
  pendingAiMove.valid = true;

  Serial.print("OK:");
  Serial.println(uci);

  // If we already had a previous move, we can compute a path
  if (lastAiMove.valid) {
    printJourney(lastAiMove, pendingAiMove);
  }

  // Commit this move as the last move
  lastAiMove = pendingAiMove;
}

void printJourney(const AiMove& prev, const AiMove& curr) {
  Serial.print("PATH ");
  Serial.print(prev.to);
  Serial.print("->");
  Serial.print(curr.from);
  Serial.print("->");
  Serial.println(curr.to);
}
