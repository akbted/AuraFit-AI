# PushupMonitor Explained - A Learning Guide

## Overview

This code uses **AI pose estimation** to count pushups by detecting body keypoints and measuring arm angles. Here's how it works:

---

## 1. Imports & Setup

```python
import cv2          # OpenCV - for video/image processing
import numpy as np  # NumPy - for math operations on arrays
import math         # For trigonometry (angle calculations)
from ultralytics import YOLO  # YOLOv8 - the AI model for pose detection
```

---

## 2. The COCO Keypoint Format

YOLO Pose models detect **17 body keypoints** in this order:

```
0: Nose           5: Left Shoulder    10: Right Wrist
1: Left Eye       6: Right Shoulder   11: Left Hip
2: Right Eye      7: Left Elbow       12: Right Hip
3: Left Ear       8: Right Elbow      13: Left Knee
4: Right Ear      9: Left Wrist       14: Right Knee
                                      15: Left Ankle
                                      16: Right Ankle
```

For pushups, we only need **shoulders, elbows, and wrists** (indices 5-10):

```
Shoulder (5,6) -----> Elbow (7,8) -----> Wrist (9,10)
```

---

## 3. How Angle Calculation Works

```python
def calculate_angle(self, p1, p2, p3):
```

This calculates the angle at point `p2` (the elbow):

```
        p1 (Shoulder)
         \
          \  angle
           p2 (Elbow) <-- We measure the angle HERE
          /
         /
        p3 (Wrist)
```

### The Math:

```python
# Step 1: Create vectors from elbow to shoulder and elbow to wrist
vector1 = np.array([p1[0] - p2[0], p1[1] - p2[1]])  # Elbow → Shoulder
vector2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])  # Elbow → Wrist

# Step 2: Calculate magnitudes (lengths)
magnitude1 = np.linalg.norm(vector1)  # √(x² + y²)
magnitude2 = np.linalg.norm(vector2)

# Step 3: Dot product formula: A·B = |A||B|cos(θ)
dot_product = np.dot(vector1, vector2)
cos_angle = dot_product / (magnitude1 * magnitude2)

# Step 4: Get angle in degrees
angle = math.acos(cos_angle)  # Returns radians
return math.degrees(angle)    # Convert to degrees
```

**Visual Example:**

```
ARM EXTENDED (UP position):     ARM BENT (DOWN position):
Shoulder                        Shoulder
    \                              \
     \  ~160°                       \ ~90°
      Elbow -----> Wrist            Elbow
                                      \
                                       Wrist
```

---

## 4. State Machine for Counting

```python
# Thresholds
self.ELBOW_DOWN_ANGLE = 90   # Arm is bent (pushup DOWN)
self.ELBOW_UP_ANGLE = 160    # Arm is extended (pushup UP)
```

The counting logic:

```python
if angle < self.ELBOW_DOWN_ANGLE:      # Angle < 90° = bent arm
    if self.current_state == "UP":      # Was previously UP?
        self.pushup_count += 1          # ✓ Count a rep!
    self.current_state = "DOWN"
    
elif angle > self.ELBOW_UP_ANGLE:       # Angle > 160° = extended arm
    self.current_state = "UP"
```

**State Flow:**

```
START → UNKNOWN
         ↓
    [Arms Extended]
         ↓
        UP ←←←←←←←←←←←
         ↓            ↑
    [Arms Bent]       ↑
         ↓            ↑
       DOWN →→→→→→→→→→
         ↓
   [Arms Extended]
         ↓
   COUNT += 1, → UP
```

---

## 5. Keypoint Extraction

```python
def get_keypoint(self, keypoints, confidence, index):
    if confidence[index] < self.MIN_CONFIDENCE:  # 0.5 = 50%
        return None  # Ignore low-confidence detections
    return keypoints[index]  # Returns [x, y] coordinates
```

The model gives each keypoint a **confidence score** (0-1). We ignore anything below 50% to avoid errors.

---

## 6. Processing Pipeline

```python
def process_frame(self, frame):
    results = self.model.track(frame, persist=True, device=DEVICE, verbose=False)
    return results
```

| Parameter | Purpose |
|-----------|---------|
| `frame` | Video frame (image) to analyze |
| `persist=True` | Keep tracking the same person across frames |
| `device=DEVICE` | Use GPU (mps/cuda) or CPU |
| `verbose=False` | Don't print debug info |

---

## 7. Visualization

### Drawing Skeleton:
```python
connections = [
    (LEFT_SHOULDER, RIGHT_SHOULDER),  # Across shoulders
    (LEFT_SHOULDER, LEFT_ELBOW),      # Left upper arm
    (LEFT_ELBOW, LEFT_WRIST),         # Left forearm
    (RIGHT_SHOULDER, RIGHT_ELBOW),    # Right upper arm
    (RIGHT_ELBOW, RIGHT_WRIST),       # Right forearm
]
```

### Drawing UI Overlay:
```python
cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
# 85% overlay + 15% original = semi-transparent effect
```

---

## 8. Main Loop

```python
if __name__ == "__main__":
    monitor = PushupMonitor()       # Initialize
    cap = cv2.VideoCapture(0)       # Open webcam (0 = default camera)
    
    while True:
        success, frame = cap.read()         # Read frame from camera
        results = monitor.process_frame(frame)  # AI inference
        annotated = monitor.visualize(results)  # Draw on frame
        cv2.imshow("Pushup Counter", annotated) # Display
        
        if cv2.waitKey(1) & 0xFF == ord("q"):   # Press 'q' to quit
            break
```

---

## Summary Diagram

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│   Camera    │────▶│  YOLO Model  │────▶│   Keypoints   │
│   Frame     │     │  (Pose Est.) │     │  [x,y,conf]   │
└─────────────┘     └──────────────┘     └───────┬───────┘
                                                 │
                                                 ▼
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  Display    │◀────│  Visualize   │◀────│ Calculate     │
│  + Count    │     │  (Draw UI)   │     │ Arm Angle     │
└─────────────┘     └──────────────┘     └───────┬───────┘
                                                 │
                                                 ▼
                                         ┌───────────────┐
                                         │ State Machine │
                                         │ UP→DOWN=+1rep │
                                         └───────────────┘
```
