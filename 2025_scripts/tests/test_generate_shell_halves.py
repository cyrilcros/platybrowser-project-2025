import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from generate_shell_halves import HALVES, HALF_NAMES, block_slices, mask_block


class TestMasking(unittest.TestCase):
    def test_sag_left_keeps_x_ge_y(self):
        block = np.ones((1, 4, 5), dtype=np.uint8)
        out = mask_block(block, 0, 0, HALVES["shell_sag_left"], 0)
        for y in range(4):
            for x in range(5):
                self.assertEqual(out[0, y, x], 1 if x >= y else 0)

    def test_sag_right_keeps_x_le_y(self):
        block = np.ones((1, 4, 5), dtype=np.uint8)
        out = mask_block(block, 0, 0, HALVES["shell_sag_right"], 0)
        for y in range(4):
            for x in range(5):
                self.assertEqual(out[0, y, x], 1 if x <= y else 0)

    def test_cor_front_keeps_x_ge_neg_y(self):
        block = np.ones((1, 4, 5), dtype=np.uint8)
        out = mask_block(block, 0, 0, HALVES["shell_cor_front"], 0)
        for y in range(4):
            for x in range(5):
                self.assertEqual(out[0, y, x], 1 if x >= -y else 0)

    def test_cor_back_keeps_x_le_neg_y(self):
        block = np.ones((1, 4, 5), dtype=np.uint8)
        out = mask_block(block, 0, 0, HALVES["shell_cor_back"], 0)
        for y in range(4):
            for x in range(5):
                self.assertEqual(out[0, y, x], 1 if x <= -y else 0)

    def test_global_offset_used_for_block(self):
        # block at global y0=2, x0=5 with all ones; x-y >= 1 everywhere.
        # (local coordinates would give x-y in [-2, 2], so this distinguishes
        # global from block-local masking.)
        block = np.ones((1, 3, 3), dtype=np.uint8)
        out = mask_block(block, y0=2, x0=5, keep=HALVES["shell_sag_left"], offset=0)
        self.assertTrue((out == 1).all())

    def test_offset_shifts_plane(self):
        # keep x - y >= 2; at x=2,y=0 -> 2>=2 kept; at x=0,y=0 -> 0>=2 dropped
        block = np.ones((1, 1, 3), dtype=np.uint8)
        out = mask_block(block, y0=0, x0=0, keep=HALVES["shell_sag_left"], offset=2)
        self.assertEqual(list(out[0, 0]), [0, 0, 1])

    def test_half_names_and_order(self):
        self.assertEqual(
            HALF_NAMES,
            ["shell_sag_left", "shell_sag_right", "shell_cor_front", "shell_cor_back"],
        )

    def test_block_slices_cover_shape(self):
        slices = list(block_slices((3, 4, 5), (2, 2, 2)))
        self.assertEqual(len(slices), 2 * 2 * 3)
        covered = sum(
            (sl[0].stop - sl[0].start)
            * (sl[1].stop - sl[1].start)
            * (sl[2].stop - sl[2].start)
            for sl in slices
        )
        self.assertEqual(covered, 3 * 4 * 5)


if __name__ == "__main__":
    unittest.main()
