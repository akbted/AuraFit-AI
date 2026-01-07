from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import cv2
import numpy as np
import base64
from typing import Dict
import json
from app.services.vision.pushup import PushupMonitor
from app.services.vision.squats import SquatMonitor
from app.services.vision.crunches import CrunchMonitor
from app.services.vision.legraise import LegRaiseMonitor
from app.services.vision.plank import PlankMonitor
from app.config.device import DEVICE

# Active sessions storage
active_sessions: Dict[str, Dict] = {}

# Exercise monitor mapping
EXERCISE_MONITORS = {
    "pushups": PushupMonitor,
    "squats": SquatMonitor,
    "crunches": CrunchMonitor,
    "leg_raises": LegRaiseMonitor,
    "plank": PlankMonitor,
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"AuraFit AI started on device: {DEVICE}")
    yield
    # Shutdown
    print("AuraFit AI shutting down...")
    active_sessions.clear()

app = FastAPI(title="AuraFit AI", version="1.0.0", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check"""
    return {
        "service": "AuraFit AI",
        "status": "active",
        "version": "1.0.0"
    }


@app.get("/api/exercises")
async def get_exercises():
    """Get available exercises"""
    return {
        "exercises": [
            {
                "id": "pushups",
                "name": "Pushups",
                "description": "Upper body strength",
                "icon": "💪",
                "type": "reps",
                "available": True
            },
            {
                "id": "squats",
                "name": "Squats",
                "description": "Lower body strength",
                "icon": "🦵",
                "type": "reps",
                "available": True
            },
            {
                "id": "crunches",
                "name": "Crunches",
                "description": "Core strength",
                "icon": "🔥",
                "type": "reps",
                "available": True
            },
            {
                "id": "leg_raises",
                "name": "Leg Raises",
                "description": "Lower abs",
                "icon": "🦿",
                "type": "reps",
                "available": True
            },
            {
                "id": "plank",
                "name": "Plank",
                "description": "Core endurance",
                "icon": "🧘",
                "type": "timed",
                "available": True
            }
        ]
    }


@app.post("/api/session/start")
async def start_session(exercise: str, session_id: str):
    """Start workout session"""
    if exercise not in EXERCISE_MONITORS:
        raise HTTPException(status_code=400, detail=f"Exercise '{exercise}' not supported")
    
    if session_id in active_sessions:
        current_session = active_sessions[session_id]
        if current_session["exercise"] == exercise:
            return {
                "session_id": session_id,
                "exercise": current_session["exercise"],
                "status": "already_active",
                "message": f"Session already running for {exercise}"
            }
        else:
            print(f"Switching exercise for session {session_id} from {current_session['exercise']} to {exercise}")
            del active_sessions[session_id]
    
    try:
        monitor_class = EXERCISE_MONITORS[exercise]
        monitor = monitor_class()
        
        # Determine exercise type
        exercise_type = "timed" if exercise == "plank" else "reps"
        
        active_sessions[session_id] = {
            "exercise": exercise,
            "exercise_type": exercise_type,
            "monitor": monitor,
            "sets": 0,
            "active": True
        }
        
        return {
            "session_id": session_id,
            "exercise": exercise,
            "exercise_type": exercise_type,
            "status": "started",
            "message": f"Session started for {exercise}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start session: {str(e)}")


@app.post("/api/session/stop")
async def stop_session(session_id: str):
    """Stop workout session"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    monitor = session["monitor"]
    exercise = session["exercise"]
    
    # Get final stats based on exercise type
    if exercise == "plank":
        stats = monitor.get_current_stats()
        final_stats = {
            "session_id": session_id,
            "exercise": exercise,
            "exercise_type": "timed",
            "total_time": stats["total_time"],
            "best_time": stats["best_time"],
            "sets": session["sets"],
            "status": "completed"
        }
    else:
        # Rep-based exercises
        total_reps = _get_rep_count(monitor)
        final_stats = {
            "session_id": session_id,
            "exercise": exercise,
            "exercise_type": "reps",
            "total_reps": total_reps,
            "sets": session["sets"],
            "status": "completed"
        }
    
    del active_sessions[session_id]
    return final_stats


def _get_rep_count(monitor):
    """Get rep count from various monitor types"""
    if hasattr(monitor, 'pushup_count'):
        return monitor.pushup_count
    elif hasattr(monitor, 'squat_count'):
        return monitor.squat_count
    elif hasattr(monitor, 'crunch_count'):
        return monitor.crunch_count
    elif hasattr(monitor, 'rep_count'):
        return monitor.rep_count
    return 0


@app.get("/api/session/stats")
async def get_session_stats(session_id: str):
    """Get current session stats"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    monitor = session["monitor"]
    exercise = session["exercise"]
    
    if exercise == "plank":
        stats = monitor.get_current_stats()
        return {
            "session_id": session_id,
            "exercise": exercise,
            "exercise_type": "timed",
            "current_time": stats["current_time"],
            "best_time": stats["best_time"],
            "total_time": stats["total_time"],
            "state": stats["state"],
            "sets": session["sets"],
            "active": session["active"]
        }
    else:
        reps = _get_rep_count(monitor)
        return {
            "session_id": session_id,
            "exercise": exercise,
            "exercise_type": "reps",
            "reps": reps,
            "sets": session["sets"],
            "state": monitor.current_state,
            "active": session["active"]
        }


@app.websocket("/ws/exercise/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket for real-time video processing"""
    await websocket.accept()
    print(f"WebSocket connected: {session_id}")
    
    if session_id not in active_sessions:
        await websocket.send_json({"error": "Session not found. Please start a session first."})
        await websocket.close()
        return
    
    session = active_sessions[session_id]
    monitor = session["monitor"]
    exercise = session["exercise"]
    exercise_type = session.get("exercise_type", "reps")
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "frame":
                try:
                    # Decode base64 image
                    frame_data = message["frame"]
                    if "," in frame_data:
                        frame_data = frame_data.split(",")[1]
                    
                    img_bytes = base64.b64decode(frame_data)
                    nparr = np.frombuffer(img_bytes, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    if frame is None:
                        await websocket.send_json({"error": "Failed to decode frame"})
                        continue
                    
                    # Process frame
                    results = monitor.process_frame(frame)
                    annotated_frame = monitor.visualize(results)
                    
                    # Encode annotated frame
                    _, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    frame_base64 = base64.b64encode(buffer).decode('utf-8')
                    
                    # Build response based on exercise type
                    if exercise_type == "timed":
                        # Plank - timed exercise
                        stats = monitor.get_current_stats()
                        feedback = _get_plank_feedback(stats["state"])
                        
                        await websocket.send_json({
                            "type": "processed_frame",
                            "frame": f"image/jpeg;base64,{frame_base64}",
                            "exercise_type": "timed",
                            "current_time": stats["current_time"],
                            "best_time": stats["best_time"],
                            "total_time": stats["total_time"],
                            "sets": session["sets"],
                            "state": stats["state"],
                            "feedback": feedback
                        })
                    else:
                        # Rep-based exercises
                        count = _get_rep_count(monitor)
                        feedback = _get_rep_feedback(monitor.current_state, exercise)
                        
                        await websocket.send_json({
                            "type": "processed_frame",
                            "frame": f"image/jpeg;base64,{frame_base64}",
                            "exercise_type": "reps",
                            "reps": count,
                            "sets": session["sets"],
                            "state": monitor.current_state,
                            "feedback": feedback
                        })
                
                except Exception as e:
                    print(f"Frame processing error: {e}")
                    await websocket.send_json({"error": f"Frame processing failed: {str(e)}"})
            
            elif message.get("type") == "complete_set":
                session["sets"] += 1
                
                # Reset counter based on exercise type
                if hasattr(monitor, 'reset_counter'):
                    monitor.reset_counter()
                elif hasattr(monitor, 'reset'):
                    monitor.reset()
                
                await websocket.send_json({
                    "type": "set_completed",
                    "sets": session["sets"],
                    "message": f"Set {session['sets']} completed!"
                })
            
            elif message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        print(f"WebSocket disconnected: {session_id}")
        session["active"] = False
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass
    finally:
        print(f"WebSocket closed: {session_id}")


def _get_rep_feedback(state: str, exercise: str) -> list:
    """Generate feedback for rep-based exercises"""
    exercise_tips = {
        "pushups": {
            "UP": "Great form! Keep your core engaged.",
            "DOWN": "Control the descent, chest to floor.",
        },
        "squats": {
            "UP": "Drive through your heels!",
            "DOWN": "Keep your knees over toes.",
        },
        "crunches": {
            "UP": "Squeeze your abs at the top!",
            "DOWN": "Control the lowering motion.",
        },
        "leg_raises": {
            "UP": "Keep your legs straight!",
            "DOWN": "Don't let your feet touch the ground.",
        }
    }
    
    tips = exercise_tips.get(exercise, {"UP": "Good!", "DOWN": "Keep going!"})
    
    if state == "UP":
        return [tips["UP"]]
    elif state == "DOWN":
        return [tips["DOWN"]]
    else:
        return ["Position yourself in the frame."]


def _get_plank_feedback(state: str) -> list:
    """Generate feedback for plank"""
    if state == "PLANK":
        return ["Great form! Keep holding!"]
    elif state == "REST":
        return ["Get into plank position - hands under shoulders."]
    else:
        return ["Position yourself in the frame."]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
