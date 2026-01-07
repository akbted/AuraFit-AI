import cv2
import numpy as np
import math
import time
from collections import deque
from ultralytics import YOLO
from app.config.settings import setting
from app.config.device import DEVICE


class UstrasanaMonitor:
    """
    Ustrasana (Camel Pose) Monitor
    
    Key metrics:
    - Backbend depth (spine curvature)
    - Hip position (should be over knees)
    - Shoulder opening
    - Head position (can be neutral or dropped back)
    
    This pose measures spine flexibility and hip flexor stretch.
    """
    
    def __init__(self, model_path=None):
        path = model_path or setting.MODEL_PATH
        self.model = YOLO(path)
        self.model.to(DEVICE)
        
        # COCO Keypoint indices
        self.NOSE = 0
        self.L_EYE = 1
        self.R_EYE = 2
        self.L_EAR = 3
        self.R_EAR = 4
        self.L_SHOULDER = 5
        self.R_SHOULDER = 6
        self.L_ELBOW = 7
        self.R_ELBOW = 8
        self.L_WRIST = 9
        self.R_WRIST = 10
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
        
        # Backbend depth tracking
        self.current_backbend_depth = 0.0  # 0-100%
        self.best_backbend_depth = 0.0
        
        # Thresholds
        # Hip-Shoulder angle relative to vertical (more angle = deeper backbend)
        self.MIN_BACKBEND_ANGLE = 15    # Minimum to be in pose
        self.GOOD_BACKBEND_ANGLE = 35   # Good depth
        self.EXCELLENT_BACKBEND_ANGLE = 55  # Very deep backbend
        
        # Hip over knees check
        self.HIP_KNEE_TOLERANCE = 80  # Horizontal distance tolerance
        
        # Kneeling check - knees should be lower than hips
        self.MIN_KNEE_HIP_DIFF = 50
        
        # Grace period
        self.GRACE_SECONDS = 1.0
        self.last_valid_time = None
        
        # Smoothing
        self.depth_buffer = deque(maxlen=5)
        
        # State tracking
        self.current_state = "READY"
        self.last_feedback = ""
        
    def process_frame(self, frame):
        """Process frame"""
        results = self.model.track(frame, persist=True, device=DEVICE, verbose=False)
        return results
    
    def calculate_angle(self, p1, p2, p3):
        """Calculate angle at p2"""
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
        """Get midpoint"""
        return np.array([(p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2])
    
    def _calculate_backbend_angle(self, mid_shoulder, mid_hip, mid_knee):
        """
        Calculate backbend angle.
        Measures how far back the shoulders are relative to hips.
        Uses vertical line through hip as reference.
        """
        # Create a point directly above hip (vertical reference)
        hip_above = np.array([mid_hip[0], mid_hip[1] - 100])
        
        # Angle: vertical - hip - shoulder
        # When standing straight: ~0 degrees
        # When in camel pose: positive angle (shoulders behind hips)
        
        backbend_angle = self.calculate_angle(hip_above, mid_hip, mid_shoulder)
        
        # If shoulder is behind hip (x-wise), it's a backbend
        if mid_shoulder[0] < mid_hip[0]:  # Assuming side view, left = back
            return backbend_angle
        else:
            # Need to check for right-facing view
            return backbend_angle
    
    def _analyze_pose(self, keypoints, conf):
        """Analyze camel pose"""
        # Check key point visibility
        required = [self.L_SHOULDER, self.R_SHOULDER, self.L_HIP, self.R_HIP,
                   self.L_KNEE, self.R_KNEE]
        
        if not all(conf[i] > 0.4 for i in required):
            return None
        
        mid_shoulder = self.get_midpoint(keypoints[self.L_SHOULDER], keypoints[self.R_SHOULDER])
        mid_hip = self.get_midpoint(keypoints[self.L_HIP], keypoints[self.R_HIP])
        mid_knee = self.get_midpoint(keypoints[self.L_KNEE], keypoints[self.R_KNEE])
        
        # 1. Check if kneeling (knees below hips)
        is_kneeling = mid_knee[1] > mid_hip[1] + self.MIN_KNEE_HIP_DIFF
        
        # 2. Check hips over knees (horizontal alignment)
        hip_knee_h_dist = abs(mid_hip[0] - mid_knee[0])
        hips_over_knees = hip_knee_h_dist < self.HIP_KNEE_TOLERANCE
        
        # 3. Calculate backbend angle
        # Using spine angle: shoulder-hip-knee
        spine_angle = self.calculate_angle(mid_shoulder, mid_hip, mid_knee)
        
        # For camel pose, shoulders go back, so we measure deviation from straight
        # Straight kneeling would be ~180, camel brings it lower
        backbend_deviation = 180 - spine_angle
        
        # Alternative: horizontal displacement of shoulders behind hips
        shoulder_behind_hip = mid_hip[0] - mid_shoulder[0]  # Positive when shoulders behind
        
        # 4. Calculate depth score
        if backbend_deviation >= self.EXCELLENT_BACKBEND_ANGLE:
            depth_score = 100
        elif backbend_deviation >= self.GOOD_BACKBEND_ANGLE:
            depth_score = 60 + (backbend_deviation - self.GOOD_BACKBEND_ANGLE) / (self.EXCELLENT_BACKBEND_ANGLE - self.GOOD_BACKBEND_ANGLE) * 40
        elif backbend_deviation >= self.MIN_BACKBEND_ANGLE:
            depth_score = 30 + (backbend_deviation - self.MIN_BACKBEND_ANGLE) / (self.GOOD_BACKBEND_ANGLE - self.MIN_BACKBEND_ANGLE) * 30
        else:
            depth_score = (backbend_deviation / self.MIN_BACKBEND_ANGLE) * 30
        
        # 5. Check arm position (hands reaching for heels)
        arms_back = False
        if conf[self.L_WRIST] > 0.3 and conf[self.R_WRIST] > 0.3:
            avg_wrist_y = (keypoints[self.L_WRIST][1] + keypoints[self.R_WRIST][1]) / 2
            arms_back = avg_wrist_y > mid_hip[1]  # Wrists below hip level
        
        # 6. Head position
        head_back = False
        if conf[self.NOSE] > 0.3:
            head_back = keypoints[self.NOSE][1] > mid_shoulder[1]  # Head dropped back
        
        return {
            "is_kneeling": is_kneeling,
            "hips_over_knees": hips_over_knees,
            "backbend_angle": backbend_deviation,
            "depth_score": depth_score,
            "arms_back": arms_back,
            "head_back": head_back,
            "spine_angle": spine_angle,
            "shoulder_behind_hip": shoulder_behind_hip,
            "mid_shoulder": mid_shoulder,
            "mid_hip": mid_hip,
            "mid_knee": mid_knee
        }
    
    def _is_valid_pose(self, analysis):
        """Check if in valid camel pose"""
        if analysis is None:
            return False
        
        if not analysis["is_kneeling"]:
            return False
        
        if analysis["backbend_angle"] < self.MIN_BACKBEND_ANGLE:
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
        
        # Smooth depth
        self.depth_buffer.append(analysis["depth_score"])
        smoothed_depth = np.median(self.depth_buffer)
        self.current_backbend_depth = smoothed_depth
        
        if self._is_valid_pose(analysis):
            if not self.in_pose:
                self.in_pose = True
                self.pose_start_time = now
                self.current_state = "HOLDING"
            
            self.last_valid_time = now
            self.best_backbend_depth = max(self.best_backbend_depth, smoothed_depth)
            self.current_hold_time = now - self.pose_start_time
            self.best_hold_time = max(self.best_hold_time, self.current_hold_time)
            
            self.last_feedback = self._generate_feedback(analysis)
        else:
            self._check_grace_period(now)
            self.last_feedback = self._get_setup_feedback(analysis)
        
        return {
            "state": self.current_state,
            "hold_time": self.current_hold_time,
            "depth": self.current_backbend_depth,
            "best_depth": self.best_backbend_depth,
            "analysis": analysis,
            "feedback": self.last_feedback
        }
    
    def _handle_no_detection(self, now):
        self._check_grace_period(now)
        return {
            "state": self.current_state,
            "hold_time": self.current_hold_time,
            "depth": self.current_backbend_depth,
            "best_depth": self.best_backbend_depth,
            "analysis": None,
            "feedback": "Position yourself sideways to camera"
        }
    
    def _check_grace_period(self, now):
        if self.in_pose and self.last_valid_time is not None:
            if now - self.last_valid_time > self.GRACE_SECONDS:
                self.total_hold_time += self.current_hold_time
                self.in_pose = False
                self.pose_start_time = None
                self.current_hold_time = 0.0
                self.current_state = "READY"
    
    def _generate_feedback(self, analysis):
        """Generate feedback for active pose"""
        messages = []
        
        if not analysis["hips_over_knees"]:
            messages.append("Push hips forward over knees")
        
        if analysis["depth_score"] >= 80:
            messages.append("Excellent backbend! Breathe deeply")
        elif analysis["depth_score"] >= 50:
            messages.append("Great form! Open your chest more")
        else:
            messages.append("Good start! Lift your chest")
        
        if analysis["arms_back"]:
            messages.append("Hands on heels - beautiful!")
        
        return " | ".join(messages[:2])
    
    def _get_setup_feedback(self, analysis):
        """Feedback for getting into pose"""
        if analysis is None:
            return "Kneel facing sideways to camera"
        
        if not analysis["is_kneeling"]:
            return "Start in a kneeling position"
        
        if analysis["backbend_angle"] < self.MIN_BACKBEND_ANGLE:
            return "Lean back and open your chest"
        
        return "Adjust your form"
    
    def visualize(self, results):
        """Draw visualization"""
        if not hasattr(results[0], "orig_img"):
            return None
        
        frame = results[0].orig_img.copy()
        state_info = self.update_pose_state(results)
        
        h, w = frame.shape[:2]
        
        # Draw skeleton
        if state_info["analysis"] is not None:
            analysis = state_info["analysis"]
            color = (67, 245, 66) if self.in_pose else (66, 135, 245)
            
            # Draw spine line
            pts = [analysis["mid_shoulder"], analysis["mid_hip"], analysis["mid_knee"]]
            for i in range(len(pts) - 1):
                cv2.line(frame, tuple(pts[i].astype(int)),
                        tuple(pts[i + 1].astype(int)), color, 3)
            
            # Draw backbend arc
            hip_pt = tuple(analysis["mid_hip"].astype(int))
            cv2.ellipse(frame, hip_pt, (60, 60), 180, 
                       -90, -90 + analysis["backbend_angle"], (255, 200, 100), 3)
            
            # Keypoints
            for pt in pts:
                cv2.circle(frame, tuple(pt.astype(int)), 8, (255, 255, 255), -1)
                cv2.circle(frame, tuple(pt.astype(int)), 5, color, -1)
            
            # Vertical reference line from hip
            cv2.line(frame, hip_pt, (hip_pt[0], hip_pt[1] - 100), (100, 100, 100), 2)
        
        # UI
        overlay = frame.copy()
        cv2.rectangle(overlay, (20, 20), (260, 150), (40, 40, 40), -1)
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)
        
        secs = int(state_info["hold_time"])
        cv2.putText(frame, f"{secs // 60:02d}:{secs % 60:02d}", (40, 65),
                   cv2.FONT_HERSHEY_DUPLEX, 1.4, (255, 255, 255), 2)
        cv2.putText(frame, "USTRASANA (CAMEL)", (40, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        
        depth = state_info["depth"]
        cv2.putText(frame, f"Backbend: {int(depth)}%", (40, 115),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 200, 255), 1)
        cv2.putText(frame, f"Best: {int(state_info['best_depth'])}%", (40, 135),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
        
        # State
        state_color = (67, 245, 66) if self.in_pose else (100, 100, 100)
        cv2.putText(frame, state_info["state"], (w - 150, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, state_color, 2)
        
        # Depth bar
        bar_width = 200
        bar_x = w - bar_width - 40
        cv2.rectangle(frame, (bar_x, 70), (bar_x + bar_width, 90), (60, 60, 60), -1)
        fill_width = int((depth / 100) * bar_width)
        cv2.rectangle(frame, (bar_x, 70), (bar_x + fill_width, 90), (67, 245, 66), -1)
        cv2.putText(frame, "BACKBEND DEPTH", (bar_x, 65),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
        
        # Feedback
        cv2.rectangle(frame, (20, h - 60), (w - 20, h - 20), (40, 40, 40), -1)
        cv2.putText(frame, state_info["feedback"], (40, h - 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        return frame
    
    def get_current_stats(self):
        return {
            "current_time": self.current_hold_time,
            "best_time": self.best_hold_time,
            "total_time": self.total_hold_time,
            "depth": self.current_backbend_depth,
            "best_depth": self.best_backbend_depth,
            "state": self.current_state,
            "exercise": "ustrasana"
        }
    
    def reset(self):
        self.in_pose = False
        self.pose_start_time = None
        self.current_hold_time = 0.0
        self.best_hold_time = 0.0
        self.total_hold_time = 0.0
        self.current_backbend_depth = 0.0
        self.best_backbend_depth = 0.0
        self.current_state = "READY"
        self.depth_buffer.clear()