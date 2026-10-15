import cv2
import os
import numpy as np

# We can use person_framing_improved.mp4 or Use_the_provided_reference_ima.mp4
# Let's check both
source_full = os.path.expanduser(r"~\Downloads\Use_the_provided_reference_ima.mp4")
source_pfi = os.path.abspath("person_framing_improved.mp4")

print("Checking source_full:", os.path.exists(source_full))
print("Checking source_pfi:", os.path.exists(source_pfi))

cap = cv2.VideoCapture(source_full if os.path.exists(source_full) else source_pfi)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = cap.get(cv2.CAP_PROP_FPS)

print(f"Video: {width}x{height}, {fps} fps, {total_frames} frames")

frames_data = []
idx = 0
while True:
    ret, frame = cap.read()
    if not ret:
        break
    # detect person top (head) and x center
    # threshold brightness
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    person_mask = (gray > 20)
    # ignore floor reflection (bottom 10%)
    person_mask[int(height*0.85):, :] = 0
    ys, xs = np.where(person_mask)
    if len(ys) > 0:
        top_y = int(np.min(ys))
        # Head mask: top 120 pixels
        head_mask = person_mask[top_y:top_y+int(height*0.18), :]
        h_ys, h_xs = np.where(head_mask)
        if len(h_xs) > 0:
            cx = float(np.median(h_xs))
        else:
            cx = float(np.median(xs))
    else:
        top_y = 50
        cx = width / 2.0
    frames_data.append((idx, top_y, cx))
    idx += 1

cap.release()

print(f"Processed {len(frames_data)} frames")
for i in [0, 30, 60, 90, 120, 150, 180, 210, len(frames_data)-1]:
    if i < len(frames_data):
        print(f"Frame {i:3d} ({i/fps:.2f}s): top_y={frames_data[i][1]}, cx={frames_data[i][2]:.1f}")
