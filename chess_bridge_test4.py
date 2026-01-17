import time
import requests
import chess
import serial  # NEW

API_URL = "https://chess-api.com/v1"

# --- SERIAL CONFIG (edit these) ---
SERIAL_PORT = "/dev/cu.usbserial-10"   # macOS example. Could be "COM5" on Windows, "/dev/ttyACM0" on Linux.
BAUD_RATE = 115200

# Open serial connection once
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
time.sleep(2)  # let Arduino reset after serial connect
ser.reset_input_buffer()

board = chess.Board()

print("Chess API test with python-chess")
print("Enter moves in UCI format (e.g. e2e4)\n")

while not board.is_game_over():
    # ---- USER MOVE ----
    print(board)
    print("FEN:", board.fen())

    user_move = input("Your move: ").strip()

    try:
        move = chess.Move.from_uci(user_move)
    except ValueError:
        print("Invalid UCI format")
        continue

    if move not in board.legal_moves:
        print("Illegal move")
        continue

    board.push(move)

    if board.is_game_over():
        break

    # ---- AI MOVE ----
    payload = {"fen": board.fen()}
    r = requests.post(API_URL, json=payload, timeout=15)
    data = r.json()

    if data.get("type") == "error":
        print("API error:", data)
        break

    ai_move_uci = data.get("move")
    ai_move = chess.Move.from_uci(ai_move_uci)

    print("AI Move:", ai_move_uci)

    # ---- SEND TO ARDUINO ----
    # Pick a simple, parseable protocol. Example: "MOVE:e7e5\n"
    msg = f"MOVE:{ai_move_uci}\n"
    ser.write(msg.encode("utf-8"))

    # (Optional) wait for Arduino acknowledgement
    # ack = ser.readline().decode(errors="ignore").strip()
    # if ack:
    #     print("Arduino:", ack)

    board.push(ai_move)

print("\nGame over:", board.result())
ser.close()
