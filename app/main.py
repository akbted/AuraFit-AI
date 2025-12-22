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
from app.config.device import DEVICE

# Active sessions storage
active_sessions: Dict[str, Dict] = {}

# Exercise monitor mapping
EXERCISE_MONITORS = {
    "pushups": PushupMonitor,
    "squats": SquatMonitor,
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"🚀 AuraFit AI started on device: {DEVICE}")
    yield
    # Shutdown
    print("👋 AuraFit AI shutting down...")
    active_sessions.clear()

app = FastAPI(title="AuraFit AI", version="1.0.0", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exercise monitor mapping
EXERCISE_MONITORS = {
    "pushups": PushupMonitor,
    "squats": SquatMonitor,
}


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
                "available": True
            },
            {
                "id": "squats",
                "name": "Squats",
                "description": "Lower body strength",
                "icon": "🦵",
                "available": True
            },
            {
                "id": "situps",
                "name": "Situps",
                "description": "Core strength",
                "icon": "🔥",
                "available": False
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
            # Same exercise, return existing
            return {
                "session_id": session_id,
                "exercise": current_session["exercise"],
                "status": "already_active",
                "message": f"Session already running for {exercise}"
            }
        else:
            # Different exercise, stop old and start new
            print(f"Switching exercise for session {session_id} from {current_session['exercise']} to {exercise}")
            # Cleanup old monitor
            del active_sessions[session_id]
    
    # Initialize monitor
    try:
        monitor_class = EXERCISE_MONITORS[exercise]
        monitor = monitor_class()
        
        active_sessions[session_id] = {
            "exercise": exercise,
            "monitor": monitor,
            "sets": 0,
            "active": True
        }
        
        return {
            "session_id": session_id,
            "exercise": exercise,
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
    
    # Get final count
    if hasattr(monitor, 'pushup_count'):
        total_reps = monitor.pushup_count
    elif hasattr(monitor, 'squat_count'):
        total_reps = monitor.squat_count
    else:
        total_reps = 0
    
    final_stats = {
        "session_id": session_id,
        "exercise": session["exercise"],
        "total_reps": total_reps,
        "sets": session["sets"],
        "status": "completed"
    }
    
    # Cleanup
    del active_sessions[session_id]
    
    return final_stats


@app.get("/api/session/stats")
async def get_session_stats(session_id: str):
    """Get current session stats"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    monitor = session["monitor"]
    
    if hasattr(monitor, 'pushup_count'):
        reps = monitor.pushup_count
    elif hasattr(monitor, 'squat_count'):
        reps = monitor.squat_count
    else:
        reps = 0
    
    return {
        "session_id": session_id,
        "exercise": session["exercise"],
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
    
    # Frame skip counter for performance
    frame_count = 0
    process_every_n_frames = 1  # Process every frame, increase if still slow
    
    try:
        while True:
            # Receive data from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "frame":
                try:
                    frame_count += 1
                    
                    # Decode base64 image
                    frame_data = message["frame"]
                    
                    # Handle data URL format (image/jpeg;base64,...)
                    if "," in frame_data:
                        frame_data = frame_data.split(",")[1]
                    
                    img_bytes = base64.b64decode(frame_data)
                    nparr = np.frombuffer(img_bytes, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    if frame is None:
                        await websocket.send_json({"error": "Failed to decode frame"})
                        continue
                    
                    # Optional: Resize frame for faster processing
                    # Uncomment if still slow:
                    # frame = cv2.resize(frame, (480, 360))
                    
                    # Process frame
                    results = monitor.process_frame(frame)
                    annotated_frame = monitor.visualize(results)
                    
                    # Get current stats
                    if hasattr(monitor, 'pushup_count'):
                        count = monitor.pushup_count
                    elif hasattr(monitor, 'squat_count'):
                        count = monitor.squat_count
                    else:
                        count = 0
                    
                    # Encode annotated frame
                    _, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    frame_base64 = base64.b64encode(buffer).decode('utf-8')
                    
                    # Generate feedback based on state
                    feedback = []
                    if monitor.current_state == "UP":
                        feedback.append("Your form looks great! Keep your back straight.")
                    elif monitor.current_state == "DOWN":
                        feedback.append("Maintain a steady pace.")
                    else:
                        feedback.append("Position yourself in the frame.")
                    
                    # Send response
                    await websocket.send_json({
                        "type": "processed_frame",
                        "frame": f"image/jpeg;base64,{frame_base64}",
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
                # Reset counter for new set
                monitor.reset_counter()
                
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
