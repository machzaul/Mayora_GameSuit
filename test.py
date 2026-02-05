#!/usr/bin/env python3
"""
Hand Gesture Detection Test Script
Gunakan script ini untuk menguji dan mengkalibrasi deteksi gesture
sebelum bermain game Fortune Hands.
"""

import cv2
import mediapipe as mp
from collections import Counter, deque
import time

# ================= SETUP MEDIAPIPE =================
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

# Buffer untuk stabilisasi
gesture_buffer = deque(maxlen=5)

# Statistik
stats = {
    'rock': 0,
    'paper': 0,
    'scissors': 0,
    'unknown': 0,
    'total_frames': 0
}


# ================= GESTURE DETECTION =================
def detect_rps(hand_landmarks):
    """Deteksi gesture Rock, Paper, Scissors"""
    
    # Tips dan joints untuk setiap jari
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
    
    # Deteksi gesture
    if fingers_up == 0:
        return "rock"
    elif fingers_up == 2 and index_tip.y < index_pip.y and middle_tip.y < middle_pip.y:
        return "scissors"
    elif fingers_up >= 4:
        return "paper"
    else:
        return "unknown"


# ================= MAIN TESTING LOOP =================
def main():
    print("=" * 60)
    print("HAND GESTURE DETECTION TEST")
    print("=" * 60)
    print("\nInstruksi:")
    print("1. Pastikan tangan Anda terlihat jelas di kamera")
    print("2. Coba gesture: Rock (✊), Paper (✋), Scissors (✌️)")
    print("3. Lihat accuracy di layar")
    print("4. Tekan 'q' untuk keluar")
    print("5. Tekan 'r' untuk reset statistik")
    print("=" * 60)
    print()
    
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    start_time = time.time()
    last_gesture = None
    gesture_start_time = None
    
    while True:
        success, frame = cap.read()
        if not success:
            print("Error: Tidak dapat membaca frame dari kamera")
            break
        
        # Flip horizontal agar seperti cermin
        frame = cv2.flip(frame, 1)
        
        # Convert ke RGB
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)
        
        current_gesture = "none"
        stats['total_frames'] += 1
        
        # Jika tangan terdeteksi
        if results.multi_hand_landmarks:
            landmarks = results.multi_hand_landmarks[0]
            
            # Deteksi gesture
            detected_gesture = detect_rps(landmarks)
            gesture_buffer.append(detected_gesture)
            
            # Stabilisasi dengan voting
            if len(gesture_buffer) >= 3:
                gesture_counts = Counter(gesture_buffer)
                current_gesture = gesture_counts.most_common(1)[0][0]
                
                # Update stats
                if current_gesture != 'unknown':
                    stats[current_gesture] += 1
                else:
                    stats['unknown'] += 1
            
            # Draw landmarks
            mp_drawing.draw_landmarks(
                frame,
                landmarks,
                mp_hands.HAND_CONNECTIONS,
                mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2)
            )
            
            # Track gesture duration
            if current_gesture != last_gesture:
                last_gesture = current_gesture
                gesture_start_time = time.time()
            
            gesture_duration = time.time() - gesture_start_time if gesture_start_time else 0
        else:
            gesture_buffer.clear()
            last_gesture = None
            gesture_start_time = None
        
        # ================= DISPLAY INFO =================
        
        # Background untuk text
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (630, 200), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        
        # Gesture info
        gesture_text = f"Gesture: {current_gesture.upper()}"
        color = (0, 255, 0) if current_gesture in ['rock', 'paper', 'scissors'] else (0, 165, 255)
        cv2.putText(frame, gesture_text, (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)
        
        # Duration
        if gesture_start_time:
            cv2.putText(frame, f"Duration: {gesture_duration:.1f}s", (20, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Stats
        total_gestures = stats['rock'] + stats['paper'] + stats['scissors']
        if total_gestures > 0:
            accuracy = (total_gestures / (total_gestures + stats['unknown'])) * 100
        else:
            accuracy = 0
        
        cv2.putText(frame, f"Accuracy: {accuracy:.1f}%", (20, 130),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        # Gesture counts
        cv2.putText(frame, f"Rock: {stats['rock']} | Paper: {stats['paper']} | Scissors: {stats['scissors']}", 
                    (20, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Tips
        cv2.putText(frame, "Press 'q' to quit | 'r' to reset", (20, 190),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        # Gesture emoji indicators
        emoji_y = 250
        cv2.putText(frame, "Rock: ✊", (20, emoji_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 255), 2)
        cv2.putText(frame, "Paper: ✋", (20, emoji_y + 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 255, 100), 2)
        cv2.putText(frame, "Scissors: ✌️", (20, emoji_y + 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 100, 100), 2)
        
        # Show frame
        cv2.imshow('Hand Gesture Test - Fortune Hands', frame)
        
        # Key handling
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            # Reset stats
            stats = {k: 0 for k in stats}
            gesture_buffer.clear()
            print("\n✓ Statistik di-reset")
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    
    # Print final stats
    print("\n" + "=" * 60)
    print("HASIL TESTING")
    print("=" * 60)
    print(f"Total Frames: {stats['total_frames']}")
    print(f"Rock detections: {stats['rock']}")
    print(f"Paper detections: {stats['paper']}")
    print(f"Scissors detections: {stats['scissors']}")
    print(f"Unknown detections: {stats['unknown']}")
    
    total_gestures = stats['rock'] + stats['paper'] + stats['scissors']
    if total_gestures > 0:
        accuracy = (total_gestures / (total_gestures + stats['unknown'])) * 100
        print(f"\nAccuracy Rate: {accuracy:.2f}%")
        
        if accuracy >= 95:
            print("✓ EXCELLENT! Deteksi sangat baik")
        elif accuracy >= 85:
            print("✓ GOOD! Deteksi baik")
        elif accuracy >= 70:
            print("⚠ OK - Pertimbangkan untuk adjust parameter")
        else:
            print("✗ POOR - Perlu perbaikan setup atau parameter")
    
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTesting dihentikan oleh user")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()