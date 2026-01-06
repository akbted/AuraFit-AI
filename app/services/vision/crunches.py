import cv2
import numpy as np
import math
from collections import deque
from ultralytics import YOLO
from app.config.settings import setting
from app.config.device import DEVICE

class CrunchMonitor:
    def __init__(self, model_path=None):
        path = model_path or setting.MODEL_PATH
        self.model = YOLO(path)
        self.model.to(DEVICE)
        
        # Crunch counter state
        self.crunch_count = 0
        self.current_state = "UNKNOWN"
        
        # Keypoints (COCO format)
        self.LEFT_SHOULDER = 5
        self.RIGHT_SHOULDER = 6
        self.LEFT_HIP = 11
        self.RIGHT_HIP = 12
        self.LEFT_KNEE = 13
        self.RIGHT_KNEE = 14
        
        # Angle thresholds (hip angle: shoulder-hip-knee)
        self.DOWN_ANGLE = 120   # Lying flat (~180°)
        self.UP_ANGLE = 100     # Crunched up (~90-120°)
        
        # Smoothing buffer to reduce noise
        self.angle_buffer = deque(maxlen=5)
        
        # Prevent double counting
        self.last_count_frame = 0
        self.frame_count = 0
        self.min_frames_between_reps = 10  # At least 10 frames between counts
    
    def process_frame(self, frame):
        """Process frame with tracking"""
        results = self.model.track(frame, persist=True, device=DEVICE, verbose=False)
        return results

    def calculate_angle(self, p1, p2, p3):
        """Calculate angle at p2 (vertex) between p1-p2-p3"""
        vector1 = np.array([p1[0] - p2[0], p1[1] - p2[1]])
        vector2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
        
        dot_product = np.dot(vector1, vector2)
        magnitude1 = np.linalg.norm(vector1)
        magnitude2 = np.linalg.norm(vector2)
        
        if magnitude1 * magnitude2 == 0:
            return 180  # Default to flat
        
        cos_angle = np.clip(dot_product / (magnitude1 * magnitude2), -1.0, 1.0)
        angle = math.acos(cos_angle)
        return math.degrees(angle)

    def get_smoothed_angle(self, angle):
        """Apply smoothing to reduce noise"""
        self.angle_buffer.append(angle)
        return np.median(self.angle_buffer)  # Median is robust to outliers

    def _get_best_side(self, keypoints, confidence):
        """Choose left or right side based on keypoint visibility"""
        right_indices = [self.RIGHT_SHOULDER, self.RIGHT_HIP, self.RIGHT_KNEE]
        left_indices = [self.LEFT_SHOULDER, self.LEFT_HIP, self.LEFT_KNEE]
        
        right_valid = sum(1 for i in right_indices if confidence[i] > 0.5)
        left_valid = sum(1 for i in left_indices if confidence[i] > 0.5)
        
        if right_valid == 3:
            return "right", right_indices
        elif left_valid == 3:
            return "left", left_indices
        elif right_valid > left_valid:
            return "right", right_indices if right_valid == 3 else None
        elif left_valid > right_valid:
            return "left", left_indices if left_valid == 3 else None
        
        return None, None

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

    def draw_modern_overlay(self, frame, count, state, angle=None):
        """Draw modern minimal UI overlay"""
        h, w = frame.shape[:2]
        
        # Count box (top-left)
        overlay = frame.copy()
        self.draw_rounded_rectangle(overlay, (20, 20), (200, 120), (40, 40, 40), filled=True, radius=15)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
        
        cv2.putText(frame, str(count), (40, 85), 
                   cv2.FONT_HERSHEY_DUPLEX, 2.0, (255, 255, 255), 3, cv2.LINE_AA)
        cv2.putText(frame, "CRUNCHES", (40, 105), 
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
        
        # Display angle
        if angle is not None and angle > 0:
            cv2.putText(frame, f"{int(angle)}°", (state_box_x1 + 130, 55), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
        
        return frame

    def draw_skeleton(self, frame, keypoints, confidence, indices):
        """Draw skeleton: shoulder-hip-knee"""
        shoulder_idx, hip_idx, knee_idx = indices
        
        color = {
            "DOWN": (66, 135, 245),
            "UP": (67, 245, 66)
        }.get(self.current_state, (150, 150, 150))
        
        # Draw lines: shoulder -> hip -> knee
        connections = [(shoulder_idx, hip_idx), (hip_idx, knee_idx)]
        for start_idx, end_idx in connections:
            if confidence[start_idx] > 0.5 and confidence[end_idx] > 0.5:
                start_point = tuple(keypoints[start_idx].astype(int))
                end_point = tuple(keypoints[end_idx].astype(int))
                cv2.line(frame, start_point, end_point, color, 4, cv2.LINE_AA)
        
        # Draw keypoints
        point_colors = {
            shoulder_idx: (255, 165, 0),   # Orange
            hip_idx: (67, 245, 66),        # Green (vertex)
            knee_idx: (245, 66, 245)       # Purple
        }
        
        for idx in [shoulder_idx, hip_idx, knee_idx]:
            if confidence[idx] > 0.5:
                point = tuple(keypoints[idx].astype(int))
                cv2.circle(frame, point, 10, (255, 255, 255), -1, cv2.LINE_AA)
                cv2.circle(frame, point, 6, point_colors[idx], -1, cv2.LINE_AA)
        
        # Draw angle arc at hip
        if all(confidence[i] > 0.5 for i in [shoulder_idx, hip_idx, knee_idx]):
            hip_point = tuple(keypoints[hip_idx].astype(int))
            cv2.ellipse(frame, hip_point, (30, 30), 0, 0, 360, color, 2, cv2.LINE_AA)
        
        return frame

    def crunch_counter(self, results):
        """Detect crunch using hip angle (shoulder-hip-knee)"""
        self.frame_count += 1
        
        try:
            if not hasattr(results[0], 'keypoints') or results[0].keypoints is None:
                return "UNKNOWN", 0, None, None
            
            if len(results[0].keypoints) == 0:
                return "UNKNOWN", 0, None, None
            
            keypoints = results[0].keypoints.xy[0].cpu().numpy()
            confidence = results[0].keypoints.conf[0].cpu().numpy()
            
            # Get best visible side
            used_side, indices = self._get_best_side(keypoints, confidence)
            if indices is None:
                return "UNKNOWN", 0, None, None
            
            shoulder_idx, hip_idx, knee_idx = indices
            
            # Calculate hip angle (shoulder-hip-knee)
            shoulder = keypoints[shoulder_idx]
            hip = keypoints[hip_idx]
            knee = keypoints[knee_idx]
            
            raw_angle = self.calculate_angle(shoulder, hip, knee)
            smoothed_angle = self.get_smoothed_angle(raw_angle)
            
            # Determine state based on angle
            if smoothed_angle < self.UP_ANGLE:
                new_state = "UP"
            elif smoothed_angle > self.DOWN_ANGLE:
                new_state = "DOWN"
            else:
                # In transition zone - keep current state
                new_state = self.current_state if self.current_state != "UNKNOWN" else "UNKNOWN"
            
            # Count on DOWN -> UP transition (with debounce)
            frames_since_last = self.frame_count - self.last_count_frame
            if (self.current_state == "DOWN" and 
                new_state == "UP" and 
                frames_since_last >= self.min_frames_between_reps):
                
                self.crunch_count += 1
                self.last_count_frame = self.frame_count
                print(f"✓ Crunch #{self.crunch_count} | Angle: {smoothed_angle:.1f}° | Side: {used_side}")
            
            self.current_state = new_state
            
            return new_state, smoothed_angle, used_side, indices
            
        except Exception as e:
            print(f"Error: {e}")
            return "UNKNOWN", 0, None, None

    def visualize(self, results):
        """Main visualization method"""
        try:
            if not hasattr(results[0], 'orig_img'):
                return None
            
            frame = results[0].orig_img.copy()
            state, angle, used_side, indices = self.crunch_counter(results)
            
            # Draw skeleton
            if indices is not None and hasattr(results[0], 'keypoints') and len(results[0].keypoints) > 0:
                keypoints = results[0].keypoints.xy[0].cpu().numpy()
                confidence = results[0].keypoints.conf[0].cpu().numpy()
                frame = self.draw_skeleton(frame, keypoints, confidence, indices)
            
            # Draw overlay
            frame = self.draw_modern_overlay(frame, self.crunch_count, state, angle)
            
            return frame
            
        except Exception as e:
            print(f"Error in visualization: {e}")
            return results[0].orig_img if hasattr(results[0], 'orig_img') else None

    def get_current_stats(self):
        """Return current statistics as dict"""
        return {
            "count": self.crunch_count,
            "state": self.current_state,
            "exercise": "crunches"
        }

    def reset_counter(self):
        """Reset the rep counter"""
        self.crunch_count = 0
        self.current_state = "UNKNOWN"
        self.angle_buffer.clear()
        self.last_count_frame = 0
        self.frame_count = 0


if __name__ == "__main__":
    monitor = CrunchMonitor()
    # cap = cv2.VideoCapture(0)
    cap = cv2.VideoCapture('/Users/ananthakrishnab/Desktop/Screen Recording 2025-12-24 at 22.37.23.mov')
    
    while True:
        success, frame = cap.read()
        if not success:
            break
        
        results = monitor.process_frame(frame)
        annotated_frame = monitor.visualize(results)
        
        if annotated_frame is not None:
            cv2.imshow("Crunch Counter", annotated_frame)
        
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    
    print(f"\n{'='*50}")
    print(f"Final Count: {monitor.crunch_count} Crunches")
    print(f"{'='*50}\n")
    
    cap.release()
    cv2.destroyAllWindows()
