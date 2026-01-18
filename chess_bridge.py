import time
import requests
import chess
import serial
from collections import deque
from threading import Event, Thread
from flask import Flask, jsonify, request

BOARD_DEGREES = 180.0
SQUARES_PER_BOARD = 8
DEG_PER_SQUARE = BOARD_DEGREES / SQUARES_PER_BOARD      # 22.5
DEG_PER_UNIT = DEG_PER_SQUARE / 2                        # 11.25

API_URL = "https://chess-api.com/v1"

# --- MOVE SERVER CONFIG ---
MOVE_SERVER_HOST = "127.0.0.1"
MOVE_SERVER_PORT = 5001

# --- SERIAL CONFIG (edit these) ---
SERIAL_PORT = "/dev/cu.usbmodem1101"
BAUD_RATE = 115200

# Where to drop captured pieces. Set to an unused board square or
# implement off-board routing if your hardware supports it.
CAPTURE_DROP_SQ = "a1"

# Simple HTTP move queue so a web UI can submit moves.
move_queue = deque()
move_event = Event()
busy_event = Event()
move_app = Flask(__name__)


@move_app.post("/move")
def submit_move():
    data = request.get_json(silent=True) or {}
    move = (data.get("move") or "").strip()
    if not move:
        return jsonify({"ok": False, "error": "missing move"}), 400
    move_queue.append(move)
    move_event.set()
    return jsonify({"ok": True})

@move_app.get("/status")
def status():
    return jsonify({"busy": busy_event.is_set()})

@move_app.get("/board")
def board_state():
    return jsonify({"board": str(board), "fen": board.fen()})


def run_move_server():
    move_app.run(
        host=MOVE_SERVER_HOST,
        port=MOVE_SERVER_PORT,
        debug=False,
        use_reloader=False,
    )


def wait_for_move() -> str:
    while True:
        move_event.wait()
        if move_queue:
            move = move_queue.popleft()
            if not move_queue:
                move_event.clear()
            return move
        move_event.clear()

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

def interior_corner_from_center(sq: str, cx: int, cy: int) -> tuple[int, int]:
    file = ord(sq[0]) - ord('a')          # 0..7
    rank = int(sq[1]) - 1                 # 0..7  (0=rank1, 7=rank8)

    # Horizontal: avoid outer edges
    if file == 0:       # a-file: don't go left (x-1 would hit 0)
        sx = +1
    elif file == 7:     # h-file: don't go right (x+1 would hit 16)
        sx = -1
    else:
        sx = +1         # default preference (right)

    # Vertical: avoid outer edges
    if rank == 0:       # rank 1: don't go down (y-1 would hit 0)
        sy = +1         # go up (upper edge)
    elif rank == 7:     # rank 8: don't go up (y+1 would hit 16)
        sy = -1         # go down (lower edge)
    else:
        sy = -1         # default preference (down)

    return (cx + sx, cy + sy)

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

    fcx, fcy = interior_corner_from_center(from_sq, fx, fy)
    tcx, tcy = interior_corner_from_center(to_sq, tx, ty)

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

def capture_square_for_move(board: chess.Board, move: chess.Move) -> str | None:
    if not board.is_capture(move):
        return None
    if board.is_en_passant(move):
        direction = -8 if board.turn == chess.WHITE else 8
        cap_sq = move.to_square + direction
        return chess.square_name(cap_sq)
    return chess.square_name(move.to_square)

print("Chess API test with python-chess")
print("Enter moves in UCI format (e.g. e2e4)\n")
server_thread = Thread(target=run_move_server, daemon=True)
server_thread.start()
print(f"Move server listening on http://{MOVE_SERVER_HOST}:{MOVE_SERVER_PORT}/move")

while not board.is_game_over():
    # ---- USER MOVE ----
    print(board)
    print("FEN:", board.fen())

    print("Waiting for move from HTTP...")
    user_move = wait_for_move().strip()

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
    cap_sq = capture_square_for_move(board, ai_move)

    commands = []
    if prev_ai_to is not None:
        commands += plan_leg(prev_ai_to, from_sq)  # magnet travels to pick up square

    if cap_sq is not None:
        # Remove captured piece first.
        commands += plan_leg(from_sq, cap_sq)      # travel to captured piece (magnet up)
        commands += ["ROT_Z +90.00"]               # raise magnet
        commands += plan_leg(cap_sq, CAPTURE_DROP_SQ)  # carry off to drop zone
        commands += ["ROT_Z -90.00"]               # lower magnet
        commands += plan_leg(CAPTURE_DROP_SQ, from_sq)  # return to mover (magnet up)

    commands += ["ROT_Z +90.00"]              # raise magnet
    commands += plan_leg(from_sq, to_sq)          # magnet carries piece to destination
    commands += ["ROT_Z -90.00"]              # lower magnet

    busy_event.set()
    for line in commands:
        ser.write((line + "\n").encode("utf-8"))
        time.sleep(1)
    busy_event.clear()

    prev_ai_to = to_sq  # remember for next move

    # ---- SEND TO ARDUINO ----
    msg = f"MOVE:{ai_move_uci}\n"
    ser.write(msg.encode("utf-8"))

    board.push(ai_move)

print("\nGame over:", board.result())
ser.close()
