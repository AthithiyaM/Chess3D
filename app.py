import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

MOVE_SERVER_URL = "http://127.0.0.1:5001/move"
MOVE_SERVER_STATUS_URL = "http://127.0.0.1:5001/status"
MOVE_SERVER_BOARD_URL = "http://127.0.0.1:5001/board"
last_move = ""
last_status = ""


@app.get("/")
def index():
    return render_template(
        "index.html",
        last_move=last_move,
        last_status=last_status,
    )


@app.post("/move")
def move():
    global last_move, last_status
    last_move = request.form.get("move", "").strip()
    if not last_move:
        last_status = "Missing move."
        return render_template(
            "index.html",
            last_move=last_move,
            last_status=last_status,
        )
    try:
        r = requests.post(MOVE_SERVER_URL, json={"move": last_move}, timeout=5)
        if r.ok:
            last_status = "Sent."
        else:
            last_status = f"Error: {r.status_code}"
    except requests.RequestException as exc:
        last_status = f"Error: {exc}"
    return render_template(
        "index.html",
        last_move=last_move,
        last_status=last_status,
    )

@app.get("/status")
def status():
    try:
        r = requests.get(MOVE_SERVER_STATUS_URL, timeout=2)
        if r.ok:
            data = r.json()
            return jsonify({"busy": bool(data.get("busy"))})
    except requests.RequestException:
        pass
    return jsonify({"busy": False})

@app.get("/board")
def board():
    try:
        r = requests.get(MOVE_SERVER_BOARD_URL, timeout=2)
        if r.ok:
            data = r.json()
            return jsonify(
                {
                    "board": data.get("board", ""),
                    "fen": data.get("fen", ""),
                }
            )
    except requests.RequestException:
        pass
    return jsonify({"board": "", "fen": ""})


if __name__ == "__main__":
    # app.run(debug=True)
    app.run(host="127.0.0.1", port=8000, debug=True)
