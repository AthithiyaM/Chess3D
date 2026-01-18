*McHacks 2026*

# Chess3D

Play chess against an AI on a real, motorized board. You enter a move in the browser, the AI replies, and the machine moves the pieces on the physical board using a magnet and motors.

## How it works
- The web UI posts your UCI move (e.g. `e2e4`) to a local HTTP endpoint.
- `chess_bridge.py` keeps the game state with python-chess, calls the chess-api.com service for AI moves, and converts moves into motor rotations.
- An Arduino receives simple serial commands (e.g. `ROT_X`, `ROT_Y`, `ROT_Z`) and moves the magnet to pick up and place pieces.

## Run
1. Start the bridge: `python chess_bridge.py`
2. Start the UI: `python app.py`
3. Open the local web server and play!

## Notes
- Update `SERIAL_PORT`, `BAUD_RATE` in `chess_bridge.py` to match your hardware.
- Note: Discarded pieces will be moved to `a1` by the machine, feel free to move these pieces off the board as the game progresses.
- Arduino firmware lives in `chess_bot/chess_bot.ino`.
