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
        
        # Thresholds with hysteresis
        self.KNEE_DOWN_ANGLE = 100   # Down position (bent knees)
        self.KNEE_UP_ANGLE = 160     # Up position (straight legs)
        
        # Minimum confidence
        self.MIN_CONFIDENCE = 0.5
    
    def process_frame(self, frame):
        """Process frame with tracking"""
        results = self.model.track(frame, persist=True, device=DEVICE, verbose=False)
        return results

    def calculate_angle(self, p1, p2, p3):
        """Calculate angle between three points (p1-p2-p3)"""
        if p1 is None or p2 is None or p3 is None:
            return None
        
        try:
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
        except Exception:
            return None

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
        """Draw modern minimal UI overlay"""
        h, w = frame.shape[:2]
        
        # Count box (top-left)
        overlay = frame.copy()
        self.draw_rounded_rectangle(overlay, (20, 20), (200, 120), (40, 40, 40), filled=True, radius=15)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
        
        cv2.putText(frame, str(count), (40, 85), 
                   cv2.FONT_HERSHEY_DUPLEX, 2.0, (255, 255, 255), 3, cv2.LINE_AA)
        cv2.putText(frame, "SQUATS", (40, 105), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)
        
        # State box (top-right)
        state_colors = {
            "DOWN": (66, 135, 245),    # Blue
            "UP": (67, 245, 66),       # Green
            "UNKNOWN": (150, 150, 150) # Gray
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
        """Draw minimal skeleton for whichever leg is used"""
        if used_side == "right":
            hip = self.RIGHT_HIP
            knee = self.RIGHT_KNEE
            ankle = self.RIGHT_ANKLE
        elif used_side == "left":
            hip = self.LEFT_HIP
            knee = self.LEFT_KNEE
            ankle = self.LEFT_ANKLE
        elif used_side == "both":
            # Draw both legs
            frame = self._draw_single_leg(frame, keypoints, confidence, "left")
            frame = self._draw_single_leg(frame, keypoints, confidence, "right")
            return frame
        else:
            return frame
        
        return self._draw_single_leg(frame, keypoints, confidence, used_side)
    
    def _draw_single_leg(self, frame, keypoints, confidence, side):
        """Draw a single leg skeleton"""
        if side == "right":
            hip = self.RIGHT_HIP
            knee = self.RIGHT_KNEE
            ankle = self.RIGHT_ANKLE
        else:
            hip = self.LEFT_HIP
            knee = self.LEFT_KNEE
            ankle = self.LEFT_ANKLE
        
        connections = [(hip, knee), (knee, ankle)]
        
        # Draw lines
        for start_idx, end_idx in connections:
            if confidence[start_idx] > self.MIN_CONFIDENCE and confidence[end_idx] > self.MIN_CONFIDENCE:
                start_point = tuple(keypoints[start_idx].astype(int))
                end_point = tuple(keypoints[end_idx].astype(int))
                
                color = {
                    "DOWN": (66, 135, 245),   # Blue
                    "UP": (67, 245, 66)       # Green
                }.get(self.current_state, (150, 150, 150))
                
                cv2.line(frame, start_point, end_point, color, 4, cv2.LINE_AA)
        
        # Draw keypoints with distinct colors
        point_colors = {
            hip: (67, 245, 66),      # Green - Hip
            knee: (255, 165, 0),     # Orange - Knee
            ankle: (245, 66, 245)    # Magenta - Ankle
        }
        
        for idx in [hip, knee, ankle]:
            if confidence[idx] > self.MIN_CONFIDENCE:
                point = tuple(keypoints[idx].astype(int))
                cv2.circle(frame, point, 10, (255, 255, 255), -1, cv2.LINE_AA)
                cv2.circle(frame, point, 6, point_colors[idx], -1, cv2.LINE_AA)
        
        return frame

    def _best_leg_and_angle(self, keypoints, confidence):
        """Choose left or right leg based on visibility and calculate angle."""
        if keypoints is None or confidence is None:
            return None, None
        
        if len(keypoints) == 0 or len(confidence) == 0:
            return None, None
        
        right_indices = [self.RIGHT_HIP, self.RIGHT_KNEE, self.RIGHT_ANKLE]
        left_indices = [self.LEFT_HIP, self.LEFT_KNEE, self.LEFT_ANKLE]
        
        # Check bounds
        max_idx = max(max(right_indices), max(left_indices))
        if len(confidence) <= max_idx or len(keypoints) <= max_idx:
            return None, None
        
        right_valid = [i for i in right_indices if confidence[i] > self.MIN_CONFIDENCE]
        left_valid = [i for i in left_indices if confidence[i] > self.MIN_CONFIDENCE]
        
        used_side = None
        
        if len(right_valid) == 3 and len(left_valid) == 3:
            # Both legs visible - use average
            used_side = "both"
        elif len(right_valid) == 3 and len(left_valid) < 3:
            used_side = "right"
        elif len(left_valid) == 3 and len(right_valid) < 3:
            used_side = "left"
        else:
            return None, None
        
        # Calculate angles
        left_angle = None
        right_angle = None
        
        if used_side in ["left", "both"]:
            left_angle = self.calculate_angle(
                keypoints[self.LEFT_HIP],
                keypoints[self.LEFT_KNEE],
                keypoints[self.LEFT_ANKLE]
            )
        
        if used_side in ["right", "both"]:
            right_angle = self.calculate_angle(
                keypoints[self.RIGHT_HIP],
                keypoints[self.RIGHT_KNEE],
                keypoints[self.RIGHT_ANKLE]
            )
        
        # Return appropriate angle
        if used_side == "both" and left_angle is not None and right_angle is not None:
            return (left_angle + right_angle) / 2, "both"
        elif used_side == "left" and left_angle is not None:
            return left_angle, "left"
        elif used_side == "right" and right_angle is not None:
            return right_angle, "right"
        else:
            return None, None

    def squat_counter(self, results):
        """Detect squat using whichever leg is more visible."""
        try:
            # Safety checks
            if results is None or len(results) == 0:
                return "UNKNOWN", 0, None
            
            if not hasattr(results[0], 'keypoints') or results[0].keypoints is None:
                return "UNKNOWN", 0, None
            
            if len(results[0].keypoints) == 0:
                return "UNKNOWN", 0, None
            
            # Extract keypoints
            try:
                keypoints = results[0].keypoints.xy[0].cpu().numpy()
                confidence = results[0].keypoints.conf[0].cpu().numpy()
            except (IndexError, AttributeError):
                return "UNKNOWN", 0, None
            
            if len(keypoints) == 0 or len(confidence) == 0:
                return "UNKNOWN", 0, None
            
            # Get angle
            knee_angle, used_side = self._best_leg_and_angle(keypoints, confidence)
            
            # Check if angle is None BEFORE comparing
            if knee_angle is None or used_side is None:
                return "UNKNOWN", 0, None
            
            # Determine state
            if knee_angle < self.KNEE_DOWN_ANGLE:
                new_state = "DOWN"
            elif knee_angle > self.KNEE_UP_ANGLE:
                new_state = "UP"
            else:
                new_state = self.current_state if self.current_state != "UNKNOWN" else "UNKNOWN"
            
            # Count squat on DOWN -> UP
            if self.current_state == "DOWN" and new_state == "UP":
                self.squat_count += 1
                print(f"✓ Squat #{self.squat_count} | Angle: {int(knee_angle)}° | Side: {used_side}")
            
            self.current_state = new_state
            
            return new_state, knee_angle, used_side
            
        except Exception as e:
            print(f"Error: {e}")
            return "UNKNOWN", 0, None

    def visualize(self, results):
        """Main visualization method"""
        try:
            if results is None or len(results) == 0:
                return None
            
            if not hasattr(results[0], 'orig_img'):
                return None
            
            frame = results[0].orig_img.copy()
            state, knee_angle, used_side = self.squat_counter(results)
            
            # Draw skeleton for whichever leg was used
            if used_side is not None and hasattr(results[0], 'keypoints') and results[0].keypoints is not None:
                if len(results[0].keypoints) > 0:
                    try:
                        keypoints = results[0].keypoints.xy[0].cpu().numpy()
                        confidence = results[0].keypoints.conf[0].cpu().numpy()
                        frame = self.draw_skeleton(frame, keypoints, confidence, used_side)
                    except (IndexError, AttributeError):
                        pass
            
            # Draw overlay (count + state)
            frame = self.draw_modern_overlay(frame, self.squat_count, state)
            
            return frame
            
        except Exception as e:
            print(f"Error in visualization: {e}")
            if results and len(results) > 0 and hasattr(results[0], 'orig_img'):
                return results[0].orig_img
            return None

    def get_current_stats(self):
        """Return current statistics as dict"""
        return {
            "count": self.squat_count,
            "state": self.current_state,
            "exercise": "squats"
        }

    def reset_counter(self):
        """Reset the rep counter"""
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
