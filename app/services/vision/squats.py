import cv2
import numpy as np
import math
from ultralytics import YOLO
from app.config.settings import setting
from app.config.device import DEVICE

class SquatMonitor:
    def __init__(self, model_path=None):
        path = model_path or setting.MODEL_PATH
        self.model = YOLO(path)
        self.model.to(DEVICE)
        
        # Squat counter state
        self.squat_count = 0
        self.current_state = "UNKNOWN"
        
        # Keypoint indices - legs (COCO format)
        self.LEFT_HIP = 11
        self.RIGHT_HIP = 12
        self.LEFT_KNEE = 13
        self.RIGHT_KNEE = 14
        self.LEFT_ANKLE = 15
        self.RIGHT_ANKLE = 16
        
        # Thresholds
        self.KNEE_DOWN_ANGLE = 100
        self.KNEE_UP_ANGLE = 160
        
        # Minimum confidence
        self.MIN_CONFIDENCE = 0.5
    
    def process_frame(self, frame):
        """Process frame with tracking"""
        results = self.model.track(frame, persist=True, device=DEVICE, verbose=False)
        return results

    def calculate_angle(self, p1, p2, p3):
        """Calculate angle between three points"""
        if p1 is None or p2 is None or p3 is None:
            return None
            
        vector1 = np.array([p1[0] - p2[0], p1[1] - p2[1]])
        vector2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
        
        magnitude1 = np.linalg.norm(vector1)
        magnitude2 = np.linalg.norm(vector2)
        
        if magnitude1 * magnitude2 == 0:
            return None
        
        dot_product = np.dot(vector1, vector2)
        cos_angle = np.clip(dot_product / (magnitude1 * magnitude2), -1.0, 1.0)
        angle = math.acos(cos_angle)
        return math.degrees(angle)

    def get_keypoint(self, keypoints, confidence, index):
        """Safely get a keypoint if confidence is sufficient"""
        if keypoints is None or confidence is None:
            return None
        if index >= len(keypoints) or index >= len(confidence):
            return None
        if confidence[index] < self.MIN_CONFIDENCE:
            return None
        return keypoints[index]

    def _best_leg_and_angle(self, keypoints, confidence):
        """Get the best leg angle"""
        left_hip = self.get_keypoint(keypoints, confidence, self.LEFT_HIP)
        left_knee = self.get_keypoint(keypoints, confidence, self.LEFT_KNEE)
        left_ankle = self.get_keypoint(keypoints, confidence, self.LEFT_ANKLE)
        
        right_hip = self.get_keypoint(keypoints, confidence, self.RIGHT_HIP)
        right_knee = self.get_keypoint(keypoints, confidence, self.RIGHT_KNEE)
        right_ankle = self.get_keypoint(keypoints, confidence, self.RIGHT_ANKLE)
        
        left_angle = None
        right_angle = None
        
        if left_hip is not None and left_knee is not None and left_ankle is not None:
            left_angle = self.calculate_angle(left_hip, left_knee, left_ankle)
        
        if right_hip is not None and right_knee is not None and right_ankle is not None:
            right_angle = self.calculate_angle(right_hip, right_knee, right_ankle)
        
        if left_angle is not None and right_angle is not None:
            return (left_angle + right_angle) / 2, "both"
        elif left_angle is not None:
            return left_angle, "left"
        elif right_angle is not None:
            return right_angle, "right"
        else:
            return None, None

    def squat_counter(self, results):
        """Count squats based on knee angle"""
        if not results or len(results) == 0:
            return self.squat_count, self.current_state
        
        result = results[0]
        
        if result.keypoints is None or len(result.keypoints) == 0:
            return self.squat_count, self.current_state
        
        try:
            keypoints = result.keypoints.xy[0].cpu().numpy()
            confidence = result.keypoints.conf[0].cpu().numpy()
        except (IndexError, AttributeError):
            return self.squat_count, self.current_state
        
        if len(keypoints) == 0:
            return self.squat_count, self.current_state
        
        angle, used_leg = self._best_leg_and_angle(keypoints, confidence)
        
        if angle is None:
            return self.squat_count, self.current_state
        
        if angle < self.KNEE_DOWN_ANGLE:
            if self.current_state == "UP":
                self.squat_count += 1
            self.current_state = "DOWN"
        elif angle > self.KNEE_UP_ANGLE:
            self.current_state = "UP"
        
        return self.squat_count, self.current_state

    def draw_rounded_rectangle(self, img, pt1, pt2, color, radius=15, filled=False):
        """Draw a rounded rectangle"""
        x1, y1 = pt1
        x2, y2 = pt2
        
        if filled:
            cv2.rectangle(img, (x1 + radius, y1), (x2 - radius, y2), color, -1)
            cv2.rectangle(img, (x1, y1 + radius), (x2, y2 - radius), color, -1)
            cv2.circle(img, (x1 + radius, y1 + radius), radius, color, -1)
            cv2.circle(img, (x2 - radius, y1 + radius), radius, color, -1)
            cv2.circle(img, (x1 + radius, y2 - radius), radius, color, -1)
            cv2.circle(img, (x2 - radius, y2 - radius), radius, color, -1)

    def draw_modern_overlay(self, frame, count, state):
        """Draw modern minimal UI overlay"""
        h, w = frame.shape[:2]
        
        state_colors = {
            "DOWN": (66, 135, 245),
            "UP": (67, 245, 66),
            "UNKNOWN": (150, 150, 150)
        }
        state_color = state_colors.get(state, (150, 150, 150))
        
        overlay = frame.copy()
        state_box_x1 = w - 220
        self.draw_rounded_rectangle(overlay, (state_box_x1, 20), (w - 20, 80), (40, 40, 40), 
                                    filled=True, radius=12)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
        
        cv2.putText(frame, f"State: {state}", (state_box_x1 + 15, 58), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, state_color, 2, cv2.LINE_AA)
        
        return frame

    def draw_skeleton(self, frame, keypoints, confidence):
        """Draw skeleton on frame"""
        if keypoints is None or len(keypoints) == 0:
            return frame
            
        connections = [
            (self.LEFT_HIP, self.RIGHT_HIP),
            (self.LEFT_HIP, self.LEFT_KNEE),
            (self.LEFT_KNEE, self.LEFT_ANKLE),
            (self.RIGHT_HIP, self.RIGHT_KNEE),
            (self.RIGHT_KNEE, self.RIGHT_ANKLE),
        ]
        
        for start_idx, end_idx in connections:
            start_pt = self.get_keypoint(keypoints, confidence, start_idx)
            end_pt = self.get_keypoint(keypoints, confidence, end_idx)
            
            if start_pt is not None and end_pt is not None:
                cv2.line(frame, 
                        (int(start_pt[0]), int(start_pt[1])),
                        (int(end_pt[0]), int(end_pt[1])),
                        (0, 255, 255), 2)
        
        for idx in [self.LEFT_HIP, self.RIGHT_HIP, 
                    self.LEFT_KNEE, self.RIGHT_KNEE,
                    self.LEFT_ANKLE, self.RIGHT_ANKLE]:
            pt = self.get_keypoint(keypoints, confidence, idx)
            if pt is not None:
                cv2.circle(frame, (int(pt[0]), int(pt[1])), 5, (0, 255, 0), -1)
        
        return frame

    def visualize(self, results):
        """Visualize results on frame"""
        if not results or len(results) == 0:
            return np.zeros((480, 640, 3), dtype=np.uint8)
        
        frame = results[0].orig_img.copy()
        
        count, state = self.squat_counter(results)
        
        if results[0].keypoints is not None and len(results[0].keypoints) > 0:
            try:
                keypoints = results[0].keypoints.xy[0].cpu().numpy()
                confidence = results[0].keypoints.conf[0].cpu().numpy()
                frame = self.draw_skeleton(frame, keypoints, confidence)
            except (IndexError, AttributeError):
                pass
        
        frame = self.draw_modern_overlay(frame, count, state)
        
        return frame

    def get_current_stats(self):
        return {"count": self.squat_count, "state": self.current_state}

    def reset_counter(self):
        self.squat_count = 0
        self.current_state = "UNKNOWN"



if __name__ == "__main__":
    monitor = SquatMonitor()
    cap = cv2.VideoCapture(0)
    
    while True:
        success, frame = cap.read()
        if not success:
            break
        
        results = monitor.process_frame(frame)
        annotated_frame = monitor.visualize(results)
        
        if annotated_frame is not None:
            cv2.imshow("Squat Counter", annotated_frame)
        
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    
    print(f"\n{'='*50}")
    print(f"Final Count: {monitor.squat_count} Squats")
    print(f"{'='*50}\n")
    
    cap.release()
    cv2.destroyAllWindows()
