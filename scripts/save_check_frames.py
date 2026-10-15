import cv2
import os

source_full = os.path.expanduser(r"~\Downloads\Use_the_provided_reference_ima.mp4")
cap = cv2.VideoCapture(source_full)

for sec in [1, 3, 5, 8]:
    cap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000)
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(f"check_frame_{sec}s.png", frame)

cap.release()
print("Saved check frames")
