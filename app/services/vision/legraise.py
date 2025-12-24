import cv2
import numpy as np
import math
from collections import deque
from ultralytics import YOLO
from app.config.settings import setting
from app.config.device import DEVICE


class LegRaiseMonitor:
    def __init__(self, model_path=None):
        path = model_path or setting.MODEL_PATH
        self.model = YOLO(path)
        self.model.to(DEVICE)
        
        # Leg raise counter state
        self.rep_count = 0
        self.current_state = "UNKNOWN"
        
        # Keypoints (COCO format)
        self.LEFT_HIP = 11
        self.RIGHT_HIP = 12
        self.LEFT_ANKLE = 15
        self.RIGHT_ANKLE = 16
        
        # Height thresholds (how much higher ankle must be than hip)
        # Positive = ankle is ABOVE hip (raised)
        # These will be calculated as percentage of torso length for scale invariance
        self.UP_THRESHOLD = 0.3    # Ankle 30% of torso height above hip = UP
        self.DOWN_THRESHOLD = 0.1  # Ankle within 10% of hip level = DOWN
        
        # Smoothing buffer to reduce noise
        self.height_buffer = deque(maxlen=5)
        
        # Prevent double counting
        self.last_count_frame = 0
        self.frame_count = 0
        self.min_frames_between_reps = 10
        
        # Track initial hip position for reference
        self.reference_hip_y = None
    
    def process_frame(self, frame):
        """Process frame with tracking"""
        results = self.model.track(frame, persist=True, device=DEVICE, verbose=False)
        return results

    def get_smoothed_height(self, height_ratio):
        """Apply smoothing to reduce noise"""
        self.height_buffer.append(height_ratio)
        return np.median(self.height_buffer)

    def _get_highest_ankle(self, keypoints, confidence):
        """
        Get the ankle that is highest (smallest Y value).
        Returns ankle index, hip index, and which side.
        """
        left_ankle_conf = confidence[self.LEFT_ANKLE]
        right_ankle_conf = confidence[self.RIGHT_ANKLE]
        left_hip_conf = confidence[self.LEFT_HIP]
        right_hip_conf = confidence[self.RIGHT_HIP]
        
        left_valid = left_ankle_conf > 0.5 and left_hip_conf > 0.5
        right_valid = right_ankle_conf > 0.5 and right_hip_conf > 0.5
        
        if not left_valid and not right_valid:
            return None, None, None
        
        # Get ankle Y positions
        left_ankle_y = keypoints[self.LEFT_ANKLE][1] if left_valid else float('inf')
        right_ankle_y = keypoints[self.RIGHT_ANKLE][1] if right_valid else float('inf')
        
        # Return the HIGHER ankle (smaller Y)
        if left_ankle_y < right_ankle_y and left_valid:
            return self.LEFT_ANKLE, self.LEFT_HIP, "left"
        elif right_valid:
            return self.RIGHT_ANKLE, self.RIGHT_HIP, "right"
        
        return None, None, None

    def _calculate_relative_height(self, keypoints, ankle_idx, hip_idx):
        """
        Calculate how high the ankle is relative to the hip.
        Returns a ratio: positive = ankle above hip, negative = ankle below hip
        
        We normalize by the distance between hips (body width) for scale invariance.
        """
        ankle_y = keypoints[ankle_idx][1]
        hip_y = keypoints[hip_idx][1]
        
        # In image coordinates, Y increases downward
        # So if ankle_y < hip_y, ankle is ABOVE hip
        height_diff = hip_y - ankle_y  # Positive when ankle is raised
        
        # Normalize by hip width for scale invariance
        left_hip = keypoints[self.LEFT_HIP]
        right_hip = keypoints[self.RIGHT_HIP]
        hip_width = np.linalg.norm(left_hip - right_hip)
        
        if hip_width < 10:  # Too small, use raw pixels
            hip_width = 100  # Default normalization
        
        return height_diff / hip_width

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

    def draw_modern_overlay(self, frame, count, state, height_ratio=None):
        """Draw modern minimal UI overlay"""
        h, w = frame.shape[:2]
        
        overlay = frame.copy()
        self.draw_rounded_rectangle(overlay, (20, 20), (200, 120), (40, 40, 40), filled=True, radius=15)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
        
        cv2.putText(frame, str(count), (40, 85), 
                   cv2.FONT_HERSHEY_DUPLEX, 2.0, (255, 255, 255), 3, cv2.LINE_AA)
        cv2.putText(frame, "LEG RAISES", (40, 105), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA)
        
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
        
        # Show height ratio for debugging
        if height_ratio is not None:
            cv2.putText(frame, f"{height_ratio:.2f}", (state_box_x1 + 120, 55), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
        
        return frame

    def draw_skeleton(self, frame, keypoints, confidence, ankle_idx, hip_idx, used_side):
        """Draw skeleton for the raised leg"""
        color = {
            "DOWN": (66, 135, 245),
            "UP": (67, 245, 66)
        }.get(self.current_state, (150, 150, 150))
        
        # Draw line from hip to ankle
        if confidence[hip_idx] > 0.5 and confidence[ankle_idx] > 0.5:
            hip_point = tuple(keypoints[hip_idx].astype(int))
            ankle_point = tuple(keypoints[ankle_idx].astype(int))
            cv2.line(frame, hip_point, ankle_point, color, 4, cv2.LINE_AA)
            
            # Draw horizontal reference line at hip level
            ref_start = (hip_point[0] - 80, hip_point[1])
            ref_end = (hip_point[0] + 80, hip_point[1])
            cv2.line(frame, ref_start, ref_end, (100, 100, 100), 2, cv2.LINE_AA)
            
            # Draw "above hip" indicator line
            cv2.putText(frame, "HIP LEVEL", (ref_end[0] + 5, ref_end[1] + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1, cv2.LINE_AA)
        
        # Draw keypoints
        for idx, point_color in [(ankle_idx, (245, 66, 245)), (hip_idx, (67, 245, 66))]:
            if confidence[idx] > 0.5:
                point = tuple(keypoints[idx].astype(int))
                cv2.circle(frame, point, 10, (255, 255, 255), -1, cv2.LINE_AA)
                cv2.circle(frame, point, 6, point_color, -1, cv2.LINE_AA)
        
        # Label which leg
        if confidence[hip_idx] > 0.5:
            hip_point = tuple(keypoints[hip_idx].astype(int))
            cv2.putText(frame, f"{used_side.upper()} LEG", 
                       (hip_point[0] + 15, hip_point[1] - 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA)
        
        return frame

    def leg_raise_counter(self, results):
        """Detect leg raise by tracking ankle height relative to hip"""
        self.frame_count += 1
        
        try:
            if not hasattr(results[0], 'keypoints') or results[0].keypoints is None:
                return "UNKNOWN", 0, None, None, None
            
            if len(results[0].keypoints) == 0:
                return "UNKNOWN", 0, None, None, None
            
            keypoints = results[0].keypoints.xy[0].cpu().numpy()
            confidence = results[0].keypoints.conf[0].cpu().numpy()
            
            # Get the highest ankle
            ankle_idx, hip_idx, used_side = self._get_highest_ankle(keypoints, confidence)
            if ankle_idx is None:
                return "UNKNOWN", 0, None, None, None
            
            # Calculate relative height (positive = ankle above hip)
            raw_height_ratio = self._calculate_relative_height(keypoints, ankle_idx, hip_idx)
            smoothed_ratio = self.get_smoothed_height(raw_height_ratio)
            
            # Debug output
            print(f"DEBUG: Height ratio = {smoothed_ratio:.2f} | Side = {used_side} | State = {self.current_state}")
            
            # Determine state based on height ratio
            # Positive ratio = ankle is ABOVE hip = leg raised
            if smoothed_ratio > self.UP_THRESHOLD:
                new_state = "UP"
            elif smoothed_ratio < self.DOWN_THRESHOLD:
                new_state = "DOWN"
            else:
                # In transition zone - keep current state (hysteresis)
                new_state = self.current_state if self.current_state != "UNKNOWN" else "UNKNOWN"
            
            # Count on DOWN -> UP transition
            frames_since_last = self.frame_count - self.last_count_frame
            if (self.current_state == "DOWN" and 
                new_state == "UP" and 
                frames_since_last >= self.min_frames_between_reps):
                
                self.rep_count += 1
                self.last_count_frame = self.frame_count
                print(f"✓ Leg Raise #{self.rep_count} | Height: {smoothed_ratio:.2f} | Side: {used_side}")
            
            self.current_state = new_state
            
            return new_state, smoothed_ratio, used_side, ankle_idx, hip_idx
            
        except Exception as e:
            print(f"Error: {e}")
            return "UNKNOWN", 0, None, None, None

    def visualize(self, results):
        """Main visualization method"""
        try:
            if not hasattr(results[0], 'orig_img'):
                return None
            
            frame = results[0].orig_img.copy()
            state, height_ratio, used_side, ankle_idx, hip_idx = self.leg_raise_counter(results)
            
            if ankle_idx is not None and hasattr(results[0], 'keypoints') and len(results[0].keypoints) > 0:
                keypoints = results[0].keypoints.xy[0].cpu().numpy()
                confidence = results[0].keypoints.conf[0].cpu().numpy()
                frame = self.draw_skeleton(frame, keypoints, confidence, ankle_idx, hip_idx, used_side)
            
            frame = self.draw_modern_overlay(frame, self.rep_count, state, height_ratio)
            
            return frame
            
        except Exception as e:
            print(f"Error in visualization: {e}")
            return results[0].orig_img if hasattr(results[0], 'orig_img') else None

    def get_current_stats(self):
        return {
            "count": self.rep_count,
            "state": self.current_state,
            "exercise": "leg_raises"
        }

    def reset_counter(self):
        self.rep_count = 0
        self.current_state = "UNKNOWN"
        self.height_buffer.clear()
        self.last_count_frame = 0
        self.frame_count = 0


if __name__ == "__main__":
    monitor = LegRaiseMonitor()
    cap = cv2.VideoCapture(0)
    
    while True:
        success, frame = cap.read()
        if not success:
            break
        
        results = monitor.process_frame(frame)
        annotated_frame = monitor.visualize(results)
        
        if annotated_frame is not None:
            cv2.imshow("Leg Raise Counter", annotated_frame)
        
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    
    print(f"\n{'='*50}")
    print(f"Final Count: {monitor.rep_count} Leg Raises")
    print(f"{'='*50}\n")
    
    cap.release()
    cv2.destroyAllWindows()