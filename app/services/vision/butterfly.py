import cv2
import numpy as np
import math
import time
from collections import deque
from ultralytics import YOLO
from app.config.settings import setting
from app.config.device import DEVICE


class BaddhaKonasanaMonitor:
    """
    Baddha Konasana (Butterfly/Bound Angle Pose) Monitor
    
    Key metrics:
    - Knee spread angle (hip flexibility)
    - Knee height from ground (how far down knees can go)
    - Spine alignment (upright posture)
    - Forward fold depth (optional variation)
    
    This pose measures hip external rotation flexibility.
    """
    
    def __init__(self, model_path=None):
        path = model_path or setting.MODEL_PATH
        self.model = YOLO(path)
        self.model.to(DEVICE)
        
        # COCO Keypoint indices
        self.NOSE = 0
        self.L_EYE = 1
        self.R_EYE = 2
        self.L_SHOULDER = 5
        self.R_SHOULDER = 6
        self.L_HIP = 11
        self.R_HIP = 12
        self.L_KNEE = 13
        self.R_KNEE = 14
        self.L_ANKLE = 15
        self.R_ANKLE = 16
        
        # Pose state
        self.in_pose = False
        self.pose_start_time = None
        self.current_hold_time = 0.0
        self.best_hold_time = 0.0
        self.total_hold_time = 0.0
        
        # Flexibility tracking
        self.current_knee_spread = 0.0  # Angle between knees
        self.best_knee_spread = 0.0
        self.current_flexibility_score = 0.0  # 0-100%
        
        # Thresholds
        self.MIN_KNEE_SPREAD = 60       # Minimum spread to be considered in pose
        self.GOOD_KNEE_SPREAD = 120     # Good flexibility
        self.EXCELLENT_KNEE_SPREAD = 160  # Excellent flexibility (knees near ground)
        self.MIN_SEATED_DETECTION = True
        
        # Feet together detection
        self.MAX_FEET_DISTANCE = 100    # Feet should be close together
        
        # Grace period
        self.GRACE_SECONDS = 1.0
        self.last_valid_time = None
        
        # Smoothing
        self.spread_buffer = deque(maxlen=5)
        
        # State tracking
        self.current_state = "READY"
        self.last_feedback = ""
        
    def process_frame(self, frame):
        """Process frame with pose detection"""
        results = self.model.track(frame, persist=True, device=DEVICE, verbose=False)
        return results
    
    def calculate_angle(self, p1, p2, p3):
        """Calculate angle at p2 (vertex)"""
        v1 = np.array([p1[0] - p2[0], p1[1] - p2[1]])
        v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
        
        dot = np.dot(v1, v2)
        m1 = np.linalg.norm(v1)
        m2 = np.linalg.norm(v2)
        
        if m1 * m2 == 0:
            return 180
        
        cos_ang = np.clip(dot / (m1 * m2), -1.0, 1.0)
        return math.degrees(math.acos(cos_ang))
    
    def get_midpoint(self, p1, p2):
        """Get midpoint between two points"""
        return np.array([(p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2])
    
    def _calculate_knee_spread_angle(self, keypoints):
        """
        Calculate the angle of knee spread.
        Uses hip as vertex, measuring angle between left knee - hip - right knee.
        """
        mid_hip = self.get_midpoint(keypoints[self.L_HIP], keypoints[self.R_HIP])
        l_knee = keypoints[self.L_KNEE]
        r_knee = keypoints[self.R_KNEE]
        
        # Angle at hip center between two knees
        spread_angle = self.calculate_angle(l_knee, mid_hip, r_knee)
        
        return spread_angle
    
    def _analyze_pose(self, keypoints, conf):
        """Analyze the butterfly pose"""
        # Check visibility
        required = [self.L_HIP, self.R_HIP, self.L_KNEE, self.R_KNEE,
                   self.L_ANKLE, self.R_ANKLE, self.L_SHOULDER, self.R_SHOULDER]
        
        if not all(conf[i] > 0.4 for i in required):
            return None
        
        # Calculate key metrics
        mid_hip = self.get_midpoint(keypoints[self.L_HIP], keypoints[self.R_HIP])
        mid_shoulder = self.get_midpoint(keypoints[self.L_SHOULDER], keypoints[self.R_SHOULDER])
        
        # 1. Knee spread angle
        knee_spread = self._calculate_knee_spread_angle(keypoints)
        
        # 2. Feet distance (should be close together)
        feet_dist = np.linalg.norm(keypoints[self.L_ANKLE] - keypoints[self.R_ANKLE])
        feet_together = feet_dist < self.MAX_FEET_DISTANCE
        
        # 3. Feet position relative to hips (feet should be in front of/close to hips)
        mid_ankle = self.get_midpoint(keypoints[self.L_ANKLE], keypoints[self.R_ANKLE])
        feet_near_hips = np.linalg.norm(mid_ankle - mid_hip) < 200
        
        # 4. Spine alignment (shoulder above hip)
        spine_upright = mid_shoulder[1] < mid_hip[1]  # Shoulder higher than hip
        
        # 5. Seated check (hips low in frame)
        is_seated = mid_hip[1] > keypoints[self.L_SHOULDER][1]  # Hip below shoulder
        
        # 6. Calculate flexibility score (0-100)
        # Based on knee spread angle
        if knee_spread >= self.EXCELLENT_KNEE_SPREAD:
            flexibility = 100
        elif knee_spread >= self.GOOD_KNEE_SPREAD:
            flexibility = 70 + (knee_spread - self.GOOD_KNEE_SPREAD) / (self.EXCELLENT_KNEE_SPREAD - self.GOOD_KNEE_SPREAD) * 30
        elif knee_spread >= self.MIN_KNEE_SPREAD:
            flexibility = 30 + (knee_spread - self.MIN_KNEE_SPREAD) / (self.GOOD_KNEE_SPREAD - self.MIN_KNEE_SPREAD) * 40
        else:
            flexibility = (knee_spread / self.MIN_KNEE_SPREAD) * 30
        
        # 7. Knee height relative to hip (lower = more flexible)
        avg_knee_y = (keypoints[self.L_KNEE][1] + keypoints[self.R_KNEE][1]) / 2
        knee_drop = avg_knee_y - mid_hip[1]  # Positive = knees below hips
        
        return {
            "knee_spread": knee_spread,
            "feet_together": feet_together,
            "feet_near_hips": feet_near_hips,
            "spine_upright": spine_upright,
            "is_seated": is_seated,
            "flexibility_score": flexibility,
            "knee_drop": knee_drop,
            "feet_dist": feet_dist,
            "mid_hip": mid_hip,
            "mid_shoulder": mid_shoulder,
            "l_knee": keypoints[self.L_KNEE],
            "r_knee": keypoints[self.R_KNEE],
            "l_ankle": keypoints[self.L_ANKLE],
            "r_ankle": keypoints[self.R_ANKLE]
        }
    
    def _is_valid_pose(self, analysis):
        """Check if in valid butterfly pose"""
        if analysis is None:
            return False
        
        # Must have minimum knee spread
        if analysis["knee_spread"] < self.MIN_KNEE_SPREAD:
            return False
        
        # Feet should be reasonably close
        if not analysis["feet_together"] and not analysis["feet_near_hips"]:
            return False
        
        # Should appear seated
        if not analysis["is_seated"]:
            return False
        
        return True
    
    def update_pose_state(self, results):
        """Update pose state"""
        now = time.time()
        
        if not hasattr(results[0], "keypoints") or results[0].keypoints is None:
            return self._handle_no_detection(now)
        
        if len(results[0].keypoints) == 0:
            return self._handle_no_detection(now)
        
        keypoints = results[0].keypoints.xy[0].cpu().numpy()
        conf = results[0].keypoints.conf[0].cpu().numpy()
        
        analysis = self._analyze_pose(keypoints, conf)
        
        if analysis is None:
            return self._handle_no_detection(now)
        
        # Smooth knee spread
        self.spread_buffer.append(analysis["knee_spread"])
        smoothed_spread = np.median(self.spread_buffer)
        self.current_knee_spread = smoothed_spread
        self.current_flexibility_score = analysis["flexibility_score"]
        
        if self._is_valid_pose(analysis):
            if not self.in_pose:
                self.in_pose = True
                self.pose_start_time = now
                self.current_state = "HOLDING"
            
            self.last_valid_time = now
            self.best_knee_spread = max(self.best_knee_spread, smoothed_spread)
            self.current_hold_time = now - self.pose_start_time
            self.best_hold_time = max(self.best_hold_time, self.current_hold_time)
            
            self.last_feedback = self._generate_feedback(analysis)
        else:
            self._check_grace_period(now)
            self.last_feedback = self._get_setup_feedback(analysis)
        
        return {
            "state": self.current_state,
            "hold_time": self.current_hold_time,
            "knee_spread": self.current_knee_spread,
            "best_spread": self.best_knee_spread,
            "flexibility": self.current_flexibility_score,
            "analysis": analysis,
            "feedback": self.last_feedback
        }
    
    def _handle_no_detection(self, now):
        """Handle no detection"""
        self._check_grace_period(now)
        return {
            "state": self.current_state,
            "hold_time": self.current_hold_time,
            "knee_spread": self.current_knee_spread,
            "best_spread": self.best_knee_spread,
            "flexibility": self.current_flexibility_score,
            "analysis": None,
            "feedback": "Position yourself in the frame"
        }
    
    def _check_grace_period(self, now):
        """Check grace period"""
        if self.in_pose and self.last_valid_time is not None:
            if now - self.last_valid_time > self.GRACE_SECONDS:
                self.total_hold_time += self.current_hold_time
                self.in_pose = False
                self.pose_start_time = None
                self.current_hold_time = 0.0
                self.current_state = "READY"
    
    def _generate_feedback(self, analysis):
        """Generate form feedback"""
        if analysis["flexibility_score"] >= 90:
            return "Excellent flexibility! Hold steady"
        elif analysis["flexibility_score"] >= 70:
            return "Great hip opening! Relax into the stretch"
        elif analysis["flexibility_score"] >= 50:
            return "Good form! Let gravity pull knees down"
        else:
            return "Keep breathing, let knees relax down"
    
    def _get_setup_feedback(self, analysis):
        """Feedback for getting into pose"""
        if analysis is None:
            return "Sit with soles of feet together"
        
        if not analysis["feet_together"]:
            return "Bring soles of feet together"
        
        if analysis["knee_spread"] < self.MIN_KNEE_SPREAD:
            return "Open your knees out to the sides"
        
        if not analysis["is_seated"]:
            return "Sit on the ground"
        
        return "Adjust your position"
    
    def visualize(self, results):
        """Draw visualization"""
        if not hasattr(results[0], "orig_img"):
            return None
        
        frame = results[0].orig_img.copy()
        state_info = self.update_pose_state(results)
        
        h, w = frame.shape[:2]
        
        # Draw skeleton if available
        if state_info["analysis"] is not None:
            analysis = state_info["analysis"]
            color = (67, 245, 66) if self.in_pose else (66, 135, 245)
            
            # Draw legs (hip to knee to ankle)
            cv2.line(frame, tuple(analysis["mid_hip"].astype(int)),
                    tuple(analysis["l_knee"].astype(int)), color, 3)
            cv2.line(frame, tuple(analysis["l_knee"].astype(int)),
                    tuple(analysis["l_ankle"].astype(int)), color, 3)
            cv2.line(frame, tuple(analysis["mid_hip"].astype(int)),
                    tuple(analysis["r_knee"].astype(int)), color, 3)
            cv2.line(frame, tuple(analysis["r_knee"].astype(int)),
                    tuple(analysis["r_ankle"].astype(int)), color, 3)
            
            # Draw spread angle arc
            hip_pt = tuple(analysis["mid_hip"].astype(int))
            cv2.ellipse(frame, hip_pt, (50, 50), 0,
                       -90 - analysis["knee_spread"]/2,
                       -90 + analysis["knee_spread"]/2,
                       (255, 200, 100), 3)
            
            # Draw keypoints
            for pt in [analysis["mid_hip"], analysis["l_knee"], analysis["r_knee"],
                      analysis["l_ankle"], analysis["r_ankle"]]:
                cv2.circle(frame, tuple(pt.astype(int)), 8, (255, 255, 255), -1)
                cv2.circle(frame, tuple(pt.astype(int)), 5, color, -1)
        
        # UI Overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (20, 20), (280, 150), (40, 40, 40), -1)
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)
        
        # Timer
        secs = int(state_info["hold_time"])
        cv2.putText(frame, f"{secs // 60:02d}:{secs % 60:02d}", (40, 65),
                   cv2.FONT_HERSHEY_DUPLEX, 1.4, (255, 255, 255), 2)
        cv2.putText(frame, "BADDHA KONASANA", (40, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        
        # Flexibility score
        flex = state_info["flexibility"]
        cv2.putText(frame, f"Flexibility: {int(flex)}%", (40, 115),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 200, 255), 1)
        cv2.putText(frame, f"Spread: {int(state_info['knee_spread'])}°", (40, 135),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
        
        # State
        state_color = (67, 245, 66) if self.in_pose else (100, 100, 100)
        cv2.putText(frame, state_info["state"], (w - 150, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, state_color, 2)
        
        # Flexibility progress bar
        bar_width = 200
        bar_x = w - bar_width - 40
        cv2.rectangle(frame, (bar_x, 70), (bar_x + bar_width, 90), (60, 60, 60), -1)
        fill_width = int((flex / 100) * bar_width)
        bar_color = (67, 245, 66) if flex > 70 else (66, 200, 245) if flex > 40 else (66, 135, 245)
        cv2.rectangle(frame, (bar_x, 70), (bar_x + fill_width, 90), bar_color, -1)
        cv2.putText(frame, "HIP FLEXIBILITY", (bar_x, 65),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
        
        # Feedback
        cv2.rectangle(frame, (20, h - 60), (w - 20, h - 20), (40, 40, 40), -1)
        cv2.putText(frame, state_info["feedback"], (40, h - 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        return frame
    
    def get_current_stats(self):
        """Return current statistics"""
        return {
            "current_time": self.current_hold_time,
            "best_time": self.best_hold_time,
            "total_time": self.total_hold_time,
            "current_spread": self.current_knee_spread,
            "best_spread": self.best_knee_spread,
            "flexibility": self.current_flexibility_score,
            "state": self.current_state,
            "exercise": "baddha_konasana"
        }
    
    def reset(self):
        """Reset all state"""
        self.in_pose = False
        self.pose_start_time = None
        self.current_hold_time = 0.0
        self.best_hold_time = 0.0
        self.total_hold_time = 0.0
        self.current_knee_spread = 0.0
        self.best_knee_spread = 0.0
        self.current_flexibility_score = 0.0
        self.current_state = "READY"
        self.spread_buffer.clear()

if __name__ == "__main__":
    monitor = BaddhaKonasanaMonitor()
    cap = cv2.VideoCapture(0)

    print("Starting Baddha Konasana monitor. Press 'q' to quit.")
    print("Sit with soles of feet together, knees out to sides.")

    while True:
        success, frame = cap.read()
        if not success:
            print("Failed to read from camera.")
            break

        # Run pose model
        results = monitor.process_frame(frame)
        # Get annotated frame
        annotated = monitor.visualize(results)

        if annotated is not None:
            cv2.imshow("Baddha Konasana Monitor", annotated)
        else:
            cv2.imshow("Baddha Konasana Monitor", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    # After loop, print stats
    stats = monitor.get_current_stats()
    print("\n" + "=" * 50)
    print("Baddha Konasana session summary")
    print(f"Current hold time  : {stats['current_time']:.1f} s")
    print(f"Best single hold   : {stats['best_time']:.1f} s")
    print(f"Total hold time    : {stats['total_time']:.1f} s")
    print(f"Best knee spread   : {stats['best_spread']:.1f}°")
    print(f"Best flexibility   : {stats['flexibility']:.1f}%")
    print("=" * 50 + "\n")

    cap.release()
    cv2.destroyAllWindows()
