import cv2
import numpy as np
import math
import time
from collections import deque
from ultralytics import YOLO
from app.config.settings import setting
from app.config.device import DEVICE


class PlankMonitor:
    def __init__(self, model_path=None):
        path = model_path or setting.MODEL_PATH
        self.model = YOLO(path)
        self.model.to(DEVICE)

        # Pose state
        self.in_plank = False
        self.plank_start_time = None
        self.last_valid_time = None
        self.current_elapsed = 0.0
        self.total_plank_time = 0.0
        self.best_duration = 0.0

        # Keypoints (COCO/YOLO)
        self.L_SHOULDER = 5
        self.R_SHOULDER = 6
        self.L_HIP = 11
        self.R_HIP = 12
        self.L_ANKLE = 15
        self.R_ANKLE = 16

        # Angle thresholds for good plank (hip angle shoulder–hip–ankle)
        self.MIN_PLANK_ANGLE = 160
        self.MAX_PLANK_ANGLE = 195

        # Body orientation: ratio of horizontal span to vertical span
        # For plank: body is mostly horizontal (ratio > 1.5)
        # For standing: body is mostly vertical (ratio < 0.5)
        self.MIN_HORIZONTAL_RATIO = 1.2  # Body must be more horizontal than vertical
        
        # Grace period
        self.GRACE_SECONDS = 1.5
        
        # Smoothing
        self.angle_buffer = deque(maxlen=5)
        self.orientation_buffer = deque(maxlen=5)
        
        # Track last known values
        self.last_angle = None
        self.last_side = None
        self.last_orientation_ratio = None

    def process_frame(self, frame):
        """Process frame with tracking"""
        results = self.model.track(frame, persist=True, device=DEVICE, verbose=False)
        return results

    def calculate_angle(self, p1, p2, p3):
        """Calculate angle at p2 (vertex) between p1-p2-p3"""
        v1 = np.array([p1[0] - p2[0], p1[1] - p2[1]])
        v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
        dot = np.dot(v1, v2)
        m1 = np.linalg.norm(v1)
        m2 = np.linalg.norm(v2)
        if m1 * m2 == 0:
            return 180
        cos_ang = np.clip(dot / (m1 * m2), -1.0, 1.0)
        return math.degrees(math.acos(cos_ang))

    def get_smoothed_angle(self, angle):
        """Apply smoothing to reduce noise"""
        self.angle_buffer.append(angle)
        return np.median(self.angle_buffer)

    def get_smoothed_orientation(self, ratio):
        """Apply smoothing to orientation ratio"""
        self.orientation_buffer.append(ratio)
        return np.median(self.orientation_buffer)

    def _calculate_body_orientation(self, keypoints, shoulder_idx, ankle_idx):
        """
        Calculate body orientation as horizontal_span / vertical_span.
        
        Returns:
        - > 1.5: Body is horizontal (plank position)
        - < 0.5: Body is vertical (standing)
        - Between: Transitional pose
        """
        shoulder = keypoints[shoulder_idx]
        ankle = keypoints[ankle_idx]
        
        horizontal_span = abs(shoulder[0] - ankle[0])
        vertical_span = abs(shoulder[1] - ankle[1])
        
        # Avoid division by zero
        if vertical_span < 10:
            return 999.0  # Very horizontal
        if horizontal_span < 10:
            return 0.01   # Very vertical
        
        return horizontal_span / vertical_span

    def _best_side_and_metrics(self, keypoints, conf):
        """Get the best visible side and calculate hip angle + orientation"""
        left_ids = [self.L_SHOULDER, self.L_HIP, self.L_ANKLE]
        right_ids = [self.R_SHOULDER, self.R_HIP, self.R_ANKLE]

        left_ok = all(conf[i] > 0.5 for i in left_ids)
        right_ok = all(conf[i] > 0.5 for i in right_ids)

        if right_ok:
            s = keypoints[self.R_SHOULDER]
            h = keypoints[self.R_HIP]
            a = keypoints[self.R_ANKLE]
            angle = self.calculate_angle(s, h, a)
            orientation = self._calculate_body_orientation(keypoints, self.R_SHOULDER, self.R_ANKLE)
            return angle, orientation, "right", right_ids
        if left_ok:
            s = keypoints[self.L_SHOULDER]
            h = keypoints[self.L_HIP]
            a = keypoints[self.L_ANKLE]
            angle = self.calculate_angle(s, h, a)
            orientation = self._calculate_body_orientation(keypoints, self.L_SHOULDER, self.L_ANKLE)
            return angle, orientation, "left", left_ids

        return None, None, None, None

    def _is_good_plank(self, angle, orientation_ratio):
        """
        Check if pose indicates good plank form.
        Must satisfy BOTH conditions:
        1. Body angle is within threshold (straight line)
        2. Body is horizontal (not standing upright)
        """
        if angle is None or orientation_ratio is None:
            return False
        
        angle_ok = self.MIN_PLANK_ANGLE <= angle <= self.MAX_PLANK_ANGLE
        is_horizontal = orientation_ratio > self.MIN_HORIZONTAL_RATIO
        
        return angle_ok and is_horizontal

    def _get_form_feedback(self, angle, orientation_ratio):
        """Get specific feedback about form issues"""
        if angle is None or orientation_ratio is None:
            return "Position yourself in frame", (150, 150, 150)
        
        # Check orientation first (most important)
        if orientation_ratio <= self.MIN_HORIZONTAL_RATIO:
            if orientation_ratio < 0.5:
                return "Get down into plank position", (66, 135, 245)
            else:
                return "Lower your body - get horizontal", (66, 135, 245)
        
        # Then check angle
        if angle < self.MIN_PLANK_ANGLE:
            return "Hips sagging - engage your core!", (66, 135, 245)
        elif angle > self.MAX_PLANK_ANGLE:
            return "Hips too high - lower them down!", (66, 135, 245)
        
        return "Great form! Hold it!", (67, 245, 66)

    def update_plank_state(self, results):
        """Update plank state and timer based on pose detection"""
        if not hasattr(results[0], "keypoints") or results[0].keypoints is None:
            return self._handle_no_detection()

        if len(results[0].keypoints) == 0:
            return self._handle_no_detection()

        keypoints = results[0].keypoints.xy[0].cpu().numpy()
        conf = results[0].keypoints.conf[0].cpu().numpy()

        raw_angle, raw_orientation, side, indices = self._best_side_and_metrics(keypoints, conf)
        now = time.time()

        if raw_angle is not None and raw_orientation is not None:
            smoothed_angle = self.get_smoothed_angle(raw_angle)
            smoothed_orientation = self.get_smoothed_orientation(raw_orientation)
            
            self.last_angle = smoothed_angle
            self.last_side = side
            self.last_orientation_ratio = smoothed_orientation
            
            # Debug output
            print(f"DEBUG: Angle={smoothed_angle:.1f}° | Orientation={smoothed_orientation:.2f} | Side={side} | State={'PLANK' if self.in_plank else 'REST'}")

            if self._is_good_plank(smoothed_angle, smoothed_orientation):
                if not self.in_plank:
                    self.in_plank = True
                    self.plank_start_time = now
                    print(f"✓ Plank STARTED | angle={smoothed_angle:.1f}° | orientation={smoothed_orientation:.2f}")
                self.last_valid_time = now
            else:
                self._check_grace_period(now)
        else:
            self._check_grace_period(now)

        if self.in_plank and self.plank_start_time is not None:
            self.current_elapsed = now - self.plank_start_time
        else:
            self.current_elapsed = 0.0

        state = "PLANK" if self.in_plank else "REST"
        return state, self.current_elapsed, self.last_angle, self.last_orientation_ratio, indices

    def _handle_no_detection(self):
        """Handle frames with no person detected"""
        now = time.time()
        self._check_grace_period(now)
        return "NO_PERSON", self.current_elapsed, None, None, None

    def _check_grace_period(self, now):
        """Check if grace period has expired and end plank if so"""
        if self.in_plank and self.last_valid_time is not None:
            time_since_valid = now - self.last_valid_time
            if time_since_valid > self.GRACE_SECONDS:
                duration = self.last_valid_time - self.plank_start_time
                self.best_duration = max(self.best_duration, duration)
                self.total_plank_time += duration
                print(f"✗ Plank ENDED | duration={duration:.1f}s | best={self.best_duration:.1f}s")
                self.in_plank = False
                self.plank_start_time = None
                self.last_valid_time = None
                self.current_elapsed = 0.0

    def draw_rounded_rectangle(self, img, pt1, pt2, color, radius=15, filled=False):
        """Draw rounded rectangle for modern UI"""
        x1, y1 = pt1
        x2, y2 = pt2
        cv2.rectangle(img, (x1 + radius, y1), (x2 - radius, y2), color, -1 if filled else 1)
        cv2.rectangle(img, (x1, y1 + radius), (x2, y2 - radius), color, -1 if filled else 1)
        t = -1 if filled else 1
        cv2.circle(img, (x1 + radius, y1 + radius), radius, color, t)
        cv2.circle(img, (x2 - radius, y1 + radius), radius, color, t)
        cv2.circle(img, (x1 + radius, y2 - radius), radius, color, t)
        cv2.circle(img, (x2 - radius, y2 - radius), radius, color, t)
        return img

    def draw_skeleton(self, frame, keypoints, conf, indices):
        """Draw skeleton line for plank pose with reference line"""
        if indices is None:
            return frame
            
        shoulder_idx, hip_idx, ankle_idx = indices
        
        # Color based on plank state
        if self.in_plank:
            color = (67, 245, 66)  # Green
        elif self.last_valid_time is not None:
            color = (66, 215, 245)  # Yellow
        else:
            color = (66, 135, 245)  # Blue
        
        # Draw body line: shoulder -> hip -> ankle
        connections = [(shoulder_idx, hip_idx), (hip_idx, ankle_idx)]
        for start_idx, end_idx in connections:
            if conf[start_idx] > 0.5 and conf[end_idx] > 0.5:
                start_point = tuple(keypoints[start_idx].astype(int))
                end_point = tuple(keypoints[end_idx].astype(int))
                cv2.line(frame, start_point, end_point, color, 4, cv2.LINE_AA)
        
        # Draw REFERENCE LINE (horizontal from ankle)
        if conf[ankle_idx] > 0.5 and conf[hip_idx] > 0.5:
            ankle_point = keypoints[ankle_idx].astype(int)
            hip_point = keypoints[hip_idx].astype(int)
            
            # Horizontal reference line at ankle height
            ref_y = ankle_point[1]
            ref_start = (ankle_point[0] - 150, ref_y)
            ref_end = (ankle_point[0] + 150, ref_y)
            cv2.line(frame, ref_start, ref_end, (100, 100, 100), 2, cv2.LINE_AA)
            
            # Label the reference line
            cv2.putText(frame, "FLOOR LEVEL", (ref_end[0] + 5, ref_y + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1, cv2.LINE_AA)
            
            # Draw vertical line showing hip height above reference
            cv2.line(frame, (hip_point[0], ref_y), tuple(hip_point), (255, 255, 0), 2, cv2.LINE_AA)
            
            # Arrow indicator
            if hip_point[1] < ref_y:  # Hip is above reference (correct)
                cv2.arrowedLine(frame, (hip_point[0], ref_y), tuple(hip_point), 
                               (67, 245, 66), 2, cv2.LINE_AA, tipLength=0.3)
            else:  # Hip is below reference (wrong)
                cv2.arrowedLine(frame, tuple(hip_point), (hip_point[0], ref_y),
                               (66, 66, 245), 2, cv2.LINE_AA, tipLength=0.3)
        
        # Draw keypoints
        point_colors = {
            shoulder_idx: (255, 165, 0),
            hip_idx: (67, 245, 66),
            ankle_idx: (245, 66, 245)
        }
        
        for idx in [shoulder_idx, hip_idx, ankle_idx]:
            if conf[idx] > 0.5:
                point = tuple(keypoints[idx].astype(int))
                cv2.circle(frame, point, 10, (255, 255, 255), -1, cv2.LINE_AA)
                cv2.circle(frame, point, 6, point_colors[idx], -1, cv2.LINE_AA)
        
        # Draw angle arc at hip
        if all(conf[i] > 0.5 for i in [shoulder_idx, hip_idx, ankle_idx]):
            hip_point = tuple(keypoints[hip_idx].astype(int))
            cv2.ellipse(frame, hip_point, (30, 30), 0, 0, 360, color, 2, cv2.LINE_AA)
        
        return frame

    def draw_overlay(self, frame, state, elapsed, angle=None, orientation_ratio=None):
        """Draw modern UI overlay with timer and state"""
        h, w = frame.shape[:2]
        
        # Timer box (top-left)
        overlay = frame.copy()
        self.draw_rounded_rectangle(overlay, (20, 20), (220, 130), (40, 40, 40), filled=True, radius=15)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

        secs = int(elapsed)
        mm = secs // 60
        ss = secs % 60
        time_str = f"{mm:02d}:{ss:02d}"

        cv2.putText(frame, time_str, (40, 75),
                    cv2.FONT_HERSHEY_DUPLEX, 1.8, (255, 255, 255), 3, cv2.LINE_AA)
        cv2.putText(frame, "PLANK", (40, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)
        
        best_secs = int(self.best_duration)
        best_str = f"Best: {best_secs // 60:02d}:{best_secs % 60:02d}"
        cv2.putText(frame, best_str, (40, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1, cv2.LINE_AA)

        # State box (top-right)
        overlay2 = frame.copy()
        x1 = w - 240
        self.draw_rounded_rectangle(overlay2, (x1, 20), (w - 20, 100), (40, 40, 40), filled=True, radius=12)
        cv2.addWeighted(overlay2, 0.85, frame, 0.15, 0, frame)

        if state == "PLANK":
            color = (67, 245, 66)
        elif state == "NO_PERSON":
            color = (100, 100, 100)
        else:
            color = (66, 135, 245)
            
        cv2.putText(frame, state, (x1 + 20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)
        
        # Show angle and orientation ratio
        if angle is not None:
            cv2.putText(frame, f"Angle: {int(angle)}deg", (x1 + 20, 75),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1, cv2.LINE_AA)
        if orientation_ratio is not None:
            cv2.putText(frame, f"H/V: {orientation_ratio:.2f}", (x1 + 130, 75),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1, cv2.LINE_AA)
        
        # Form feedback (bottom)
        feedback, fb_color = self._get_form_feedback(angle, orientation_ratio)
        
        text_size = cv2.getTextSize(feedback, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
        box_x1 = (w - text_size[0]) // 2 - 20
        box_x2 = box_x1 + text_size[0] + 40
        box_y1 = h - 60
        box_y2 = h - 20
        
        overlay3 = frame.copy()
        self.draw_rounded_rectangle(overlay3, (box_x1, box_y1), (box_x2, box_y2), (40, 40, 40), filled=True, radius=10)
        cv2.addWeighted(overlay3, 0.85, frame, 0.15, 0, frame)
        
        cv2.putText(frame, feedback, (box_x1 + 20, h - 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, fb_color, 2, cv2.LINE_AA)
        
        return frame

    def visualize(self, results):
        """Main visualization method"""
        try:
            if not hasattr(results[0], "orig_img"):
                return None
            
            frame = results[0].orig_img.copy()
            state, elapsed, angle, orientation_ratio, indices = self.update_plank_state(results)
            
            if indices is not None and hasattr(results[0], 'keypoints') and len(results[0].keypoints) > 0:
                keypoints = results[0].keypoints.xy[0].cpu().numpy()
                conf = results[0].keypoints.conf[0].cpu().numpy()
                frame = self.draw_skeleton(frame, keypoints, conf, indices)
            
            frame = self.draw_overlay(frame, state, elapsed, angle, orientation_ratio)
            return frame
            
        except Exception as e:
            print(f"Error in visualization: {e}")
            return results[0].orig_img if hasattr(results[0], 'orig_img') else None

    def get_current_stats(self):
        """Return current statistics as dict"""
        return {
            "current_time": self.current_elapsed,
            "best_time": self.best_duration,
            "total_time": self.total_plank_time,
            "state": "PLANK" if self.in_plank else "REST",
            "exercise": "plank"
        }

    def reset(self):
        """Reset all timers and state"""
        self.in_plank = False
        self.plank_start_time = None
        self.last_valid_time = None
        self.current_elapsed = 0.0
        self.total_plank_time = 0.0
        self.best_duration = 0.0
        self.angle_buffer.clear()
        self.orientation_buffer.clear()
        self.last_angle = None
        self.last_side = None
        self.last_orientation_ratio = None


if __name__ == "__main__":
    monitor = PlankMonitor()
    cap = cv2.VideoCapture(0)

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        results = monitor.process_frame(frame)
        annotated = monitor.visualize(results)
        
        if annotated is not None:
            cv2.imshow("Plank Timer", annotated)
        
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    stats = monitor.get_current_stats()
    print(f"\n{'='*50}")
    print(f"Best Hold: {stats['best_time']:.1f}s")
    print(f"Total Plank Time: {stats['total_time']:.1f}s")
    print(f"{'='*50}\n")

    cap.release()
    cv2.destroyAllWindows()