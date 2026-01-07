# SquatMonitor Explained - A Learning Guide

## Overview

This code uses **AI pose estimation** to count squats by detecting body keypoints and measuring knee angles. Here's how it works:

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

For squats, we only need **hips, knees, and ankles** (indices 11-16):

```
Hip (11,12) -----> Knee (13,14) -----> Ankle (15,16)
```

---

## 3. How Angle Calculation Works

```python
def calculate_angle(self, p1, p2, p3):
```

This calculates the angle at point `p2` (the knee):

```
        p1 (Hip)
         \
          \  angle
           p2 (Knee) <-- We measure the angle HERE
          /
         /
        p3 (Ankle)
```

### The Math:

```python
# Step 1: Create vectors from knee to hip and knee to ankle
vector1 = np.array([p1[0] - p2[0], p1[1] - p2[1]])  # Knee → Hip
vector2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])  # Knee → Ankle

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
LEG STRAIGHT (UP position):     LEG BENT (DOWN position):

        Hip                              Hip
         |                                \
         |  ~160°                          \ ~90°
         |                                  Knee
        Knee                                 \
         |                                    \
         |                                    Ankle
       Ankle
```

---

## 4. State Machine for Counting

```python
# Thresholds
self.KNEE_DOWN_ANGLE = 100   # Knee is bent (squat DOWN)
self.KNEE_UP_ANGLE = 160     # Knee is straight (squat UP)
```

The counting logic:

```python
if knee_angle < self.KNEE_DOWN_ANGLE:      # Angle < 100° = bent knee
    new_state = "DOWN"
    
elif knee_angle > self.KNEE_UP_ANGLE:       # Angle > 160° = straight leg
    new_state = "UP"

# Count on transition from DOWN → UP
if self.current_state == "DOWN" and new_state == "UP":
    self.squat_count += 1          # ✓ Count a rep!
```

**State Flow:**

```
START → UNKNOWN
         ↓
    [Standing Up]
         ↓
        UP ←←←←←←←←←←←
         ↓            ↑
    [Squatting]       ↑  COUNT += 1!
         ↓            ↑
       DOWN →→→→→→→→→→
         ↓
   [Standing Up]
         ↓
        UP
```

---

## 5. Leg Selection Logic

Unlike pushups where one arm is usually visible, squats may show:
- **Both legs** → Average the angles
- **Left leg only** → Use left angle
- **Right leg only** → Use right angle

```python
def _best_leg_and_angle(self, keypoints, confidence):
    # Check which keypoints are visible (confidence > 0.5)
    right_valid = [i for i in right_indices if confidence[i] > 0.5]
    left_valid = [i for i in left_indices if confidence[i] > 0.5]
    
    if len(right_valid) == 3 and len(left_valid) == 3:
        used_side = "both"  # Average both angles
    elif len(right_valid) == 3:
        used_side = "right"
    elif len(left_valid) == 3:
        used_side = "left"
    else:
        return None, None  # Can't calculate
```

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
# For each leg, draw:
connections = [
    (hip, knee),    # Upper leg (thigh)
    (knee, ankle)   # Lower leg (shin)
]
```

### Keypoint Colors:
```python
point_colors = {
    hip: (67, 245, 66),      # Green - Hip
    knee: (255, 165, 0),     # Orange - Knee (angle measured here)
    ankle: (245, 66, 245)    # Magenta - Ankle
}
```

### State-Based Line Colors:
```python
color = {
    "DOWN": (66, 135, 245),   # Blue - Squatting
    "UP": (67, 245, 66)       # Green - Standing
}.get(self.current_state, (150, 150, 150))
```

### Drawing UI Overlay:
```python
# Count box (top-left)
cv2.putText(frame, str(count), (40, 85), ...)  # Big number
cv2.putText(frame, "SQUATS", (40, 105), ...)   # Label

# State box (top-right)
cv2.putText(frame, state, (state_box_x1 + 20, 55), ...)
```

---

## 8. Main Loop

```python
if __name__ == "__main__":
    monitor = SquatMonitor()        # Initialize
    cap = cv2.VideoCapture(0)       # Open webcam (0 = default camera)
    
    while True:
        success, frame = cap.read()         # Read frame from camera
        results = monitor.process_frame(frame)  # AI inference
        annotated = monitor.visualize(results)  # Draw on frame
        cv2.imshow("Squat Counter", annotated)  # Display
        
        if cv2.waitKey(1) & 0xFF == ord("q"):   # Press 'q' to quit
            break
```

---

## 9. Key Differences from Pushups

| Aspect | Pushups | Squats |
|--------|---------|--------|
| **Body Part** | Arms | Legs |
| **Keypoints Used** | Shoulder → Elbow → Wrist | Hip → Knee → Ankle |
| **Indices** | 5-10 | 11-16 |
| **Angle Measured At** | Elbow | Knee |
| **DOWN Threshold** | < 100° | < 100° |
| **UP Threshold** | > 150° | > 160° |
| **Typical View** | Side view | Front or side view |
| **Both Sides** | Usually one arm | Often both legs |

---

## 10. Summary Diagram

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│   Camera    │────▶│  YOLO Model  │────▶│   Keypoints   │
│   Frame     │     │  (Pose Est.) │     │  [x,y,conf]   │
└─────────────┘     └──────────────┘     └───────┬───────┘
                                                 │
                                                 ▼
                                         ┌───────────────┐
                                         │ Select Best   │
                                         │ Leg(s)        │
                                         │ L / R / Both  │
                                         └───────┬───────┘
                                                 │
                                                 ▼
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  Display    │◀────│  Visualize   │◀────│ Calculate     │
│  + Count    │     │  (Draw UI)   │     │ Knee Angle    │
└─────────────┘     └──────────────┘     └───────┬───────┘
                                                 │
                                                 ▼
                                         ┌───────────────┐
                                         │ State Machine │
                                         │DOWN→UP = +1rep│
                                         └───────────────┘
```

---

## 11. Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| `NoneType` error | Keypoints not detected | Check `if angle is None` before comparing |
| Double counting | Noisy angle readings | Use hysteresis (gap between thresholds) |
| Wrong count | Camera angle | Position camera to see full leg bend |
| No detection | Low confidence | Ensure good lighting, full body visible |