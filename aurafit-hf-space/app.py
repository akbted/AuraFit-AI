import os
import cv2
import numpy as np
import base64
import json
import time
from pathlib import Path
from collections import deque
from typing import Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import torch
from ultralytics import YOLO

# Device detection - GPU if available, else CPU
DEVICE = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
print(f"Using device: {DEVICE}")

# Model path - use yolov8n-pose which auto-downloads from ultralytics hub
MODEL_PATH = "yolov8n-pose.pt"

# ============== PUSHUP MONITOR ==============
class PushupMonitor:
    def __init__(self, model_path=MODEL_PATH):
        self.model = YOLO(model_path)
        self.model.to(DEVICE)
        self.pushup_count = 0
        self.current_state = "UNKNOWN"
        self.prev_state = "UNKNOWN"
        self.angle_buffer = deque(maxlen=5)
        
        # Thresholds
        self.UP_ANGLE = 160
        self.DOWN_ANGLE = 90
    
    def process_frame(self, frame):
        results = self.model(frame, verbose=False, device=DEVICE)
        return results
    
    def calculate_angle(self, p1, p2, p3):
        v1 = np.array([p1[0] - p2[0], p1[1] - p2[1]])
        v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
        angle = np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0)))
        return angle
    
    def get_smoothed_angle(self, angle):
        self.angle_buffer.append(angle)
        return np.mean(self.angle_buffer)
    
    def pushup_counter(self, results):
        if not results or len(results) == 0:
            return self.pushup_count, "UNKNOWN"
        
        result = results[0]
        if result.keypoints is None or len(result.keypoints) == 0:
            return self.pushup_count, "UNKNOWN"
        
        keypoints = result.keypoints.xy.cpu().numpy()
        confidence = result.keypoints.conf.cpu().numpy() if result.keypoints.conf is not None else None
        
        if keypoints.shape[0] == 0:
            return self.pushup_count, "UNKNOWN"
        
        kp = keypoints[0]
        conf = confidence[0] if confidence is not None else np.ones(17)
        
        # Use right side: shoulder(6), elbow(8), wrist(10)
        if conf[6] > 0.5 and conf[8] > 0.5 and conf[10] > 0.5:
            shoulder, elbow, wrist = kp[6], kp[8], kp[10]
        # Use left side: shoulder(5), elbow(7), wrist(9)
        elif conf[5] > 0.5 and conf[7] > 0.5 and conf[9] > 0.5:
            shoulder, elbow, wrist = kp[5], kp[7], kp[9]
        else:
            return self.pushup_count, "UNKNOWN"
        
        angle = self.calculate_angle(shoulder, elbow, wrist)
        smoothed = self.get_smoothed_angle(angle)
        
        if smoothed > self.UP_ANGLE:
            self.current_state = "UP"
        elif smoothed < self.DOWN_ANGLE:
            self.current_state = "DOWN"
        
        if self.prev_state == "DOWN" and self.current_state == "UP":
            self.pushup_count += 1
        
        self.prev_state = self.current_state
        return self.pushup_count, self.current_state
    
    def visualize(self, results):
        if not results or len(results) == 0:
            return np.zeros((480, 640, 3), dtype=np.uint8)
        
        frame = results[0].orig_img.copy()
        self.pushup_counter(results)
        
        # Draw skeleton
        if results[0].keypoints is not None:
            kp = results[0].keypoints.xy.cpu().numpy()
            if kp.shape[0] > 0:
                for point in kp[0]:
                    if point[0] > 0 and point[1] > 0:
                        cv2.circle(frame, (int(point[0]), int(point[1])), 4, (0, 255, 0), -1)
        
        return frame
    
    def reset_counter(self):
        self.pushup_count = 0
        self.current_state = "UNKNOWN"
        self.prev_state = "UNKNOWN"
        self.angle_buffer.clear()


# ============== SQUAT MONITOR ==============
class SquatMonitor:
    def __init__(self, model_path=MODEL_PATH):
        self.model = YOLO(model_path)
        self.model.to(DEVICE)
        self.squat_count = 0
        self.current_state = "UNKNOWN"
        self.prev_state = "UNKNOWN"
        self.angle_buffer = deque(maxlen=5)
        
        self.UP_ANGLE = 160
        self.DOWN_ANGLE = 90
    
    def process_frame(self, frame):
        return self.model(frame, verbose=False, device=DEVICE)
    
    def calculate_angle(self, p1, p2, p3):
        v1 = np.array([p1[0] - p2[0], p1[1] - p2[1]])
        v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
        return np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0)))
    
    def get_smoothed_angle(self, angle):
        self.angle_buffer.append(angle)
        return np.mean(self.angle_buffer)
    
    def squat_counter(self, results):
        if not results or len(results) == 0:
            return self.squat_count, "UNKNOWN"
        
        result = results[0]
        if result.keypoints is None:
            return self.squat_count, "UNKNOWN"
        
        kp = result.keypoints.xy.cpu().numpy()
        conf = result.keypoints.conf.cpu().numpy() if result.keypoints.conf is not None else None
        
        if kp.shape[0] == 0:
            return self.squat_count, "UNKNOWN"
        
        kp, conf = kp[0], conf[0] if conf is not None else np.ones(17)
        
        # Right leg: hip(12), knee(14), ankle(16)
        if conf[12] > 0.5 and conf[14] > 0.5 and conf[16] > 0.5:
            hip, knee, ankle = kp[12], kp[14], kp[16]
        # Left leg: hip(11), knee(13), ankle(15)
        elif conf[11] > 0.5 and conf[13] > 0.5 and conf[15] > 0.5:
            hip, knee, ankle = kp[11], kp[13], kp[15]
        else:
            return self.squat_count, "UNKNOWN"
        
        angle = self.get_smoothed_angle(self.calculate_angle(hip, knee, ankle))
        
        if angle > self.UP_ANGLE:
            self.current_state = "UP"
        elif angle < self.DOWN_ANGLE:
            self.current_state = "DOWN"
        
        if self.prev_state == "DOWN" and self.current_state == "UP":
            self.squat_count += 1
        
        self.prev_state = self.current_state
        return self.squat_count, self.current_state
    
    def visualize(self, results):
        if not results or len(results) == 0:
            return np.zeros((480, 640, 3), dtype=np.uint8)
        frame = results[0].orig_img.copy()
        self.squat_counter(results)
        return frame
    
    def reset_counter(self):
        self.squat_count = 0
        self.current_state = "UNKNOWN"
        self.prev_state = "UNKNOWN"
        self.angle_buffer.clear()


# ============== CRUNCH MONITOR ==============
class CrunchMonitor:
    def __init__(self, model_path=MODEL_PATH):
        self.model = YOLO(model_path)
        self.model.to(DEVICE)
        self.crunch_count = 0
        self.current_state = "UNKNOWN"
        self.prev_state = "UNKNOWN"
        self.angle_buffer = deque(maxlen=5)
        
        self.UP_ANGLE = 60
        self.DOWN_ANGLE = 120
    
    def process_frame(self, frame):
        return self.model(frame, verbose=False, device=DEVICE)
    
    def calculate_angle(self, p1, p2, p3):
        v1 = np.array([p1[0] - p2[0], p1[1] - p2[1]])
        v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
        return np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0)))
    
    def get_smoothed_angle(self, angle):
        self.angle_buffer.append(angle)
        return np.mean(self.angle_buffer)
    
    def crunch_counter(self, results):
        if not results or len(results) == 0:
            return self.crunch_count, "UNKNOWN"
        
        result = results[0]
        if result.keypoints is None:
            return self.crunch_count, "UNKNOWN"
        
        kp = result.keypoints.xy.cpu().numpy()
        conf = result.keypoints.conf.cpu().numpy() if result.keypoints.conf is not None else None
        
        if kp.shape[0] == 0:
            return self.crunch_count, "UNKNOWN"
        
        kp, conf = kp[0], conf[0] if conf is not None else np.ones(17)
        
        # shoulder(6), hip(12), knee(14)
        if conf[6] > 0.5 and conf[12] > 0.5 and conf[14] > 0.5:
            shoulder, hip, knee = kp[6], kp[12], kp[14]
        elif conf[5] > 0.5 and conf[11] > 0.5 and conf[13] > 0.5:
            shoulder, hip, knee = kp[5], kp[11], kp[13]
        else:
            return self.crunch_count, "UNKNOWN"
        
        angle = self.get_smoothed_angle(self.calculate_angle(shoulder, hip, knee))
        
        if angle < self.UP_ANGLE:
            self.current_state = "UP"
        elif angle > self.DOWN_ANGLE:
            self.current_state = "DOWN"
        
        if self.prev_state == "UP" and self.current_state == "DOWN":
            self.crunch_count += 1
        
        self.prev_state = self.current_state
        return self.crunch_count, self.current_state
    
    def visualize(self, results):
        if not results or len(results) == 0:
            return np.zeros((480, 640, 3), dtype=np.uint8)
        frame = results[0].orig_img.copy()
        self.crunch_counter(results)
        return frame
    
    def reset_counter(self):
        self.crunch_count = 0
        self.current_state = "UNKNOWN"
        self.prev_state = "UNKNOWN"
        self.angle_buffer.clear()


# ============== LEG RAISE MONITOR ==============
class LegRaiseMonitor:
    def __init__(self, model_path=MODEL_PATH):
        self.model = YOLO(model_path)
        self.model.to(DEVICE)
        self.rep_count = 0
        self.current_state = "UNKNOWN"
        self.prev_state = "UNKNOWN"
        self.height_buffer = deque(maxlen=5)
        
        self.UP_THRESHOLD = 0.6
        self.DOWN_THRESHOLD = 0.2
    
    def process_frame(self, frame):
        return self.model(frame, verbose=False, device=DEVICE)
    
    def leg_raise_counter(self, results):
        if not results or len(results) == 0:
            return self.rep_count, "UNKNOWN"
        
        result = results[0]
        if result.keypoints is None:
            return self.rep_count, "UNKNOWN"
        
        kp = result.keypoints.xy.cpu().numpy()
        conf = result.keypoints.conf.cpu().numpy() if result.keypoints.conf is not None else None
        
        if kp.shape[0] == 0:
            return self.rep_count, "UNKNOWN"
        
        kp, conf = kp[0], conf[0] if conf is not None else np.ones(17)
        
        # ankle(16), hip(12)
        if conf[16] > 0.5 and conf[12] > 0.5:
            ankle, hip = kp[16], kp[12]
        elif conf[15] > 0.5 and conf[11] > 0.5:
            ankle, hip = kp[15], kp[11]
        else:
            return self.rep_count, "UNKNOWN"
        
        # Calculate height ratio (higher ankle = smaller y = UP)
        height_ratio = (hip[1] - ankle[1]) / (hip[1] + 1e-6)
        self.height_buffer.append(height_ratio)
        smoothed = np.mean(self.height_buffer)
        
        if smoothed > self.UP_THRESHOLD:
            self.current_state = "UP"
        elif smoothed < self.DOWN_THRESHOLD:
            self.current_state = "DOWN"
        
        if self.prev_state == "UP" and self.current_state == "DOWN":
            self.rep_count += 1
        
        self.prev_state = self.current_state
        return self.rep_count, self.current_state
    
    def visualize(self, results):
        if not results or len(results) == 0:
            return np.zeros((480, 640, 3), dtype=np.uint8)
        frame = results[0].orig_img.copy()
        self.leg_raise_counter(results)
        return frame
    
    def reset_counter(self):
        self.rep_count = 0
        self.current_state = "UNKNOWN"
        self.prev_state = "UNKNOWN"
        self.height_buffer.clear()


# ============== PLANK MONITOR ==============
class PlankMonitor:
    def __init__(self, model_path=MODEL_PATH):
        self.model = YOLO(model_path)
        self.model.to(DEVICE)
        self.current_state = "REST"
        self.plank_start_time = None
        self.current_time = 0
        self.best_time = 0
        self.total_time = 0
        self.angle_buffer = deque(maxlen=5)
        
        self.MIN_PLANK_ANGLE = 150
        self.MAX_PLANK_ANGLE = 180
    
    def process_frame(self, frame):
        return self.model(frame, verbose=False, device=DEVICE)
    
    def calculate_angle(self, p1, p2, p3):
        v1 = np.array([p1[0] - p2[0], p1[1] - p2[1]])
        v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
        return np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0)))
    
    def update_plank_state(self, results):
        if not results or len(results) == 0:
            self._handle_no_detection()
            return
        
        result = results[0]
        if result.keypoints is None:
            self._handle_no_detection()
            return
        
        kp = result.keypoints.xy.cpu().numpy()
        conf = result.keypoints.conf.cpu().numpy() if result.keypoints.conf is not None else None
        
        if kp.shape[0] == 0:
            self._handle_no_detection()
            return
        
        kp, conf = kp[0], conf[0] if conf is not None else np.ones(17)
        
        # shoulder(6), hip(12), ankle(16)
        if conf[6] > 0.5 and conf[12] > 0.5 and conf[16] > 0.5:
            shoulder, hip, ankle = kp[6], kp[12], kp[16]
        elif conf[5] > 0.5 and conf[11] > 0.5 and conf[15] > 0.5:
            shoulder, hip, ankle = kp[5], kp[11], kp[15]
        else:
            self._handle_no_detection()
            return
        
        angle = self.calculate_angle(shoulder, hip, ankle)
        self.angle_buffer.append(angle)
        smoothed = np.mean(self.angle_buffer)
        
        is_plank = self.MIN_PLANK_ANGLE <= smoothed <= self.MAX_PLANK_ANGLE
        
        if is_plank:
            if self.current_state != "PLANK":
                self.plank_start_time = time.time()
                self.current_state = "PLANK"
            else:
                self.current_time = time.time() - self.plank_start_time
                if self.current_time > self.best_time:
                    self.best_time = self.current_time
        else:
            if self.current_state == "PLANK":
                self.total_time += self.current_time
                self.current_time = 0
            self.current_state = "REST"
    
    def _handle_no_detection(self):
        if self.current_state == "PLANK":
            self.total_time += self.current_time
            self.current_time = 0
        self.current_state = "UNKNOWN"
    
    def visualize(self, results):
        if not results or len(results) == 0:
            return np.zeros((480, 640, 3), dtype=np.uint8)
        frame = results[0].orig_img.copy()
        self.update_plank_state(results)
        return frame
    
    def get_current_stats(self):
        return {
            "state": self.current_state,
            "current_time": round(self.current_time, 1),
            "best_time": round(self.best_time, 1),
            "total_time": round(self.total_time + self.current_time, 1)
        }
    
    def reset_counter(self):
        self.current_state = "REST"
        self.plank_start_time = None
        self.current_time = 0
        self.angle_buffer.clear()


# ============== FASTAPI APP ==============
active_sessions: Dict[str, Dict] = {}

EXERCISE_MONITORS = {
    "pushups": PushupMonitor,
    "squats": SquatMonitor,
    "crunches": CrunchMonitor,
    "leg_raises": LegRaiseMonitor,
    "plank": PlankMonitor,
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🚀 AuraFit AI started on device: {DEVICE}")
    yield
    print("👋 AuraFit AI shutting down...")
    active_sessions.clear()

app = FastAPI(title="AuraFit AI", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (React build)
static_dir = Path("static")
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")

@app.get("/")
async def root():
    """Serve React app"""
    index_path = Path("static/index.html")
    if index_path.exists():
        return FileResponse(index_path)
    return {"service": "AuraFit AI", "status": "active", "device": DEVICE}


@app.get("/api/health")
async def health():
    return {"status": "healthy", "device": DEVICE}


@app.get("/api/exercises")
async def get_exercises():
    return {
        "exercises": [
            {"id": "pushups", "name": "Pushups", "type": "reps", "available": True},
            {"id": "squats", "name": "Squats", "type": "reps", "available": True},
            {"id": "crunches", "name": "Crunches", "type": "reps", "available": True},
            {"id": "leg_raises", "name": "Leg Raises", "type": "reps", "available": True},
            {"id": "plank", "name": "Plank", "type": "timed", "available": True},
        ]
    }


@app.post("/api/session/start")
async def start_session(exercise: str, session_id: str):
    if exercise not in EXERCISE_MONITORS:
        raise HTTPException(status_code=400, detail=f"Exercise '{exercise}' not supported")
    
    if session_id in active_sessions:
        if active_sessions[session_id]["exercise"] == exercise:
            return {"session_id": session_id, "status": "already_active"}
        del active_sessions[session_id]
    
    monitor = EXERCISE_MONITORS[exercise]()
    exercise_type = "timed" if exercise == "plank" else "reps"
    
    active_sessions[session_id] = {
        "exercise": exercise,
        "exercise_type": exercise_type,
        "monitor": monitor,
        "sets": 0,
        "active": True
    }
    
    return {"session_id": session_id, "exercise": exercise, "exercise_type": exercise_type, "status": "started"}


@app.post("/api/session/stop")
async def stop_session(session_id: str):
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions.pop(session_id)
    return {"session_id": session_id, "status": "stopped", "sets": session["sets"]}


def _get_rep_count(monitor):
    for attr in ['pushup_count', 'squat_count', 'crunch_count', 'rep_count']:
        if hasattr(monitor, attr):
            return getattr(monitor, attr)
    return 0


@app.websocket("/ws/exercise/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    
    if session_id not in active_sessions:
        await websocket.send_json({"error": "Session not found"})
        await websocket.close()
        return
    
    session = active_sessions[session_id]
    monitor = session["monitor"]
    exercise_type = session["exercise_type"]
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "frame":
                try:
                    frame_data = message["frame"]
                    if "," in frame_data:
                        frame_data = frame_data.split(",")[1]
                    
                    img_bytes = base64.b64decode(frame_data)
                    nparr = np.frombuffer(img_bytes, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    if frame is None:
                        continue
                    
                    results = monitor.process_frame(frame)
                    annotated = monitor.visualize(results)
                    
                    _, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 75])
                    frame_b64 = base64.b64encode(buffer).decode('utf-8')
                    
                    if exercise_type == "timed":
                        stats = monitor.get_current_stats()
                        await websocket.send_json({
                            "type": "processed_frame",
                            "frame": f"image/jpeg;base64,{frame_b64}",
                            "exercise_type": "timed",
                            "current_time": stats["current_time"],
                            "best_time": stats["best_time"],
                            "state": stats["state"],
                            "sets": session["sets"],
                            "feedback": ["Hold the position!" if stats["state"] == "PLANK" else "Get into position"]
                        })
                    else:
                        count = _get_rep_count(monitor)
                        await websocket.send_json({
                            "type": "processed_frame",
                            "frame": f"image/jpeg;base64,{frame_b64}",
                            "exercise_type": "reps",
                            "reps": count,
                            "state": monitor.current_state,
                            "sets": session["sets"],
                            "feedback": ["Keep going!"]
                        })
                
                except Exception as e:
                    print(f"Frame error: {e}")
            
            elif message.get("type") == "complete_set":
                session["sets"] += 1
                if hasattr(monitor, 'reset_counter'):
                    monitor.reset_counter()
                await websocket.send_json({"type": "set_completed", "sets": session["sets"]})
    
    except WebSocketDisconnect:
        print(f"Disconnected: {session_id}")
    except Exception as e:
        print(f"WS Error: {e}")


# Catch-all for React Router
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Serve React app for all other routes"""
    # Check if it's a static file request
    static_file = Path(f"static/{full_path}")
    if static_file.exists() and static_file.is_file():
        return FileResponse(static_file)
    # Otherwise serve index.html for SPA routing
    index_path = Path("static/index.html")
    if index_path.exists():
        return FileResponse(index_path)
    return {"error": "Not found"}