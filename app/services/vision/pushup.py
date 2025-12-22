import cv2
import numpy as np
import math
from ultralytics import YOLO
from app.config.settings import setting

class PushupMonitor:
    def __init__(self, model_path=None):
        path = model_path or setting.MODEL_PATH
        self.model = YOLO(path)
        
        # Pushup counter state
        self.pushup_count = 0
        self.current_state = "UNKNOWN"
        
        # Keypoint indices - left and right arms (COCO/YOLO pose)
        self.LEFT_SHOULDER = 5
        self.RIGHT_SHOULDER = 6
        self.LEFT_ELBOW = 7
        self.RIGHT_ELBOW = 8
        self.LEFT_WRIST = 9
        self.RIGHT_WRIST = 10
        
        # Thresholds with hysteresis
        self.ELBOW_DOWN_ANGLE = 100   # Down position (more bent)
        self.ELBOW_UP_ANGLE = 150     # Up position (more straight)
    
    def process_frame(self, frame):
        """Process frame with tracking"""
        results = self.model.track(frame, persist=True)
        return results

    def calculate_angle(self, p1, p2, p3):
        """Calculate angle between three points (p1-p2-p3)"""
        vector1 = np.array([p1[0] - p2[0], p1[1] - p2[1]])
        vector2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
        
        dot_product = np.dot(vector1, vector2)
        magnitude1 = np.linalg.norm(vector1)
        magnitude2 = np.linalg.norm(vector2)
        
        if magnitude1 * magnitude2 == 0:
            return 0
        
        cos_angle = np.clip(dot_product / (magnitude1 * magnitude2), -1.0, 1.0)
        angle = math.acos(cos_angle)
        return math.degrees(angle)

    def draw_rounded_rectangle(self, img, pt1, pt2, color, radius=15, filled=False):
        """Draw rounded rectangle for modern UI"""
        x1, y1 = pt1
        x2, y2 = pt2
        
        cv2.rectangle(img, (x1 + radius, y1), (x2 - radius, y2), color, -1 if filled else 1)
        cv2.rectangle(img, (x1, y1 + radius), (x2, y2 - radius), color, -1 if filled else 1)
        
        thickness = -1 if filled else 1
        cv2.circle(img, (x1 + radius, y1 + radius), radius, color, thickness)
        cv2.circle(img, (x2 - radius, y1 + radius), radius, color, thickness)
        cv2.circle(img, (x1 + radius, y2 - radius), radius, color, thickness)
        cv2.circle(img, (x2 - radius, y2 - radius), radius, color, thickness)
        
        return img

    def draw_modern_overlay(self, frame, count, state):
        """Draw modern minimal UI overlay (no angle text)"""
        h, w = frame.shape[:2]
        
        # Count box (top-left)
        overlay = frame.copy()
        self.draw_rounded_rectangle(overlay, (20, 20), (200, 120), (40, 40, 40), filled=True, radius=15)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
        
        cv2.putText(frame, str(count), (40, 85), 
                   cv2.FONT_HERSHEY_DUPLEX, 2.0, (255, 255, 255), 3, cv2.LINE_AA)
        cv2.putText(frame, "PUSHUPS", (40, 105), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)
        
        # State box (top-right)
        state_colors = {
            "DOWN": (66, 135, 245),
            "UP": (67, 245, 66),
            "UNKNOWN": (150, 150, 150)
        }
        state_color = state_colors.get(state, (150, 150, 150))
        
        overlay2 = frame.copy()
        state_box_x1 = w - 220
        self.draw_rounded_rectangle(overlay2, (state_box_x1, 20), (w - 20, 80), (40, 40, 40), 
                                    filled=True, radius=12)
        cv2.addWeighted(overlay2, 0.85, frame, 0.15, 0, frame)
        
        cv2.putText(frame, state, (state_box_x1 + 20, 55), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, state_color, 2, cv2.LINE_AA)
        
        return frame

    def draw_skeleton(self, frame, keypoints, confidence, used_side):
        """Draw minimal skeleton for whichever arm is used ('left' or 'right')"""
        if used_side == "right":
            shoulder = self.RIGHT_SHOULDER
            elbow = self.RIGHT_ELBOW
            wrist = self.RIGHT_WRIST
        elif used_side == "left":
            shoulder = self.LEFT_SHOULDER
            elbow = self.LEFT_ELBOW
            wrist = self.LEFT_WRIST
        else:
            return frame  # nothing to draw
        
        connections = [(shoulder, elbow), (elbow, wrist)]
        
        # Draw lines
        for start_idx, end_idx in connections:
            if confidence[start_idx] > 0.5 and confidence[end_idx] > 0.5:
                start_point = tuple(keypoints[start_idx].astype(int))
                end_point = tuple(keypoints[end_idx].astype(int))
                
                color = {
                    "DOWN": (66, 135, 245),
                    "UP": (67, 245, 66)
                }.get(self.current_state, (150, 150, 150))
                
                cv2.line(frame, start_point, end_point, color, 4, cv2.LINE_AA)
        
        # Draw keypoints
        point_colors = {
            shoulder: (67, 245, 66),
            elbow: (255, 165, 0),
            wrist: (245, 66, 245)
        }
        
        for idx in [shoulder, elbow, wrist]:
            if confidence[idx] > 0.5:
                point = tuple(keypoints[idx].astype(int))
                cv2.circle(frame, point, 10, (255, 255, 255), -1, cv2.LINE_AA)
                cv2.circle(frame, point, 6, point_colors[idx], -1, cv2.LINE_AA)
        
        return frame

    def _best_arm_and_angle(self, keypoints, confidence):
        """Choose left or right arm based on how many of the 3 keypoints are visible."""
        # Right arm indices
        right_indices = [self.RIGHT_SHOULDER, self.RIGHT_ELBOW, self.RIGHT_WRIST]
        left_indices = [self.LEFT_SHOULDER, self.LEFT_ELBOW, self.LEFT_WRIST]
        
        right_valid = [i for i in right_indices if confidence[i] > 0.5]
        left_valid = [i for i in left_indices if confidence[i] > 0.5]
        
        # Decide which arm to use
        used_side = None
        angle = 0.0
        
        if len(right_valid) == 3 and len(left_valid) < 3:
            used_side = "right"
        elif len(left_valid) == 3 and len(right_valid) < 3:
            used_side = "left"
        elif len(left_valid) == 3 and len(right_valid) == 3:
            # If both fully visible, you can choose one or average; choose right for simplicity
            used_side = "right"
        else:
            # If neither arm has all 3 keypoints confidently visible, return no angle
            return None, None
        
        if used_side == "right":
            angle = self.calculate_angle(
                keypoints[self.RIGHT_SHOULDER],
                keypoints[self.RIGHT_ELBOW],
                keypoints[self.RIGHT_WRIST]
            )
        else:  # left
            angle = self.calculate_angle(
                keypoints[self.LEFT_SHOULDER],
                keypoints[self.LEFT_ELBOW],
                keypoints[self.LEFT_WRIST]
            )
        
        return angle, used_side

    def pushup_counter(self, results):
        """Detect pushup using whichever arm (left/right) is more visible."""
        try:
            if not hasattr(results[0], 'keypoints') or results[0].keypoints is None:
                return "UNKNOWN", 0, None
            
            if len(results[0].keypoints) == 0:
                return "UNKNOWN", 0, None
            
            keypoints = results[0].keypoints.xy[0].cpu().numpy()
            confidence = results[0].keypoints.conf[0].cpu().numpy()
            
            elbow_angle, used_side = self._best_arm_and_angle(keypoints, confidence)
            if used_side is None:
                # No reliable arm this frame
                return "UNKNOWN", 0, None
            
            # Determine state - ONLY 3 states: UP, DOWN, UNKNOWN
            if elbow_angle < self.ELBOW_DOWN_ANGLE:
                new_state = "DOWN"
            elif elbow_angle > self.ELBOW_UP_ANGLE:
                new_state = "UP"
            else:
                new_state = self.current_state if self.current_state != "UNKNOWN" else "UNKNOWN"
            
            # Count pushup on DOWN -> UP
            if self.current_state == "DOWN" and new_state == "UP":
                self.pushup_count += 1
                print(f"✓ Pushup #{self.pushup_count} | Angle: {int(elbow_angle)}° | Side: {used_side}")
            
            self.current_state = new_state
            
            return new_state, elbow_angle, used_side
            
        except Exception as e:
            print(f"Error: {e}")
            return "UNKNOWN", 0, None

    def visualize(self, results):
        """Main visualization method"""
        try:
            if not hasattr(results[0], 'orig_img'):
                return None
            
            frame = results[0].orig_img.copy()
            state, elbow_angle, used_side = self.pushup_counter(results)
            
            # Draw skeleton for whichever arm was used
            if used_side is not None and hasattr(results[0], 'keypoints') and len(results[0].keypoints) > 0:
                keypoints = results[0].keypoints.xy[0].cpu().numpy()
                confidence = results[0].keypoints.conf[0].cpu().numpy()
                frame = self.draw_skeleton(frame, keypoints, confidence, used_side)
            
            # Draw overlay (count + state)
            frame = self.draw_modern_overlay(frame, self.pushup_count, state)
            
            return frame
            
        except Exception as e:
            print(f"Error in visualization: {e}")
            return results[0].orig_img if hasattr(results[0], 'orig_img') else None

    def get_current_stats(self):
        """Return current statistics as dict"""
        return {
            "count": self.pushup_count,
            "state": self.current_state,
            "exercise": "pushups"
        }

    def reset_counter(self):
        """Reset the rep counter"""
        self.pushup_count = 0
        self.current_state = "UNKNOWN"


if __name__ == "__main__":
    monitor = PushupMonitor()
    cap = cv2.VideoCapture('/Users/ananthakrishnab/Desktop/Screen Recording 2025-12-22 at 10.13.03.mov')
    
    while True:
        success, frame = cap.read()
        if not success:
            break
        
        results = monitor.process_frame(frame)
        annotated_frame = monitor.visualize(results)
        
        if annotated_frame is not None:
            cv2.imshow("Pushup Counter", annotated_frame)
        
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    
    print(f"\n{'='*50}")
    print(f"Final Count: {monitor.pushup_count} Pushups")
    print(f"{'='*50}\n")
    
    cap.release()
    cv2.destroyAllWindows()
