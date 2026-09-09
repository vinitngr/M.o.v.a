import numpy as np


# Feature vector versions:
#   v1 single hand: 63 normalized points + 3 palm-normal values = 66
#   v2 single hand: v1 + 5 finger-extension values = 71
FEATURE_VERSION = 2
SINGLE_HAND_SHAPE_SIZE = 66
FINGER_PROFILE_SIZE = 5
V2_SINGLE_HAND_SIZE = SINGLE_HAND_SHAPE_SIZE + FINGER_PROFILE_SIZE
V1_TWO_HAND_SIZE = SINGLE_HAND_SHAPE_SIZE * 2 + 3
V2_TWO_HAND_SIZE = V2_SINGLE_HAND_SIZE * 2 + 3

FINGER_TIPS = (4, 8, 12, 16, 20)
FINGER_MCPS = (2, 5, 9, 13, 17)


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


def compute_finger_extension_profile(pts_normalized):
    """
    Returns five scale-invariant values describing thumb/index/middle/ring/pinky
    extension.  Each value is the fingertip-to-wrist distance relative to that
    finger's MCP-to-wrist distance, clamped to [0, 1].

    This is deliberately an additional signal, not a replacement for the
    landmark shape.  It makes gestures that share most of their palm geometry
    distinguishable when they differ by which fingers are raised.
    """
    wrist = pts_normalized[0]
    profile = []
    for tip_index, mcp_index in zip(FINGER_TIPS, FINGER_MCPS):
        tip_distance = np.linalg.norm(pts_normalized[tip_index] - wrist)
        mcp_distance = np.linalg.norm(pts_normalized[mcp_index] - wrist)
        ratio = tip_distance / mcp_distance if mcp_distance > 1e-8 else 0.0
        profile.append(float(np.clip(ratio / 2.0, 0.0, 1.0)))
    return profile


def extract_features(landmarks_3d):
    """
    Full feature extraction for a single hand.
    Returns a flat v2 list of numbers:
      - 63 values: 21 normalized (x,y,z) points
      - 3 values: palm normal vector
      - 5 values: thumb/index/middle/ring/pinky extension profile
    Total: 71 features per hand.
    """
    pts = normalize_landmarks(landmarks_3d)
    palm_normal = compute_palm_normal(pts)
    finger_profile = compute_finger_extension_profile(pts)
    
    # Flatten the 21x3 array into 63 values, then append 3 palm normal values
    features = pts.flatten().tolist() + palm_normal.tolist() + finger_profile
    return features


def extract_two_hand_features(left_landmarks, right_landmarks):
    """
    Full feature extraction for a two-handed gesture.
    Returns a flat list:
      - 71 values: left hand features
      - 71 values: right hand features
      - 3 values: normalized direction vector from left wrist to right wrist
    Total: 145 features.
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


def _v2_shape_and_profile(features):
    """Split a v2 single-hand vector into its old shape and new profile."""
    if len(features) != V2_SINGLE_HAND_SIZE:
        return None, None
    return features[:SINGLE_HAND_SHAPE_SIZE], features[SINGLE_HAND_SHAPE_SIZE:]


def _v2_similarity(live_features, stored_features):
    """Return the weighted v2 similarity as a percentage."""
    live_shape, live_profile = _v2_shape_and_profile(live_features)
    stored_shape, stored_profile = _v2_shape_and_profile(stored_features)
    if live_shape is None or stored_shape is None:
        return None

    shape_score = max(0.0, cosine_similarity(live_shape, stored_shape))
    profile_difference = np.mean(np.abs(np.array(live_profile) - np.array(stored_profile)))
    profile_score = float(np.clip(1.0 - profile_difference, 0.0, 1.0))

    # Keep the proven whole-hand shape dominant, while giving finger identity
    # enough weight to separate one/two/middle-style gestures.
    return (shape_score * 0.60 + profile_score * 0.40) * 100.0


def _legacy_similarity(live_features, stored_features):
    """Compare a v2 live vector with a v1 template for backwards compatibility."""
    if len(stored_features) == SINGLE_HAND_SHAPE_SIZE and len(live_features) == V2_SINGLE_HAND_SIZE:
        return max(0.0, cosine_similarity(live_features[:SINGLE_HAND_SHAPE_SIZE], stored_features))

    if len(stored_features) == V1_TWO_HAND_SIZE and len(live_features) == V2_TWO_HAND_SIZE:
        live_legacy = (live_features[:SINGLE_HAND_SHAPE_SIZE]
                       + live_features[V2_SINGLE_HAND_SIZE:V2_SINGLE_HAND_SIZE + SINGLE_HAND_SHAPE_SIZE]
                       + live_features[-3:])
        return max(0.0, cosine_similarity(live_legacy, stored_features))

    return None


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
        
        if len(live_features) == V2_SINGLE_HAND_SIZE and len(stored_features) == V2_SINGLE_HAND_SIZE:
            score_pct = round(_v2_similarity(live_features, stored_features), 1)
        elif len(live_features) == V2_TWO_HAND_SIZE and len(stored_features) == V2_TWO_HAND_SIZE:
            live_left, live_right, live_relative = (live_features[:V2_SINGLE_HAND_SIZE],
                                                     live_features[V2_SINGLE_HAND_SIZE:V2_SINGLE_HAND_SIZE * 2],
                                                     live_features[-3:])
            stored_left, stored_right, stored_relative = (stored_features[:V2_SINGLE_HAND_SIZE],
                                                          stored_features[V2_SINGLE_HAND_SIZE:V2_SINGLE_HAND_SIZE * 2],
                                                          stored_features[-3:])
            left_score = _v2_similarity(live_left, stored_left)
            right_score = _v2_similarity(live_right, stored_right)
            relative_score = max(0.0, cosine_similarity(live_relative, stored_relative)) * 100.0
            score_pct = round(left_score * 0.4 + right_score * 0.4 + relative_score * 0.2, 1)
        else:
            legacy_score = _legacy_similarity(live_features, stored_features)
            if legacy_score is None:
                continue
            score_pct = round(legacy_score * 100.0, 1)
        
        if name not in scores or score_pct > scores[name]:
            scores[name] = score_pct
    
    # Sort descending
    sorted_scores = dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))
    return sorted_scores
