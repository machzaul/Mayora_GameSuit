from flask import Flask, render_template, jsonify, session, redirect, url_for, request
import cv2
import mediapipe as mp
import serial
import serial.tools.list_ports
import numpy as np
import time
from collections import deque
import os
import sys
import re
from threading import Thread, Lock
import webbrowser

if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(base_path, 'templates'),
    static_folder=os.path.join(base_path, 'static')
)
app.secret_key = 'your-secret-key-here-change-this'  # Ganti dengan secret key yang aman

# ================= PENCARI COM =================
KNOWN_VID_PID = {
    ("10C4", "EA60"),  # CP210x
    ("1A86", "7523"),  # CH340
    ("1A86", "55D4"),  # CH9102
    ("303A", "1001"),  # Espressif USB JTAG/Serial
    ("303A", "0002"),  # Espressif USB Serial
    ("0403", "6001"),  # FTDI
}

PORT_KEYWORDS = (
    "arduino",
    "ch340",
    "usb serial",
    "cp210",
    "silicon labs",
    "uart",
    "esp32",
    "usb-serial",
)


def extract_vid_pid(hwid):
    if not hwid:
        return None
    match = re.search(r"VID:PID=([0-9A-F]{4}):([0-9A-F]{4})", hwid, re.I)
    if match:
        return (match.group(1).upper(), match.group(2).upper())
    match = re.search(r"VID_([0-9A-F]{4}).*PID_([0-9A-F]{4})", hwid, re.I)
    if match:
        return (match.group(1).upper(), match.group(2).upper())
    return None


def list_ports_debug(ports):
    for port in ports:
        desc = port.description or ""
        hwid = port.hwid or ""
        print(f"- {port.device} | {desc} | {hwid}")


def get_candidate_ports():
    ports = list(serial.tools.list_ports.comports())

    env_port = os.environ.get("ARDUINO_PORT") or os.environ.get("SERIAL_PORT")
    if env_port:
        for port in ports:
            if port.device.lower() == env_port.lower():
                return [port.device]
        # Jika env diset tapi tidak terdeteksi, tetap coba pakai nilai env
        return [env_port]

    scored = []
    for port in ports:
        desc = (port.description or "").lower()
        hwid = port.hwid or ""
        score = 0

        if any(keyword in desc for keyword in PORT_KEYWORDS):
            score += 2

        vid_pid = extract_vid_pid(hwid)
        if vid_pid in KNOWN_VID_PID:
            score += 3

        if "bluetooth" in desc:
            score -= 3

        if score > 0:
            scored.append((score, port.device))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [device for _, device in scored]


def find_arduino_port():
    candidates = get_candidate_ports()
    if candidates:
        return candidates[0]
    return None


# ================= ARDUINO SERVO =================
arduino = None

def init_serial():
    global arduino

    if arduino is not None and arduino.is_open:
        return

    candidates = get_candidate_ports()
    if not candidates:
        print("Arduino tidak ditemukan! Port tersedia:")
        list_ports_debug(serial.tools.list_ports.comports())
        return

    last_error = None
    for port in candidates:
        try:
            arduino = serial.Serial(port, 115200, timeout=1)
            time.sleep(2)
            print(f"Arduino ditemukan di {port}")
            return
        except Exception as e:
            last_error = e
            print(f"Gagal membuka serial {port}: {e}")
            try:
                if arduino is not None:
                    arduino.close()
            except Exception:
                pass
            arduino = None

    print("Gagal membuka semua port kandidat.")
    if last_error is not None:
        print("Error terakhir:", last_error)


# ================= MEDIA PIPE =================
mp_hands = mp.solutions.hands

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

# ================= CAMERA MANAGER =================
camera = None
camera_thread = None
camera_lock = Lock()
frame_lock = Lock()
latest_jpeg = None
camera_running = False
camera_clients = 0
camera_clients_lock = Lock()


def _open_camera():
    backend = cv2.CAP_DSHOW if os.name == 'nt' and hasattr(cv2, 'CAP_DSHOW') else cv2.CAP_ANY
    cap = cv2.VideoCapture(0, backend)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 480)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
    cap.set(cv2.CAP_PROP_FPS, 24)
    # Kurangi buffer agar latency lebih rendah (jika didukung driver)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def _camera_loop():
    global camera, latest_jpeg
    target_fps = 24
    frame_interval = 1.0 / target_fps

    while True:
        with camera_lock:
            if not camera_running:
                break

        with camera_clients_lock:
            active = camera_clients > 0

        if not active:
            if camera is not None:
                camera.release()
                camera = None
            time.sleep(0.1)
            continue

        if camera is None or not camera.isOpened():
            camera = _open_camera()
            if camera is None or not camera.isOpened():
                time.sleep(0.2)
                continue

        success, frame = camera.read()
        if not success:
            time.sleep(0.05)
            continue

        frame = cv2.flip(frame, 1)

        if hand_tracking_active:
            frame = process_hand_frame(frame)

        ret, buffer = cv2.imencode('.jpg', frame)
        if ret:
            with frame_lock:
                latest_jpeg = buffer.tobytes()

        time.sleep(frame_interval)

    if camera is not None:
        camera.release()
        camera = None


def _ensure_camera_thread():
    global camera_thread, camera_running
    with camera_lock:
        if camera_running:
            return
        camera_running = True
        camera_thread = Thread(target=_camera_loop, daemon=True)
        camera_thread.start()


def _register_camera_client():
    global camera_clients
    with camera_clients_lock:
        camera_clients += 1
    _ensure_camera_thread()


def _unregister_camera_client():
    global camera_clients
    with camera_clients_lock:
        camera_clients = max(0, camera_clients - 1)


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
    elif fingers_up in [2, 3] and index_tip.y < index_pip.y and middle_tip.y < middle_pip.y:
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

    else:
        detection_buffer.append(False)
        gesture_buffer.clear()
        hand_gesture = "none"

    # Tangan dianggap terdeteksi jika mayoritas frame terakhir mendeteksi tangan
    hand_detected = sum(detection_buffer) >= len(detection_buffer) // 2

    return frame

# ================= VIDEO STREAM =================
def generate_frames():
    _register_camera_client()
    try:
        while True:
            with frame_lock:
                frame = latest_jpeg
            if frame is None:
                time.sleep(0.05)
                continue

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(1.0 / 24)
    finally:
        _unregister_camera_client()


# ================= ROUTES =================
@app.route('/')
def index():
    return render_template('shell.html')


def render_screen(template_name, **context):
    if request.args.get('embed') == '1':
        return render_template(template_name, **context)
    return redirect(url_for('index', screen=request.path))


@app.route('/screen/index')
def screen_index():
    # Reset game state
    session['current_round'] = 1
    session['wins'] = 0
    session['losses'] = 0
    return render_screen('index.html')


@app.route('/round')
def round_page():
    """Round page with transition effect"""
    current_round = session.get('current_round', 1)
    return render_screen('round.html', round=current_round)


@app.route('/game')
def game():
    current_round = session.get('current_round', 1)
    wins = session.get('wins', 0)
    losses = session.get('losses', 0)
    
    # Reset gesture buffers saat masuk game
    global gesture_buffer, detection_buffer
    gesture_buffer.clear()
    detection_buffer.clear()
    
    return render_screen('game.html', round=current_round, wins=wins)


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
        
        if wins >= 2:
            return jsonify({
                "status": "game_over",
                "message": "SELAMAT! Anda menang 3 kali!",
                "final_result": "win"
            })
    
    elif result == 'KALAH':
        losses += 1
        session['losses'] = losses
        
        if losses >= 2:
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
    return render_screen('loading.html')

@app.route('/win')
def win():
    """win page"""
    return render_screen('win.html')

@app.route('/lose')
def lose():
    """win page"""
    return render_screen('lose.html')

@app.route('/api/servo/collect', methods=['POST'])
def servo_collect():
    if arduino is None or not arduino.is_open:
        init_serial()
    if arduino is None or not arduino.is_open:
        return jsonify({"status": "arduino_not_found"})

    arduino.write(b'O\n')
    arduino.flush()
    print("Command O dikirim ke ESP32")

    return jsonify({"status": "ok"})




@app.route('/audio-player')
def audio_player():
    """Audio player iframe - loads once and never reloads"""
    return render_template('audio_player.html')

if __name__ == '__main__':
    # Hindari double-open COM saat debug reloader aktif
    enable_debug = True
    if not enable_debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        init_serial()
        def _open_browser():
            time.sleep(1)
            try:
                webbrowser.open_new("http://127.0.0.1:5000/")
            except Exception as e:
                print("Gagal membuka browser:", e)
        Thread(target=_open_browser, daemon=True).start()
    app.run(debug=enable_debug, use_reloader=enable_debug)
