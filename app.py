from flask import Flask, render_template, jsonify, session, redirect, url_for
import cv2
import mediapipe as mp
import numpy as np
import time
from collections import deque

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-this'  # Ganti dengan secret key yang aman

# ================= MEDIA PIPE =================
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

# ================= GLOBAL STATE =================
hand_tracking_active = False
hand_detected = False
hand_position = {"x": 0, "y": 0}
hand_gesture = "none"

# Buffer untuk stabilisasi deteksi gesture
gesture_buffer = deque(maxlen=5)  # Simpan 5 frame terakhir
detection_buffer = deque(maxlen=3)  # Simpan 3 frame untuk deteksi keberadaan tangan


# ================= RPS DETECTION (IMPROVED) =================
def detect_rps(hand_landmarks):
    """Deteksi gesture Rock, Paper, Scissors dengan lebih akurat"""
    
    # Tips dan joints untuk setiap jari
    thumb_tip = hand_landmarks.landmark[4]
    thumb_ip = hand_landmarks.landmark[3]
    
    index_tip = hand_landmarks.landmark[8]
    index_pip = hand_landmarks.landmark[6]
    index_mcp = hand_landmarks.landmark[5]
    
    middle_tip = hand_landmarks.landmark[12]
    middle_pip = hand_landmarks.landmark[10]
    middle_mcp = hand_landmarks.landmark[9]
    
    ring_tip = hand_landmarks.landmark[16]
    ring_pip = hand_landmarks.landmark[14]
    ring_mcp = hand_landmarks.landmark[13]
    
    pinky_tip = hand_landmarks.landmark[20]
    pinky_pip = hand_landmarks.landmark[18]
    pinky_mcp = hand_landmarks.landmark[17]
    
    wrist = hand_landmarks.landmark[0]
    
    # Hitung jari yang terangkat
    fingers_up = 0
    
    # Index finger
    if index_tip.y < index_pip.y < index_mcp.y:
        fingers_up += 1
    
    # Middle finger
    if middle_tip.y < middle_pip.y < middle_mcp.y:
        fingers_up += 1
    
    # Ring finger
    if ring_tip.y < ring_pip.y < ring_mcp.y:
        fingers_up += 1
    
    # Pinky finger
    if pinky_tip.y < pinky_pip.y < pinky_mcp.y:
        fingers_up += 1
    
    # Deteksi gesture berdasarkan jumlah jari yang terangkat
    if fingers_up == 0:
        return "rock"
    elif fingers_up == 2 and index_tip.y < index_pip.y and middle_tip.y < middle_pip.y:
        # Scissors: hanya telunjuk dan jari tengah terangkat
        return "scissors"
    elif fingers_up >= 4:
        return "paper"
    else:
        return "unknown"


# ================= PROCESS FRAME (IMPROVED) =================
def process_hand_frame(frame):
    global hand_detected, hand_position, hand_gesture

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    if results.multi_hand_landmarks:
        detection_buffer.append(True)
        landmarks = results.multi_hand_landmarks[0]

        h, w, _ = frame.shape
        wrist = landmarks.landmark[0]
        hand_position = {
            "x": int(wrist.x * w),
            "y": int(wrist.y * h)
        }

        # Deteksi gesture dan tambahkan ke buffer
        current_gesture = detect_rps(landmarks)
        gesture_buffer.append(current_gesture)
        
        # Gunakan gesture yang paling sering muncul dalam buffer (stabilisasi)
        if len(gesture_buffer) >= 3:
            from collections import Counter
            gesture_counts = Counter(gesture_buffer)
            hand_gesture = gesture_counts.most_common(1)[0][0]
        else:
            hand_gesture = current_gesture

        mp_drawing.draw_landmarks(
            frame,
            landmarks,
            mp_hands.HAND_CONNECTIONS
        )
    else:
        detection_buffer.append(False)
        gesture_buffer.clear()
        hand_gesture = "none"

    # Tangan dianggap terdeteksi jika mayoritas frame terakhir mendeteksi tangan
    hand_detected = sum(detection_buffer) >= len(detection_buffer) // 2

    return frame


# ================= VIDEO STREAM =================
def generate_frames():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 480)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
    cap.set(cv2.CAP_PROP_FPS, 24)

    while True:
        success, frame = cap.read()
        if not success:
            break

        frame = cv2.flip(frame, 1)

        if hand_tracking_active:
            frame = process_hand_frame(frame)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    cap.release()


# ================= ROUTES =================
@app.route('/')
def index():
    # Reset game state
    session['current_round'] = 1
    session['wins'] = 0
    session['losses'] = 0
    return render_template('index.html')


@app.route('/round')
def round_page():
    """Round page with transition effect"""
    current_round = session.get('current_round', 1)
    return render_template('round.html', round=current_round)


@app.route('/game')
def game():
    current_round = session.get('current_round', 1)
    wins = session.get('wins', 0)
    losses = session.get('losses', 0)
    
    # Reset gesture buffers saat masuk game
    global gesture_buffer, detection_buffer
    gesture_buffer.clear()
    detection_buffer.clear()
    
    return render_template('game.html', round=current_round, wins=wins)


@app.route('/video_feed')
def video_feed():
    return app.response_class(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/api/start-tracking', methods=['POST'])
def start_tracking():
    global hand_tracking_active
    hand_tracking_active = True
    return jsonify({"status": "started"})


@app.route('/api/hand-data')
def hand_data():
    return jsonify({
        "detected": hand_detected,
        "gesture": hand_gesture,
        "position": hand_position
    })


@app.route('/api/game-result', methods=['POST'])
def game_result():
    """Update game state after each round"""
    from flask import request
    
    data = request.get_json()
    result = data.get('result')
    
    current_round = session.get('current_round', 1)
    wins = session.get('wins', 0)
    losses = session.get('losses', 0)
    
    if result == 'MENANG':
        wins += 1
        session['wins'] = wins
        
        if wins >= 3:
            return jsonify({
                "status": "game_over",
                "message": "SELAMAT! Anda menang 3 kali!",
                "final_result": "win"
            })
    
    elif result == 'KALAH':
        losses += 1
        session['losses'] = losses
        
        if losses >= 3:
            return jsonify({
                "status": "game_over",
                "message": "GAME OVER! Anda kalah 3 kali!",
                "final_result": "lose"
            })
    
    # Jika belum selesai, lanjut ke round berikutnya
    if result != 'SERI':
        current_round += 1
        session['current_round'] = current_round
    
    return jsonify({
        "status": "continue",
        "current_round": current_round,
        "wins": wins,
        "losses": losses
    })


@app.route('/loading')
def loading():
    """Loading page"""
    return render_template('loading.html')

@app.route('/win')
def win():
    """win page"""
    return render_template('win.html')

@app.route('/lose')
def lose():
    """win page"""
    return render_template('lose.html')

if __name__ == '__main__':
    app.run(debug=True)