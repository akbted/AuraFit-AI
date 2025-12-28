import cv2
import numpy as np
import math
import time
from collections import deque
from ultralytics import YOLO
from app.config.settings import setting
from app.config.device import DEVICE


class PaschimottanasanaMonitor:
    """
    Paschimottanasana (Seated Forward Bend) Monitor
    
    Key metrics:
    - Torso-to-leg angle (how far forward the bend goes)
    - Spine alignment
    - Knee extension (legs should be straight)
    
    Keypoints used:
    - Shoulders, Hips, Knees, Ankles for angle calculation
    - Nose/Head position relative to feet for depth
    """
    
    def __init__(self, model_path=None):
        path = model_path or setting.MODEL_PATH
        self.model = YOLO(path)
        self.model.to(DEVICE)
        
        # COCO Keypoint indices
        self.NOSE = 0
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
        
        # Depth tracking (0-100%)
        self.current_depth = 0.0
        self.best_depth = 0.0
        
        # Thresholds
        self.MIN_FORWARD_ANGLE = 20   # Minimum hip angle to be considered in pose
        self.IDEAL_FORWARD_ANGLE = 45  # Deep forward bend
        self.MAX_KNEE_BEND = 15        # Knees should be nearly straight
        self.MIN_SEATED_RATIO = 0.3    # Body more horizontal than vertical (seated)
        
        # Grace period
        self.GRACE_SECONDS = 1.0
        self.last_valid_time = None
        
        # Smoothing
        self.angle_buffer = deque(maxlen=5)
        self.depth_buffer = deque(maxlen=5)
        
        # State tracking
        self.current_state = "READY"
        self.last_feedback = ""
        
    def process_frame(self, frame):
        """Process frame with pose detection"""
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
    
    def get_midpoint(self, p1, p2):
        """Get midpoint between two points"""
        return np.array([(p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2])
    
    def _analyze_pose(self, keypoints, conf):
        """Analyze the forward bend pose"""
        # Check visibility of required keypoints
        required = [self.L_SHOULDER, self.R_SHOULDER, self.L_HIP, self.R_HIP,
                   self.L_KNEE, self.R_KNEE, self.L_ANKLE, self.R_ANKLE]
        
        if not all(conf[i] > 0.4 for i in required):
            return None
        
        # Calculate midpoints for better stability
        mid_shoulder = self.get_midpoint(keypoints[self.L_SHOULDER], keypoints[self.R_SHOULDER])
        mid_hip = self.get_midpoint(keypoints[self.L_HIP], keypoints[self.R_HIP])
        mid_knee = self.get_midpoint(keypoints[self.L_KNEE], keypoints[self.R_KNEE])
        mid_ankle = self.get_midpoint(keypoints[self.L_ANKLE], keypoints[self.R_ANKLE])
        
        # 1. Hip angle (shoulder-hip-knee) - measures forward bend
        hip_angle = self.calculate_angle(mid_shoulder, mid_hip, mid_knee)
        forward_bend_angle = 180 - hip_angle  # Convert to forward bend measurement
        
        # 2. Knee angle (hip-knee-ankle) - should be ~180 for straight legs
        knee_angle = self.calculate_angle(mid_hip, mid_knee, mid_ankle)
        knee_bend = abs(180 - knee_angle)
        
        # 3. Calculate depth percentage
        # Depth is based on how far the torso goes towards the legs
        max_bend = 90  # Maximum expected forward bend
        depth_percentage = min(100, (forward_bend_angle / max_bend) * 100)
        
        # 4. Check if person is seated (hips lower than shoulders, horizontal orientation)
        is_seated = mid_hip[1] > mid_shoulder[1] - 50  # Hip roughly at or below shoulder level
        
        # 5. Head towards feet (optional depth indicator)
        head_to_feet_dist = None
        if conf[self.NOSE] > 0.4:
            nose = keypoints[self.NOSE]
            head_to_feet_dist = np.linalg.norm(nose - mid_ankle)
        
        return {
            "forward_bend_angle": forward_bend_angle,
            "knee_bend": knee_bend,
            "depth_percentage": depth_percentage,
            "is_seated": is_seated,
            "head_to_feet_dist": head_to_feet_dist,
            "mid_shoulder": mid_shoulder,
            "mid_hip": mid_hip,
            "mid_knee": mid_knee,
            "mid_ankle": mid_ankle
        }
    
    def _is_valid_pose(self, analysis):
        """Check if the pose is valid"""
        if analysis is None:
            return False
        
        # Must be in a forward bend position
        if analysis["forward_bend_angle"] < self.MIN_FORWARD_ANGLE:
            return False
        
        # Must be seated
        if not analysis["is_seated"]:
            return False
        
        return True
    
    def _get_form_quality(self, analysis):
        """
        Rate the form quality (0-100)
        Factors:
        - Forward bend depth (60%)
        - Leg straightness (40%)
        """
        if analysis is None:
            return 0
        
        # Forward bend score (0-60 points)
        bend_score = min(60, (analysis["forward_bend_angle"] / self.IDEAL_FORWARD_ANGLE) * 60)
        
        # Leg straightness score (0-40 points)
        # Perfect is 0 knee bend, loses points as knee bends
        leg_score = max(0, 40 - (analysis["knee_bend"] * 2))
        
        return bend_score + leg_score
    
    def update_pose_state(self, results):
        """Update pose state based on detection results"""
        now = time.time()
        
        if not hasattr(results[0], "keypoints") or results[0].keypoints is None:
            return self._handle_no_detection(now)
        
        if len(results[0].keypoints) == 0:
            return self._handle_no_detection(now)
        
        # Check if keypoints data exists
        if results[0].keypoints.xy is None or len(results[0].keypoints.xy) == 0:
            return self._handle_no_detection(now)
        
        # Check if confidence data exists
        if results[0].keypoints.conf is None:
            return self._handle_no_detection(now)
        
        keypoints = results[0].keypoints.xy[0].cpu().numpy()
        conf = results[0].keypoints.conf[0].cpu().numpy()
        
        analysis = self._analyze_pose(keypoints, conf)
        
        if analysis is None:
            return self._handle_no_detection(now)
        
        # Smooth the depth value
        self.depth_buffer.append(analysis["depth_percentage"])
        smoothed_depth = np.median(self.depth_buffer)
        self.current_depth = smoothed_depth
        
        if self._is_valid_pose(analysis):
            if not self.in_pose:
                self.in_pose = True
                self.pose_start_time = now
                self.current_state = "HOLDING"
            
            self.last_valid_time = now
            self.best_depth = max(self.best_depth, smoothed_depth)
            
            # Update hold time
            self.current_hold_time = now - self.pose_start_time
            self.best_hold_time = max(self.best_hold_time, self.current_hold_time)
            
            # Generate feedback
            quality = self._get_form_quality(analysis)
            self.last_feedback = self._generate_feedback(analysis, quality)
            
        else:
            self._check_grace_period(now)
        
        return {
            "state": self.current_state,
            "hold_time": self.current_hold_time,
            "depth": self.current_depth,
            "best_depth": self.best_depth,
            "analysis": analysis,
            "feedback": self.last_feedback
        }
    
    def _handle_no_detection(self, now):
        """Handle frames with no valid detection"""
        self._check_grace_period(now)
        return {
            "state": self.current_state,
            "hold_time": self.current_hold_time,
            "depth": self.current_depth,
            "best_depth": self.best_depth,
            "analysis": None,
            "feedback": "Position yourself in the frame"
        }
    
    def _check_grace_period(self, now):
        """Check if grace period expired"""
        if self.in_pose and self.last_valid_time is not None:
            if now - self.last_valid_time > self.GRACE_SECONDS:
                self.total_hold_time += self.current_hold_time
                self.in_pose = False
                self.pose_start_time = None
                self.current_hold_time = 0.0
                self.current_state = "READY"
    
    def _generate_feedback(self, analysis, quality):
        """Generate form feedback"""
        feedback = []
        
        if analysis["knee_bend"] > self.MAX_KNEE_BEND:
            feedback.append("Straighten your legs")
        
        if analysis["forward_bend_angle"] < self.MIN_FORWARD_ANGLE:
            feedback.append("Bend forward more from hips")
        elif analysis["forward_bend_angle"] < self.IDEAL_FORWARD_ANGLE:
            feedback.append("Good! Try to reach further")
        else:
            feedback.append("Excellent depth!")
        
        if quality >= 80:
            feedback.append("Great form! Hold steady")
        
        return " | ".join(feedback)
    
    def visualize(self, results):
        """Draw visualization overlay"""
        if not hasattr(results[0], "orig_img"):
            return None
        
        frame = results[0].orig_img.copy()
        state_info = self.update_pose_state(results)
        
        h, w = frame.shape[:2]
        
        # Draw skeleton if available
        if state_info["analysis"] is not None:
            analysis = state_info["analysis"]
            
            # Draw main body line
            pts = [analysis["mid_shoulder"], analysis["mid_hip"], 
                   analysis["mid_knee"], analysis["mid_ankle"]]
            
            color = (67, 245, 66) if self.in_pose else (66, 135, 245)
            
            for i in range(len(pts) - 1):
                p1 = tuple(pts[i].astype(int))
                p2 = tuple(pts[i + 1].astype(int))
                cv2.line(frame, p1, p2, color, 3, cv2.LINE_AA)
            
            # Draw keypoints
            for pt in pts:
                cv2.circle(frame, tuple(pt.astype(int)), 8, (255, 255, 255), -1)
                cv2.circle(frame, tuple(pt.astype(int)), 5, color, -1)
        
        # Draw UI overlay
        # Timer box
        overlay = frame.copy()
        cv2.rectangle(overlay, (20, 20), (250, 140), (40, 40, 40), -1)
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)
        
        # Hold time
        secs = int(state_info["hold_time"])
        cv2.putText(frame, f"{secs // 60:02d}:{secs % 60:02d}", (40, 70),
                   cv2.FONT_HERSHEY_DUPLEX, 1.5, (255, 255, 255), 2)
        cv2.putText(frame, "PASCHIMOTTANASANA", (40, 95),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        
        # Depth indicator
        depth = state_info["depth"]
        cv2.putText(frame, f"Depth: {int(depth)}%", (40, 120),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 200, 255), 1)
        cv2.putText(frame, f"Best: {int(state_info['best_depth'])}%", (150, 120),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
        
        # State indicator
        state_color = (67, 245, 66) if self.in_pose else (100, 100, 100)
        cv2.putText(frame, state_info["state"], (w - 150, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, state_color, 2)
        
        # Feedback bar at bottom
        feedback = state_info["feedback"]
        cv2.rectangle(frame, (20, h - 60), (w - 20, h - 20), (40, 40, 40), -1)
        cv2.putText(frame, feedback, (40, h - 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        # Depth progress bar
        bar_width = 200
        bar_x = w - bar_width - 40
        cv2.rectangle(frame, (bar_x, 70), (bar_x + bar_width, 90), (60, 60, 60), -1)
        fill_width = int((depth / 100) * bar_width)
        bar_color = (67, 245, 66) if depth > 60 else (66, 200, 245)
        cv2.rectangle(frame, (bar_x, 70), (bar_x + fill_width, 90), bar_color, -1)
        cv2.putText(frame, "DEPTH", (bar_x, 65),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
        
        return frame
    
    def get_current_stats(self):
        """Return current statistics"""
        return {
            "current_time": self.current_hold_time,
            "best_time": self.best_hold_time,
            "total_time": self.total_hold_time,
            "current_depth": self.current_depth,
            "best_depth": self.best_depth,
            "state": self.current_state,
            "exercise": "paschimottanasana"
        }
    
    def reset(self):
        """Reset all state"""
        self.in_pose = False
        self.pose_start_time = None
        self.current_hold_time = 0.0
        self.best_hold_time = 0.0
        self.total_hold_time = 0.0
        self.current_depth = 0.0
        self.best_depth = 0.0
        self.current_state = "READY"
        self.depth_buffer.clear()
        self.angle_buffer.clear()

if __name__ == "__main__":
    monitor = PaschimottanasanaMonitor()
    cap = cv2.VideoCapture(0)

    print("Starting Paschimottanasana monitor. Press 'q' to quit.")

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
            cv2.imshow("Paschimottanasana Monitor", annotated)
        else:
            cv2.imshow("Paschimottanasana Monitor", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    # After loop, print stats
    stats = monitor.get_current_stats()
    print("\n" + "=" * 50)
    print("Paschimottanasana session summary")
    print(f"Current hold time : {stats['current_time']:.1f} s")
    print(f"Best single hold  : {stats['best_time']:.1f} s")
    print(f"Total hold time   : {stats['total_time']:.1f} s")
    print(f"Best depth        : {stats['best_depth']:.1f} %")
    print("=" * 50 + "\n")

    cap.release()
    cv2.destroyAllWindows()
