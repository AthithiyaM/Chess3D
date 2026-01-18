import time
import requests
import chess
import serial  # NEW

BOARD_DEGREES = 180.0
SQUARES_PER_BOARD = 8
DEG_PER_SQUARE = BOARD_DEGREES / SQUARES_PER_BOARD      # 22.5
DEG_PER_UNIT = DEG_PER_SQUARE / 2                        # 11.25

API_URL = "https://chess-api.com/v1"

# --- SERIAL CONFIG (edit these) ---
SERIAL_PORT = "/dev/cu.usbserial-10"
BAUD_RATE = 115200

# Open serial connection once
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
time.sleep(2)  # let Arduino reset after serial connect
ser.reset_input_buffer()

board = chess.Board()
prev_ai_to = "a1"

# ROUTE PLANNING METHODS

def sq_to_center_units(sq: str) -> tuple[int, int]:
    # half-square units: center is (2*file+1, 2*rank+1)
    file = ord(sq[0]) - ord('a')          # 0..7
    rank = int(sq[1]) - 1                 # 0..7
    return (2*file + 1, 2*rank + 1)

def bottom_right_corner_from_center(cx: int, cy: int) -> tuple[int, int]:
    return (cx + 1, cy - 1)

def emit_delta_cmds(ax: int, ay: int, bx: int, by: int) -> list[str]:
    cmds = []
    dx_units = bx - ax
    dy_units = by - ay

    if dy_units != 0:
        deg = dy_units * DEG_PER_UNIT
        cmds.append(f"ROT_Y {deg:+.2f}")

    if dx_units != 0:
        deg = dx_units * DEG_PER_UNIT
        cmds.append(f"ROT_X {deg:+.2f}")

    return cmds

def plan_leg(from_sq: str, to_sq: str) -> list[str]:
    fx, fy = sq_to_center_units(from_sq)
    tx, ty = sq_to_center_units(to_sq)

    fcx, fcy = bottom_right_corner_from_center(fx, fy)
    tcx, tcy = bottom_right_corner_from_center(tx, ty)

    cmds = []
    cmds.append(f"LEG {from_sq}->{to_sq}")

    # center -> corner
    cmds += emit_delta_cmds(fx, fy, fcx, fcy)

    # corner -> corner (border travel)
    cmds += emit_delta_cmds(fcx, fcy, tcx, tcy)

    # corner -> center
    cmds += emit_delta_cmds(tcx, tcy, tx, ty)

    cmds.append("ENDLEG")
    return cmds

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

    # ---- PLAN ROUTE FOR ARDUINO ----
    from_sq = ai_move_uci[0:2]
    to_sq   = ai_move_uci[2:4]

    commands = []
    if prev_ai_to is not None:
        commands += plan_leg(prev_ai_to, from_sq)  # magnet travels to pick up square

    commands += ["ROT_Z +90.00"]              # lower magnet
    commands += plan_leg(from_sq, to_sq)          # magnet carries piece to destination
    commands += ["ROT_Z -90.00"]              # raise magnet

    for line in commands:
        ser.write((line + "\n").encode("utf-8"))

    prev_ai_to = to_sq  # remember for next move

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