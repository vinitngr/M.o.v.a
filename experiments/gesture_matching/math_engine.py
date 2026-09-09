import numpy as np

def calculate_angle(v1, v2):
    """
    Returns angle in degrees between two 3D vectors.
    """
    unit_v1 = v1 / np.linalg.norm(v1) if np.linalg.norm(v1) != 0 else v1
    unit_v2 = v2 / np.linalg.norm(v2) if np.linalg.norm(v2) != 0 else v2
    dot_product = np.clip(np.dot(unit_v1, unit_v2), -1.0, 1.0)
    return float(np.degrees(np.arccos(dot_product)))

def extract_features(landmarks_3d):
    """
    Takes a list of 21 (x,y,z) points from MediaPipe.
    Returns a dictionary of invariant features (angles and palm normal).
    """
    pts = np.array(landmarks_3d)
    
    # 1. Palm Normal (Orientation)
    wrist = pts[0]
    index_mcp = pts[5]
    pinky_mcp = pts[17]
    
    v1 = index_mcp - wrist
    v2 = pinky_mcp - wrist
    normal = np.cross(v1, v2)
    normal_length = np.linalg.norm(normal)
    normal = normal / normal_length if normal_length != 0 else normal
    
    # 2. Finger Angles (Handshape)
    # We calculate the bend angles at the joints of each finger.
    angles = []
    # Finger bases: Thumb(1), Index(5), Middle(9), Ring(13), Pinky(17)
    for base in [1, 5, 9, 13, 17]:
        v_a = pts[base+1] - pts[base]
        v_b = pts[base+2] - pts[base+1]
        angles.append(calculate_angle(v_a, v_b))
        
        # All fingers except thumb have an extra highly-mobile joint we should track
        if base != 1: 
            v_c = pts[base+3] - pts[base+2]
            angles.append(calculate_angle(v_b, v_c))
            
    return {
        "angles": angles,
        "palm_normal": [float(n) for n in normal]
    }
