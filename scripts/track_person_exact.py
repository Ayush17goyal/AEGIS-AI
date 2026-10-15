import cv2
import os
import numpy as np

source_full = os.path.expanduser(r"~\Downloads\Use_the_provided_reference_ima.mp4")
cap = cv2.VideoCapture(source_full)

width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = cap.get(cv2.CAP_PROP_FPS)

print(f"Tracking person in {source_full} ({width}x{height})")

frame_idx = 0
data = []
while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    # White shirt is bright in all 3 channels: r>140, g>140, b>140
    # And near the horizontal center of the frame (400 <= x <= 880)
    b, g, r = frame[:,:,0], frame[:,:,1], frame[:,:,2]
    shirt_mask = (r > 130) & (g > 130) & (b > 130)
    # Mask out background spotlight flare on far right (x > 900)
    shirt_mask[:, 880:] = False
    shirt_mask[:, :400] = False
    shirt_mask[550:, :] = False # below waist
    
    ys, xs = np.where(shirt_mask)
    if len(ys) > 50:
        shirt_top = int(np.min(ys))
        shirt_cx = float(np.median(xs))
        # Head is above shirt top: y from shirt_top - 140 to shirt_top
        head_top = max(0, shirt_top - 120)
        # Search head in x window around shirt_cx
        head_x_min = max(0, int(shirt_cx - 80))
        head_x_max = min(width, int(shirt_cx + 80))
        head_region = frame[head_top:shirt_top, head_x_min:head_x_max]
        # Skin/hair detection in this window
        h_gray = cv2.cvtColor(head_region, cv2.COLOR_BGR2GRAY)
        h_ys, h_xs = np.where(h_gray > 25)
        if len(h_ys) > 20:
            actual_head_top = head_top + int(np.min(h_ys))
            actual_head_cx = head_x_min + float(np.median(h_xs))
        else:
            actual_head_top = head_top
            actual_head_cx = shirt_cx
    else:
        shirt_top = 220
        shirt_cx = 640
        actual_head_top = 100
        actual_head_cx = 640

    data.append((frame_idx, actual_head_top, shirt_top, actual_head_cx, shirt_cx))
    frame_idx += 1

cap.release()

for i in [0, 24, 48, 72, 96, 120, 144, 168, 192, 216, len(data)-1]:
    if i < len(data):
        d = data[i]
        face_height = d[2] - d[1]
        print(f"Frame {d[0]:3d} ({d[0]/fps:.2f}s): head_top={d[1]}, shirt_top={d[2]}, face_h={face_height}, head_cx={d[3]:.1f}")
