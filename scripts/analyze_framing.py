import cv2
import os
import numpy as np

video_path = os.path.expanduser(r"~\Downloads\Use_the_provided_reference_ima.mp4")
cap = cv2.VideoCapture(video_path)

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

frame_idx = 0
results = []
while True:
    ret, frame = cap.read()
    if not ret:
        break
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    if len(faces) > 0:
        # Sort by area descending
        faces = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)
        x, y, w, h = faces[0]
        results.append((frame_idx, x, y, w, h))
    else:
        results.append((frame_idx, None, None, None, None))
    frame_idx += 1

cap.release()

print(f"Total frames: {frame_idx}")
detected = [r for r in results if r[1] is not None]
print(f"Detected faces in {len(detected)}/{frame_idx} frames")
for i in range(0, len(results), 24):
    r = results[i]
    print(f"Frame {r[0]} ({r[0]/24:.1f}s): Face x={r[1]}, y={r[2]}, w={r[3]}, h={r[4]}")
