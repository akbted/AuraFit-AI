import cv2
import numpy as np
import math
import time
from collections import deque
from ultralytics import YOLO
from app.config.settings import setting
from app.config.device import DEVICE


class NatarajasanaMonitor:
    """
    Natarajasana (Lord of the Dance / Dancer's Pose) Monitor
    
    Key metrics:
    - Balance stability (how much the standing leg moves)
    - Leg lift height (back leg elevation)
    - Arm extension (reaching arm)
    - Back arch depth
    - Overall form quality
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
        
        # Quality metrics
        self.current_leg_height = 0.0
        self.best_leg_height = 0.0
        self.balance_score = 100.0
        self.overall_form_score = 0.0
        
        # Balance tracking
        self.standing_foot_history = deque(maxlen=30)
        self.balance_threshold = 30
        
        # Thresholds
        self.MIN_LEG_LIFT_ANGLE = 25
        self.GOOD_LEG_LIFT_ANGLE = 45
        self.EXCELLENT_LEG_LIFT_ANGLE = 70
        self.ONE_LEG_THRESHOLD = 80
        
        # Grace period
        self.GRACE_SECONDS = 1.5
        self.last_valid_time = None
        
        # Smoothing
        self.height_buffer = deque(maxlen=5)
        self.form_buffer = deque(maxlen=5)
        
        # State
        self.current_state = "READY"
        self.last_feedback = ""
        self.detected_side = None
        
    def process_frame(self, frame):
        """Process frame with pose detection"""
        results = self.model.track(frame, persist=True, device=DEVICE, verbose=False)
        return results
    
    def calculate_angle(self, p1, p2, p3):
        """Calculate angle at p2 between p1-p2-p3"""
        v1 = np.array([p1[0] - p2[0], p1[1] - p2[1]])
        v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
        
        dot = np.dot(v1, v2)
        m1 = np.linalg.norm(v1)
        m2 = np.linalg.norm(v2)
        
        if m1 * m2 == 0:
            return 180
        
        cos_ang = np.clip(dot / (m1 * m2), -1.0, 1.0)
        return math.degrees(math.acos(cos_ang))
    
    def _calculate_angle_from_vertical(self, p1, p2):
        """Calculate angle of line p1-p2 from vertical"""
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        
        # Angle from vertical (0 = straight down, 90 = horizontal)
        angle = math.degrees(math.atan2(abs(dx), abs(dy)))
        return angle
    
    def _detect_standing_side(self, keypoints, conf):
        """Detect which leg is the standing leg"""
        if conf[self.L_ANKLE] < 0.4 or conf[self.R_ANKLE] < 0.4:
            return None
        
        l_ankle_y = keypoints[self.L_ANKLE][1]
        r_ankle_y = keypoints[self.R_ANKLE][1]
        
        # The lower ankle (higher y value) is the standing foot
        if l_ankle_y > r_ankle_y + self.ONE_LEG_THRESHOLD:
            return "left"
        elif r_ankle_y > l_ankle_y + self.ONE_LEG_THRESHOLD:
            return "right"
        
        return None
    
    def _calculate_balance_score(self, standing_ankle):
        """Calculate balance score based on standing foot stability"""
        self.standing_foot_history.append(standing_ankle.copy())
        
        if len(self.standing_foot_history) < 5:
            return 100.0
        
        # Calculate variance in foot position
        positions = np.array(list(self.standing_foot_history))
        variance = np.var(positions, axis=0)
        total_variance = np.sqrt(variance[0] + variance[1])
        
        # Convert to score (0-100)
        score = max(0, 100 - (total_variance * 2))
        return score
    
    def _analyze_pose(self, keypoints, conf, standing_side):
        """Analyze the dancer's pose"""
        if standing_side == "left":
            standing_hip = self.L_HIP
            standing_knee = self.L_KNEE
            standing_ankle = self.L_ANKLE
            lifted_hip = self.R_HIP
            lifted_knee = self.R_KNEE
            lifted_ankle = self.R_ANKLE
            reaching_shoulder = self.R_SHOULDER
            reaching_elbow = self.R_ELBOW
            reaching_wrist = self.R_WRIST
            holding_shoulder = self.L_SHOULDER
            holding_elbow = self.L_ELBOW
            holding_wrist = self.L_WRIST
        else:
            standing_hip = self.R_HIP
            standing_knee = self.R_KNEE
            standing_ankle = self.R_ANKLE
            lifted_hip = self.L_HIP
            lifted_knee = self.L_KNEE
            lifted_ankle = self.L_ANKLE
            reaching_shoulder = self.L_SHOULDER
            reaching_elbow = self.L_ELBOW
            reaching_wrist = self.L_WRIST
            holding_shoulder = self.R_SHOULDER
            holding_elbow = self.R_ELBOW
            holding_wrist = self.R_WRIST
        
        # Check required keypoints
        required = [standing_hip, standing_knee, standing_ankle, 
                   lifted_hip, lifted_knee, lifted_ankle]
        
        if not all(conf[i] > 0.4 for i in required):
            return None
        
        # 1. Calculate leg lift angle (from vertical)
        hip_pos = keypoints[lifted_hip]
        ankle_pos = keypoints[lifted_ankle]
        leg_lift_angle = self._calculate_angle_from_vertical(hip_pos, ankle_pos)
        
        # 2. Standing leg straightness
        standing_leg_angle = self.calculate_angle(
            keypoints[standing_hip],
            keypoints[standing_knee],
            keypoints[standing_ankle]
        )
        standing_leg_straight = abs(180 - standing_leg_angle)
        
        # 3. Lifted knee bend (should be bent to grab foot)
        lifted_knee_angle = self.calculate_angle(
            keypoints[lifted_hip],
            keypoints[lifted_knee],
            keypoints[lifted_ankle]
        )
        
        # 4. Check if arm is reaching up/forward
        arm_reaching = False
        arm_height = 0
        if conf[reaching_wrist] > 0.4 and conf[reaching_shoulder] > 0.4:
            arm_reaching = keypoints[reaching_wrist][1] < keypoints[reaching_shoulder][1]
            # Calculate how high the arm is reaching
            arm_height = keypoints[reaching_shoulder][1] - keypoints[reaching_wrist][1]
        
        # 5. Balance score
        balance = self._calculate_balance_score(keypoints[standing_ankle])
        
        # 6. Calculate overall leg height percentage
        leg_height_pct = min(100, (leg_lift_angle / self.EXCELLENT_LEG_LIFT_ANGLE) * 100)
        
        # 7. Form score calculation
        form_score = 0
        
        # Leg lift contributes 40%
        form_score += min(40, (leg_lift_angle / self.EXCELLENT_LEG_LIFT_ANGLE) * 40)
        
        # Standing leg straightness contributes 20%
        form_score += max(0, 20 - standing_leg_straight)
        
        # Balance contributes 25%
        form_score += (balance / 100) * 25
        
        # Arm reaching contributes 15%
        if arm_reaching:
            form_score += 15
        
        return {
            "leg_lift_angle": leg_lift_angle,
            "leg_height_pct": leg_height_pct,
            "standing_leg_straight": standing_leg_straight,
            "lifted_knee_angle": lifted_knee_angle,
            "arm_reaching": arm_reaching,
            "arm_height": arm_height,
            "balance_score": balance,
            "form_score": form_score,
            "standing_side": standing_side,
            "keypoints": {
                "standing_ankle": keypoints[standing_ankle],
                "standing_knee": keypoints[standing_knee],
                "standing_hip": keypoints[standing_hip],
                "lifted_ankle": keypoints[lifted_ankle],
                "lifted_knee": keypoints[lifted_knee],
                "lifted_hip": keypoints[lifted_hip],
                "reaching_wrist": keypoints[reaching_wrist] if conf[reaching_wrist] > 0.4 else None,
                "reaching_shoulder": keypoints[reaching_shoulder] if conf[reaching_shoulder] > 0.4 else None
            }
        }
    
    def _is_valid_pose(self, analysis):
        """Check if in valid dancer's pose"""
        if analysis is None:
            return False
        
        # Must have minimum leg lift
        if analysis["leg_lift_angle"] < self.MIN_LEG_LIFT_ANGLE:
            return False
        
        # Standing leg should be reasonably straight
        if analysis["standing_leg_straight"] > 30:
            return False
        
        return True
    
    def _generate_feedback(self, analysis):
        """Generate form feedback"""
        if analysis is None:
            return "Get into position - stand on one leg"
        
        feedback = []
        
        # Leg height feedback
        if analysis["leg_lift_angle"] < self.MIN_LEG_LIFT_ANGLE:
            feedback.append("Lift your back leg higher")
        elif analysis["leg_lift_angle"] < self.GOOD_LEG_LIFT_ANGLE:
            feedback.append("Good! Try to lift leg more")
        else:
            feedback.append("Excellent leg height!")
        
        # Standing leg feedback
        if analysis["standing_leg_straight"] > 20:
            feedback.append("Straighten standing leg")
        
        # Arm feedback
        if not analysis["arm_reaching"]:
            feedback.append("Reach forward with arm")
        
        # Balance feedback
        if analysis["balance_score"] < 50:
            feedback.append("Focus on balance")
        elif analysis["balance_score"] > 80:
            feedback.append("Great stability!")
        
        return " | ".join(feedback[:2])
    
    def update_pose_state(self, results):
        """Update pose state based on detection"""
        now = time.time()
        
        # Validate results
        if not hasattr(results[0], "keypoints") or results[0].keypoints is None:
            return self._handle_no_detection(now)
        
        if len(results[0].keypoints) == 0:
            return self._handle_no_detection(now)
        
        if results[0].keypoints.xy is None or len(results[0].keypoints.xy) == 0:
            return self._handle_no_detection(now)
        
        if results[0].keypoints.conf is None or len(results[0].keypoints.conf) == 0:
            return self._handle_no_detection(now)
        
        try:
            keypoints = results[0].keypoints.xy[0].cpu().numpy()
            conf = results[0].keypoints.conf[0].cpu().numpy()
        except (IndexError, AttributeError):
            return self._handle_no_detection(now)
        
        # Detect which side is standing
        standing_side = self._detect_standing_side(keypoints, conf)
        
        if standing_side is None:
            return self._handle_no_detection(now)
        
        self.detected_side = standing_side
        
        # Analyze the pose
        analysis = self._analyze_pose(keypoints, conf, standing_side)
        
        if analysis is None:
            return self._handle_no_detection(now)
        
        # Smooth values
        self.height_buffer.append(analysis["leg_height_pct"])
        self.form_buffer.append(analysis["form_score"])
        
        smoothed_height = np.median(self.height_buffer)
        smoothed_form = np.median(self.form_buffer)
        
        self.current_leg_height = smoothed_height
        self.balance_score = analysis["balance_score"]
        self.overall_form_score = smoothed_form
        
        if self._is_valid_pose(analysis):
            if not self.in_pose:
                self.in_pose = True
                self.pose_start_time = now
                self.current_state = "HOLDING"
            
            self.last_valid_time = now
            self.best_leg_height = max(self.best_leg_height, smoothed_height)
            
            self.current_hold_time = now - self.pose_start_time
            self.best_hold_time = max(self.best_hold_time, self.current_hold_time)
            
            self.last_feedback = self._generate_feedback(analysis)
        else:
            self._check_grace_period(now)
            self.last_feedback = self._generate_feedback(analysis)
        
        return {
            "state": self.current_state,
            "hold_time": self.current_hold_time,
            "leg_height": self.current_leg_height,
            "best_leg_height": self.best_leg_height,
            "balance_score": self.balance_score,
            "form_score": self.overall_form_score,
            "standing_side": standing_side,
            "analysis": analysis,
            "feedback": self.last_feedback
        }
    
    def _handle_no_detection(self, now):
        """Handle frames with no valid detection"""
        self._check_grace_period(now)
        return {
            "state": self.current_state,
            "hold_time": self.current_hold_time,
            "leg_height": self.current_leg_height,
            "best_leg_height": self.best_leg_height,
            "balance_score": self.balance_score,
            "form_score": self.overall_form_score,
            "standing_side": self.detected_side,
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
                self.standing_foot_history.clear()
    
    def visualize(self, results):
        """Draw visualization overlay"""
        if not hasattr(results[0], "orig_img"):
            return None
        
        frame = results[0].orig_img.copy()
        state_info = self.update_pose_state(results)
        
        h, w = frame.shape[:2]
        
        # Draw skeleton
        if state_info["analysis"] is not None:
            kpts = state_info["analysis"]["keypoints"]
            color = (67, 245, 66) if self.in_pose else (66, 135, 245)
            
            # Draw standing leg
            if kpts["standing_ankle"] is not None:
                pts = [kpts["standing_hip"], kpts["standing_knee"], kpts["standing_ankle"]]
                for i in range(len(pts) - 1):
                    p1 = tuple(pts[i].astype(int))
                    p2 = tuple(pts[i + 1].astype(int))
                    cv2.line(frame, p1, p2, color, 3, cv2.LINE_AA)
            
            # Draw lifted leg
            if kpts["lifted_ankle"] is not None:
                pts = [kpts["lifted_hip"], kpts["lifted_knee"], kpts["lifted_ankle"]]
                for i in range(len(pts) - 1):
                    p1 = tuple(pts[i].astype(int))
                    p2 = tuple(pts[i + 1].astype(int))
                    cv2.line(frame, p1, p2, (245, 165, 66), 3, cv2.LINE_AA)
            
            # Draw reaching arm
            if kpts["reaching_wrist"] is not None and kpts["reaching_shoulder"] is not None:
                p1 = tuple(kpts["reaching_shoulder"].astype(int))
                p2 = tuple(kpts["reaching_wrist"].astype(int))
                cv2.line(frame, p1, p2, (245, 66, 245), 3, cv2.LINE_AA)
            
            # Draw keypoints
            for key, pt in kpts.items():
                if pt is not None:
                    cv2.circle(frame, tuple(pt.astype(int)), 8, (255, 255, 255), -1)
                    cv2.circle(frame, tuple(pt.astype(int)), 5, color, -1)
        
        # UI overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (20, 20), (280, 180), (40, 40, 40), -1)
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)
        
        # Timer
        secs = int(state_info["hold_time"])
        cv2.putText(frame, f"{secs // 60:02d}:{secs % 60:02d}", (40, 70),
                   cv2.FONT_HERSHEY_DUPLEX, 1.5, (255, 255, 255), 2)
        cv2.putText(frame, "NATARAJASANA", (40, 95),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        
        # Metrics
        cv2.putText(frame, f"Leg Height: {int(state_info['leg_height'])}%", (40, 120),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 200, 255), 1)
        cv2.putText(frame, f"Balance: {int(state_info['balance_score'])}%", (40, 145),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 255, 150), 1)
        cv2.putText(frame, f"Form: {int(state_info['form_score'])}%", (40, 170),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 150), 1)
        
        # Standing side indicator
        if state_info["standing_side"]:
            side_text = f"Standing: {state_info['standing_side'].upper()}"
            cv2.putText(frame, side_text, (w - 180, 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        # State
        state_color = (67, 245, 66) if self.in_pose else (100, 100, 100)
        cv2.putText(frame, state_info["state"], (w - 150, 80),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, state_color, 2)
        
        # Feedback
        feedback = state_info["feedback"]
        cv2.rectangle(frame, (20, h - 60), (w - 20, h - 20), (40, 40, 40), -1)
        cv2.putText(frame, feedback, (40, h - 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        return frame
    
    def get_current_stats(self):
        """Return current statistics"""
        return {
            "current_time": self.current_hold_time,
            "best_time": self.best_hold_time,
            "total_time": self.total_hold_time,
            "leg_height": self.current_leg_height,
            "best_leg_height": self.best_leg_height,
            "balance_score": self.balance_score,
            "form_score": self.overall_form_score,
            "state": self.current_state,
            "exercise": "natarajasana"
        }
    
    def reset(self):
        """Reset all state"""
        self.in_pose = False
        self.pose_start_time = None
        self.current_hold_time = 0.0
        self.best_hold_time = 0.0
        self.total_hold_time = 0.0
        self.current_leg_height = 0.0
        self.best_leg_height = 0.0
        self.balance_score = 100.0
        self.overall_form_score = 0.0
        self.current_state = "READY"
        self.detected_side = None
        self.standing_foot_history.clear()
        self.height_buffer.clear()
        self.form_buffer.clear()


if __name__ == "__main__":
    monitor = NatarajasanaMonitor()
    monitor.model.to('cpu')  # Use CPU for pose on Apple Silicon
    
    cap = cv2.VideoCapture(0)
    print("Starting Natarajasana monitor. Press 'q' to quit.")

    while True:
        success, frame = cap.read()
        if not success:
            break

        results = monitor.process_frame(frame)
        annotated = monitor.visualize(results)

        if annotated is not None:
            cv2.imshow("Natarajasana Monitor", annotated)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    stats = monitor.get_current_stats()
    print(f"\nBest hold: {stats['best_time']:.1f}s")
    print(f"Best leg height: {stats['best_leg_height']:.1f}%")

    cap.release()
    cv2.destroyAllWindows()