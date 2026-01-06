import cv2
import numpy as np
import math
from collections import defaultdict
from ultralytics import YOLO
from app.config.settings import setting

class CompetitionMonitor:
    def __init__(self, exercise_type="pushup", model_path=None):
        """
        exercise_type: "pushup" or "squat"
        """
        path = model_path or setting.MODEL_PATH
        self.model = YOLO(path)
        self.exercise_type = exercise_type.lower()
        
        # Per-person state: keyed by track_id
        self.person_state = defaultdict(lambda: {
            "count": 0,
            "state": "UNKNOWN"
        })
        
        # Keypoint indices (COCO/YOLO pose)
        # Arms
        self.LEFT_SHOULDER = 5
        self.RIGHT_SHOULDER = 6
        self.LEFT_ELBOW = 7
        self.RIGHT_ELBOW = 8
        self.LEFT_WRIST = 9
        self.RIGHT_WRIST = 10
        
        # Legs
        self.LEFT_HIP = 11
        self.RIGHT_HIP = 12
        self.LEFT_KNEE = 13
        self.RIGHT_KNEE = 14
        self.LEFT_ANKLE = 15
        self.RIGHT_ANKLE = 16
        
        # Thresholds
        if self.exercise_type == "pushup":
            self.DOWN_ANGLE = 100
            self.UP_ANGLE = 150
        else:  # squat
            self.DOWN_ANGLE = 100
            self.UP_ANGLE = 160

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
        """Draw rounded rectangle"""
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

    def _get_best_angle_and_side(self, keypoints, confidence):
        """Get angle based on exercise type (pushup or squat)"""
        if self.exercise_type == "pushup":
            right_idxs = [self.RIGHT_SHOULDER, self.RIGHT_ELBOW, self.RIGHT_WRIST]
            left_idxs = [self.LEFT_SHOULDER, self.LEFT_ELBOW, self.LEFT_WRIST]
        else:  # squat
            right_idxs = [self.RIGHT_HIP, self.RIGHT_KNEE, self.RIGHT_ANKLE]
            left_idxs = [self.LEFT_HIP, self.LEFT_KNEE, self.LEFT_ANKLE]
        
        right_valid = [i for i in right_idxs if confidence[i] > 0.5]
        left_valid = [i for i in left_idxs if confidence[i] > 0.5]
        
        used_side = None
        if len(right_valid) == 3 and len(left_valid) < 3:
            used_side = "right"
        elif len(left_valid) == 3 and len(right_valid) < 3:
            used_side = "left"
        elif len(right_valid) == 3 and len(left_valid) == 3:
            used_side = "right"
        else:
            return None, None
        
        if used_side == "right":
            angle = self.calculate_angle(keypoints[right_idxs[0]], 
                                        keypoints[right_idxs[1]], 
                                        keypoints[right_idxs[2]])
        else:
            angle = self.calculate_angle(keypoints[left_idxs[0]], 
                                        keypoints[left_idxs[1]], 
                                        keypoints[left_idxs[2]])
        
        return angle, used_side

    def update_person_state(self, track_id, keypoints, confidence):
        """Update one person's state and count"""
        angle, used_side = self._get_best_angle_and_side(keypoints, confidence)
        if angle is None or used_side is None:
            return "UNKNOWN", 0, None
        
        prev_state = self.person_state[track_id]["state"]
        
        # Determine new state
        if angle < self.DOWN_ANGLE:
            new_state = "DOWN"
        elif angle > self.UP_ANGLE:
            new_state = "UP"
        else:
            new_state = prev_state if prev_state != "UNKNOWN" else "UNKNOWN"
        
        # Count on DOWN -> UP
        if prev_state == "DOWN" and new_state == "UP":
            self.person_state[track_id]["count"] += 1
            print(f"ID {track_id} ✓ {self.exercise_type.upper()} #{self.person_state[track_id]['count']} | Angle: {int(angle)}°")
        
        self.person_state[track_id]["state"] = new_state
        return new_state, angle, used_side

    def draw_skeleton(self, frame, keypoints, confidence, used_side, state, color):
        """Draw skeleton for person"""
        if self.exercise_type == "pushup":
            if used_side == "right":
                indices = [self.RIGHT_SHOULDER, self.RIGHT_ELBOW, self.RIGHT_WRIST]
            else:
                indices = [self.LEFT_SHOULDER, self.LEFT_ELBOW, self.LEFT_WRIST]
        else:  # squat
            if used_side == "right":
                indices = [self.RIGHT_HIP, self.RIGHT_KNEE, self.RIGHT_ANKLE]
            else:
                indices = [self.LEFT_HIP, self.LEFT_KNEE, self.LEFT_ANKLE]
        
        connections = [(indices[0], indices[1]), (indices[1], indices[2])]
        
        # Draw lines
        base_color = {
            "DOWN": (66, 135, 245),
            "UP": (67, 245, 66),
            "UNKNOWN": (150, 150, 150),
        }.get(state, (150, 150, 150))
        
        for i1, i2 in connections:
            if confidence[i1] > 0.5 and confidence[i2] > 0.5:
                p1 = tuple(keypoints[i1].astype(int))
                p2 = tuple(keypoints[i2].astype(int))
                cv2.line(frame, p1, p2, color, 4, cv2.LINE_AA)
        
        # Draw keypoints
        for idx in indices:
            if confidence[idx] > 0.5:
                p = tuple(keypoints[idx].astype(int))
                cv2.circle(frame, p, 10, (255, 255, 255), -1, cv2.LINE_AA)
                cv2.circle(frame, p, 6, color, -1, cv2.LINE_AA)
        
        return frame

    def draw_competition_overlay(self, frame):
        """Draw static overlay boxes for Player 1 and Player 2"""
        h, w = frame.shape[:2]
        
        # Get sorted players by track_id
        sorted_players = sorted(self.person_state.items(), key=lambda x: x[0])
        
        # Player colors
        player_colors = [
            (67, 245, 66),   # Player 1 - Green
            (255, 165, 0),   # Player 2 - Orange
        ]
        
        # Draw Player 1 box (left)
        if len(sorted_players) >= 1:
            player_id, player_data = sorted_players[0]
            overlay = frame.copy()
            self.draw_rounded_rectangle(overlay, (20, 20), (220, 140), (40, 40, 40), filled=True, radius=15)
            cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
            
            # Count
            cv2.putText(frame, str(player_data['count']), (40, 85), 
                       cv2.FONT_HERSHEY_DUPLEX, 2.0, (255, 255, 255), 3, cv2.LINE_AA)
            # Label
            cv2.putText(frame, "PLAYER 1", (40, 110), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)
            # State
            state_color = {
                "DOWN": (66, 135, 245),
                "UP": (67, 245, 66),
                "UNKNOWN": (150, 150, 150)
            }.get(player_data['state'], (150, 150, 150))
            cv2.putText(frame, player_data['state'], (40, 130), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, state_color, 1, cv2.LINE_AA)
        
        # Draw Player 2 box (right)
        if len(sorted_players) >= 2:
            player_id, player_data = sorted_players[1]
            overlay2 = frame.copy()
            self.draw_rounded_rectangle(overlay2, (w - 220, 20), (w - 20, 140), (40, 40, 40), 
                                       filled=True, radius=15)
            cv2.addWeighted(overlay2, 0.85, frame, 0.15, 0, frame)
            
            # Count
            cv2.putText(frame, str(player_data['count']), (w - 200, 85), 
                       cv2.FONT_HERSHEY_DUPLEX, 2.0, (255, 255, 255), 3, cv2.LINE_AA)
            # Label
            cv2.putText(frame, "PLAYER 2", (w - 200, 110), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)
            # State
            state_color = {
                "DOWN": (66, 135, 245),
                "UP": (67, 245, 66),
                "UNKNOWN": (150, 150, 150)
            }.get(player_data['state'], (150, 150, 150))
            cv2.putText(frame, player_data['state'], (w - 200, 130), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, state_color, 1, cv2.LINE_AA)
        
        # Draw winner banner if counts are different and both > 0
        if len(sorted_players) == 2:
            p1_count = sorted_players[0][1]['count']
            p2_count = sorted_players[1][1]['count']
            if p1_count > 0 or p2_count > 0:
                if p1_count > p2_count:
                    leader_text = "PLAYER 1 LEADS!"
                    leader_color = player_colors[0]
                elif p2_count > p1_count:
                    leader_text = "PLAYER 2 LEADS!"
                    leader_color = player_colors[1]
                else:
                    leader_text = "TIE!"
                    leader_color = (255, 255, 255)
                
                # Center banner
                overlay3 = frame.copy()
                self.draw_rounded_rectangle(overlay3, (w//2 - 150, 20), (w//2 + 150, 70), 
                                           (40, 40, 40), filled=True, radius=12)
                cv2.addWeighted(overlay3, 0.85, frame, 0.15, 0, frame)
                
                text_size = cv2.getTextSize(leader_text, cv2.FONT_HERSHEY_DUPLEX, 0.7, 2)[0]
                text_x = w//2 - text_size[0]//2
                cv2.putText(frame, leader_text, (text_x, 50), 
                           cv2.FONT_HERSHEY_DUPLEX, 0.7, leader_color, 2, cv2.LINE_AA)
        
        return frame

    def visualize(self, results):
        """Visualize all persons with tracking"""
        if not hasattr(results[0], "orig_img"):
            return None
        
        frame = results[0].orig_img.copy()
        
        # Check if tracking is working
        if not hasattr(results[0].boxes, "id") or results[0].boxes.id is None:
            cv2.putText(frame, "Waiting for players...", (20, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            return frame
        
        track_ids = results[0].boxes.id.cpu().numpy().astype(int)
        
        # Assign player colors based on sorted track_id
        sorted_ids = sorted(track_ids)
        
        # Build color map safely
        player_colors = {}
        color_palette = [
            (67, 245, 66),   # Player 1 - Green
            (255, 165, 0),   # Player 2 - Orange
            (245, 66, 245),  # Player 3 - Magenta
            (66, 135, 245),  # Player 4 - Blue
        ]
        for i, pid in enumerate(sorted_ids):
            player_colors[pid] = color_palette[i % len(color_palette)]
        
        for idx, track_id in enumerate(track_ids):
            if not hasattr(results[0], "keypoints") or len(results[0].keypoints) <= idx:
                continue
            
            keypoints = results[0].keypoints.xy[idx].cpu().numpy()
            confidence = results[0].keypoints.conf[idx].cpu().numpy()
            
            state, angle, used_side = self.update_person_state(track_id, keypoints, confidence)
            
            # Use player color
            color = player_colors.get(track_id, (150, 150, 150))
            
            if used_side is not None:
                frame = self.draw_skeleton(frame, keypoints, confidence, used_side, state, color)
        
        # Draw static overlay
        frame = self.draw_competition_overlay(frame)
        
        return frame


if __name__ == "__main__":
    monitor = CompetitionMonitor(exercise_type="pushup")
    cap = cv2.VideoCapture(0)
    
    print(f"Starting {monitor.exercise_type.upper()} competition...")
    print(f"Thresholds: DOWN<{monitor.DOWN_ANGLE}°, UP>{monitor.UP_ANGLE}°")
    
    while True:
        success, frame = cap.read()
        if not success:
            break
        
        results = monitor.process_frame(frame)
        annotated = monitor.visualize(results)
        if annotated is not None:
            cv2.imshow(f"{monitor.exercise_type.upper()} Competition", annotated)
        
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    
    print("\n" + "="*50)
    print("FINAL RESULTS")
    print("="*50)
    if monitor.person_state:
        sorted_players = sorted(monitor.person_state.items(), 
                               key=lambda x: x[1]["count"], reverse=True)
        for rank, (player_id, data) in enumerate(sorted_players, 1):
            print(f"Rank #{rank} - ID {player_id}: {data['count']} {monitor.exercise_type}s")
    else:
        print(f"No players tracked")
    print("="*50 + "\n")
    
    cap.release()
    cv2.destroyAllWindows()
