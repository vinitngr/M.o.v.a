import numpy as np


def normalize_landmarks(landmarks_3d):
    """
    Takes 21 raw (x,y,z) points from MediaPipe and normalizes them:
    1. Translation Invariance: Center everything on the wrist (point 0 becomes origin).
    2. Scale Invariance: Divide by max distance from wrist so hand size = 1.0.
    
    Returns the normalized 21x3 numpy array.
    """
    pts = np.array(landmarks_3d, dtype=np.float64)
    
    # Center on wrist
    wrist = pts[0].copy()
    pts = pts - wrist
    
    # Scale by max distance from wrist
    max_dist = np.max(np.linalg.norm(pts, axis=1))
    if max_dist > 0:
        pts = pts / max_dist
    
    return pts


def compute_palm_normal(pts_normalized):
    """
    Computes the unit normal vector of the palm plane using:
    Wrist(0), Index MCP(5), Pinky MCP(17).
    """
    v1 = pts_normalized[5] - pts_normalized[0]
    v2 = pts_normalized[17] - pts_normalized[0]
    normal = np.cross(v1, v2)
    norm_len = np.linalg.norm(normal)
    if norm_len > 0:
        normal = normal / norm_len
    return normal


def extract_features(landmarks_3d):
    """
    Full feature extraction for a single hand.
    Returns a flat list of numbers:
      - 63 values: 21 normalized (x,y,z) points
      - 3 values: palm normal vector
    Total: 66 features per hand.
    """
    pts = normalize_landmarks(landmarks_3d)
    palm_normal = compute_palm_normal(pts)
    
    # Flatten the 21x3 array into 63 values, then append 3 palm normal values
    features = pts.flatten().tolist() + palm_normal.tolist()
    return features


def extract_two_hand_features(left_landmarks, right_landmarks):
    """
    Full feature extraction for a two-handed gesture.
    Returns a flat list:
      - 66 values: left hand features
      - 66 values: right hand features
      - 3 values: normalized direction vector from left wrist to right wrist
    Total: 135 features.
    """
    left_features = extract_features(left_landmarks)
    right_features = extract_features(right_landmarks)
    
    # Relative spatial vector between wrists (before normalization)
    left_wrist = np.array(left_landmarks[0])
    right_wrist = np.array(right_landmarks[0])
    relative_vec = right_wrist - left_wrist
    rel_norm = np.linalg.norm(relative_vec)
    if rel_norm > 0:
        relative_vec = relative_vec / rel_norm
    
    return left_features + right_features + relative_vec.tolist()


def average_feature_sets(feature_sets):
    """
    Takes a list of feature vectors (from multiple captures of the same gesture)
    and returns a single averaged feature vector. This smooths out noise and
    minor hand tremors across captures.
    """
    if not feature_sets:
        return []
    arr = np.array(feature_sets)
    return np.mean(arr, axis=0).tolist()


def cosine_similarity(vec_a, vec_b):
    """
    Returns cosine similarity between two vectors.
    Range: [-1, 1]. 1 = identical, 0 = orthogonal, -1 = opposite.
    """
    a = np.array(vec_a)
    b = np.array(vec_b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def score_against_templates(live_features, stored_gestures):
    """
    Compares a live feature vector against all stored gesture templates.
    Returns a dict of {gesture_name: best_score_percentage} sorted descending.
    
    For gestures with multiple templates, the highest score (best match) is kept.
    """
    scores = {}
    for gesture in stored_gestures:
        name = gesture["name"]
        stored_features = gesture["features"]
        
        # Ensure vectors are the same length (single vs two-hand)
        if len(live_features) != len(stored_features):
            continue
        
        similarity = cosine_similarity(live_features, stored_features)
        
        # Convert from [-1, 1] to [0, 100] percentage
        score_pct = round(max(0.0, similarity) * 100, 1)
        
        if name not in scores or score_pct > scores[name]:
            scores[name] = score_pct
    
    # Sort descending
    sorted_scores = dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))
    return sorted_scores
