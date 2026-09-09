import unittest

from math_engine import (
    V1_TWO_HAND_SIZE,
    V2_SINGLE_HAND_SIZE,
    V2_TWO_HAND_SIZE,
    score_against_templates,
)


class MathEngineVersion2Tests(unittest.TestCase):
    def test_version_2_single_hand_score_uses_finger_profile(self):
        live = [0.0] * V2_SINGLE_HAND_SIZE
        live[0] = 1.0
        live[-5:] = [1.0, 0.0, 1.0, 0.0, 0.0]

        same = list(live)
        different_fingers = list(live)
        different_fingers[-5:] = [1.0, 1.0, 0.0, 0.0, 0.0]

        scores = score_against_templates(live, [
            {"name": "same", "features": same},
            {"name": "different", "features": different_fingers},
        ])

        self.assertEqual(scores["same"], 100.0)
        self.assertLess(scores["different"], scores["same"])

    def test_v1_template_remains_compatible(self):
        live = [0.0] * V2_SINGLE_HAND_SIZE
        live[0] = 1.0
        legacy = live[:66]

        scores = score_against_templates(live, [
            {"name": "old", "features": legacy},
        ])

        self.assertEqual(scores["old"], 100.0)

    def test_version_2_two_hand_shape_is_supported(self):
        live = [0.0] * V2_TWO_HAND_SIZE
        live[0] = 1.0
        live[V2_SINGLE_HAND_SIZE] = 1.0
        live[-1] = 1.0

        scores = score_against_templates(live, [
            {"name": "two", "features": list(live)},
        ])

        self.assertEqual(scores["two"], 100.0)

    def test_v1_two_hand_template_remains_compatible(self):
        live = [0.0] * V2_TWO_HAND_SIZE
        live[0] = 1.0
        live[V2_SINGLE_HAND_SIZE] = 1.0
        live[-1] = 1.0
        legacy = (live[:66] + live[V2_SINGLE_HAND_SIZE:V2_SINGLE_HAND_SIZE + 66] + live[-3:])

        scores = score_against_templates(live, [
            {"name": "old_two", "features": legacy},
        ])

        self.assertEqual(len(legacy), V1_TWO_HAND_SIZE)
        self.assertEqual(scores["old_two"], 100.0)


if __name__ == "__main__":
    unittest.main()
