import math
from ultralytics import YOLO

# Load YOLOv8 pose model
def load_model(model_path='yolov8s-pose.pt'):
    return YOLO(model_path)

# Extracts x, y coordinates of a specific keypoint if detected
def get_keypoint_coordinates(results, keypoint_index):
    if results[0].keypoints and results[0].keypoints.xy.shape[1] > keypoint_index:
        kp_data = results[0].keypoints.xy[0][keypoint_index]
        if kp_data.numel() >= 2:
            return int(kp_data[0].item()), int(kp_data[1].item())
    return None, None

# Calculates the angle between three points (p2 is the vertex)
def calculate_angle(p1, p2, p3):
    if p1 is None or p2 is None or p3 is None:
        return None
    v1 = (p1[0] - p2[0], p1[1] - p2[1])
    v2 = (p3[0] - p2[0], p3[1] - p2[1])
    dot_product = v1[0]*v2[0] + v1[1]*v2[1]
    mag_v1 = math.sqrt(v1[0]**2 + v1[1]**2)
    mag_v2 = math.sqrt(v2[0]**2 + v2[1]**2)
    if mag_v1 * mag_v2 == 0:
        return None
    angle_rad = math.acos(dot_product / (mag_v1 * mag_v2))
    angle_deg = math.degrees(angle_rad)
    return angle_deg
