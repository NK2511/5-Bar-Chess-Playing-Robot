import cv2
import numpy as np
import time
import chess
import chess.engine # This is for Stockfish
import random
import serial # This is for serial communication


STOCKFISH_PATH = r"C:\Users\nandh\Downloads\stockfish-windows-x86-64-avx2\stockfish\stockfish-windows-x86-64-avx2.exe"
SERIAL_PORT    = 'COM8'
BAUD_RATE      = 9600


board = chess.Board()
engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) # Stockfish engine initialization
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) # Serial port initialization
difficulty = int(input("Enter difficulty (1–100): ").strip())

url = "http://192.168.250.111:8080/video"
cap = cv2.VideoCapture(url)

BOARD_PX = 480
corners = []


board_with_pieces = np.zeros((8, 8), dtype=int)

def mouse_callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN and len(corners) < 4:
        corners.append((x, y))
        print(f"Clicked corner {len(corners)}: ({x}, {y})")

def print_board(board):
    board_str = str(board)
    rows = board_str.split('\n')
    print("\n  a b c d e f g h")
    for i, row in enumerate(rows):
        print(f"{8 - i} {row}")
    print()

def play_move(user_move: str, difficulty: int) -> str:
    global board, engine, ser # Engine and serial port are global here

    user_move = user_move.lower()

    if len(user_move) != 4:
        print("Invalid move ")
        return ""

    # Validate if the move is legal on the current board
    try:
        move_obj = chess.Move.from_uci(user_move)
        if move_obj not in board.legal_moves:
            print("Illegal move:", user_move)
            return ""
    except ValueError:
        print(f"Invalid UCI move string: {user_move}")
        return ""


    board.push_uci(user_move)
    print("\nYou moved:", user_move.upper())
    if board.is_check():
        print("You gave check!")

    print_board(board)

    if board.is_game_over():
        print("Game Over! Final Result:", board.result())
        engine.quit() # Quitting Stockfish engine
        ser.close() # Closing serial port
        return ""



    if difficulty <= 10:
        bot_move = random.choice(list(board.legal_moves))
    else:
        limit = chess.engine.Limit(depth=max(1, difficulty // 10))
        bot_move = engine.play(board, limit).move

    board.push(bot_move)
    bot_uci = bot_move.uci()

    print("Bot moved:", bot_uci.upper())
    if board.is_check():
        print("Bot gives you check!")

    print_board(board)

    ser.write((bot_uci + '\n').encode()) # Sending bot move via serial

    if board.is_game_over():
        print("Game Over! Final Result:", board.result())
        engine.quit() # Quitting Stockfish engine
        ser.close() # Closing serial port

    return bot_uci

cv2.namedWindow("Pick Corners")
cv2.setMouseCallback("Pick Corners", mouse_callback)

print("Please click the 4 corners in order: A8 (bottom-left), A1 (bottom-right), H1 (top-right), H8 (top-left)")

while len(corners) < 4:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    display_frame = cv2.resize(frame, (720, 480))

    for idx, (x, y) in enumerate(corners, start=1):
        cv2.circle(display_frame, (x, y), 5, (0, 0, 255), -1)
        cv2.putText(display_frame, str(idx), (x + 5, y - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    cv2.imshow("Pick Corners", display_frame)

    if cv2.waitKey(1) == 27:
        cap.release()
        cv2.destroyAllWindows()
        exit()

print("Corners have been selected")



pts_src = np.array([
    corners[3],  # H8 
    corners[2],  # H1 
    corners[1],  # A1 
    corners[0]   # A8 
], dtype=np.float32)

pts_dst = np.array([
    [0, 0],          # Top-left of destination image
    [BOARD_PX, 0],   # Top-right of destination image
    [BOARD_PX, BOARD_PX], # Bottom-right of destination image
    [0, BOARD_PX]    # Bottom-left of destination image
], dtype=np.float32)

M = cv2.getPerspectiveTransform(pts_src, pts_dst)

def detect_piece_color(square):
    hsv_square = cv2.cvtColor(square, cv2.COLOR_BGR2HSV)
    black_lower = np.array([0, 0, 0])
    black_upper = np.array([180, 255, 60]) 
    white_lower = np.array([0, 0, 180]) 
    white_upper = np.array([180, 50, 255]) 
    black_mask = cv2.inRange(hsv_square, black_lower, black_upper)
    white_mask = cv2.inRange(hsv_square, white_lower, white_upper)
    black_ratio = np.sum(black_mask > 0) / (square.shape[0] * square.shape[1])
    white_ratio = np.sum(white_mask > 0) / (square.shape[0] * square.shape[1])
    if black_ratio > 0.10: 
        return 'brown'
    elif white_ratio > 0.15: 
        return 'white'
    else:
        return 'empty'

prev_board_state = [['empty'] * 8 for _ in range(8)]
last_stable_time = time.time()
stable_duration = 10
last_stable_board_state = [['empty'] * 8 for _ in range(8)]
consecutive_stable_frames = 0

last_reported_move = None

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    display_frame = cv2.resize(frame, (720, 480))
    warped = cv2.warpPerspective(display_frame, M, (BOARD_PX, BOARD_PX))
    CELL = BOARD_PX // 8

    for r in range(9):
        y = r * CELL
        cv2.line(warped, (0, y), (BOARD_PX, y), (255, 255, 255), 1)
    for c in range(9):
        x = c * CELL
        cv2.line(warped, (x, 0), (x, BOARD_PX), (255, 255, 255), 1)

    curr_board_state = [['empty'] * 8 for _ in range(8)]

    for row in range(8):
        for col in range(8):
            x1 = col * CELL
            y1 = row * CELL
            x2 = (col + 1) * CELL
            y2 = (row + 1) * CELL
            square = warped[y1:y2, x1:x2]
            piece_color = detect_piece_color(square)
            curr_board_state[row][col] = piece_color
            if piece_color == 'white':
                cv2.rectangle(warped, (x1, y1), (x2, y2), (210, 180, 140), -1)
            elif piece_color == 'brown':
                cv2.rectangle(warped, (x1, y1), (x2, y2), (139, 69, 19), -1)
            else:
                cv2.rectangle(warped, (x1, y1), (x2, y2), (255, 255, 255), 1)

            letter = chr(ord('a') + col)
            number = 8 - row
            coord = f"{letter}{number}"
            cv2.putText(warped, coord, (x1 + 5, y1 + CELL - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1) # Adjusted font size/position

    cv2.imshow("Chessboard View", warped)

    if cv2.waitKey(1) == 27:
        break

    move_from = None
    move_to = None
    black_pieces_stable = True

    for r in range(8):
        for c in range(8):
            if prev_board_state[r][c] == 'brown' and curr_board_state[r][c] != 'brown':
                black_pieces_stable = False
                break
            if prev_board_state[r][c] != 'brown' and curr_board_state[r][c] == 'brown':
                black_pieces_stable = False
                break
        if not black_pieces_stable:
            break

    if black_pieces_stable:
        consecutive_stable_frames += 1
        if consecutive_stable_frames >= stable_duration:
            diff_from = []
            diff_to = []

            for r in range(8):
                for c in range(8):
                    if last_stable_board_state[r][c] == 'brown' and curr_board_state[r][c] != 'brown':
                        diff_from.append((r, c))
                    elif last_stable_board_state[r][c] != 'brown' and curr_board_state[r][c] == 'brown':
                        diff_to.append((r, c))

            if len(diff_from) == 1 and len(diff_to) == 1:
                move_from_coords = diff_from[0]
                move_to_coords = diff_to[0]

                from_sq = f"{chr(ord('a') + move_from_coords[1])}{8 - move_from_coords[0]}"
                to_sq = f"{chr(ord('a') + move_to_coords[1])}{8 - move_to_coords[0]}"
                current_move_uci = from_sq + to_sq

                if current_move_uci != last_reported_move:
                    print(f"Detected User Move: {current_move_uci.upper()}")
                    play_move(current_move_uci, difficulty)
                    last_reported_move = current_move_uci
                    last_stable_board_state = [row.copy() for row in curr_board_state]
            elif len(diff_from) == 0 and len(diff_to) == 0:
                last_stable_board_state = [row.copy() for row in curr_board_state]
            else:
                pass

    else:
        consecutive_stable_frames = 0
        last_stable_time = time.time()
        last_reported_move = None
        last_stable_board_state = [row.copy() for row in curr_board_state]


    prev_board_state = [row.copy() for row in curr_board_state]

cap.release()
cv2.destroyAllWindows()