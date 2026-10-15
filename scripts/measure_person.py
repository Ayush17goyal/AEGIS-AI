import cv2
import glob
import numpy as np

files = sorted(glob.glob("orig_*.png"))
for f in files:
    img = cv2.imread(f)
    if img is None:
        continue
    b, g, r = img[:, :, 0], img[:, :, 1], img[:, :, 2]
    person_mask = (r > 30) | (g > 30) | (b > 30)
    person_mask[670:, :] = 0  # ignore floor reflections
    ys, xs = np.where(person_mask)
    if len(ys) == 0:
        continue
    top_y = int(np.min(ys))
    head_mask = person_mask[top_y : top_y + 120, :]
    h_ys, h_xs = np.where(head_mask)
    head_cx = float(np.median(h_xs))

    # Skin color detection in YCrCb
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    skin = (
        (ycrcb[:, :, 1] >= 133)
        & (ycrcb[:, :, 1] <= 173)
        & (ycrcb[:, :, 2] >= 77)
        & (ycrcb[:, :, 2] <= 127)
    )
    # restrict to upper area
    skin_head = skin[top_y : top_y + 180, :]
    s_ys, s_xs = np.where(skin_head)
    if len(s_ys) > 0:
        face_top = top_y + int(np.min(s_ys))
        face_bottom = top_y + int(np.max(s_ys))
        face_h = face_bottom - top_y
        face_cx = float(np.median(s_xs))
    else:
        face_top = top_y
        face_bottom = top_y + 90
        face_h = 90
        face_cx = head_cx

    print(
        f"{f}: top_y={top_y}, face_bottom={face_bottom}, face_h={face_h}, head_cx={head_cx:.1f}, face_cx={face_cx:.1f}"
    )
