import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import z5py
from scipy.spatial import ConvexHull

from clean_shell_left import (
    NAME,
    clean_half,
    depth_of,
    hull_planes,
)


def make_half_n5(path: Path, shape=(4, 4, 4), value=255,
                 levels=(1, 2)) -> Path:
    """Tiny uint8 N5 with shell-like group attributes and 1-2 levels."""
    with z5py.File(str(path), "a") as f:
        setup = f.create_group("setup0")
        setup.attrs["dataType"] = "uint8"
        setup.attrs["downsamplingFactors"] = [[d, d, d] for d in levels]
        tp = setup.create_group("timepoint0")
        tp.attrs["multiScale"] = True
        tp.attrs["resolution"] = [0.32, 0.32, 0.4]
        for i, d in enumerate(levels):
            lvl_shape = tuple((s + d - 1) // d for s in shape)
            ds = tp.create_dataset(
                f"s{i}", shape=lvl_shape, chunks=(2, 2, 2),
                dtype="uint8", compression="gzip", level=1, fillvalue=0,
            )
            ds.attrs["downsamplingFactors"] = [d, d, d]
            ds[:] = value
    return path


def cube_hull(lo=0.0, hi=10.0):
    """Plane equations (A, b) of the axis-aligned cube [lo, hi]^3."""
    corners = np.array(
        [[x, y, z] for x in (lo, hi) for y in (lo, hi) for z in (lo, hi)],
        dtype=np.float64,
    )
    eq = ConvexHull(corners).equations
    return eq[:, :3], eq[:, 3]


class TestDepthOf(unittest.TestCase):
    def test_depth_of_unit_cube(self):
        A, b = cube_hull(0.0, 10.0)
        center = depth_of(np.array([[5.0, 5.0, 5.0]]), A, b)[0]
        corner = depth_of(np.array([[0.0, 0.0, 0.0]]), A, b)[0]
        self.assertAlmostEqual(center, 5.0, places=6)
        self.assertAlmostEqual(corner, 0.0, places=6)

    def test_depth_is_positive_inside_and_negative_outside(self):
        A, b = cube_hull(0.0, 10.0)
        inside = depth_of(np.array([[2.0, 5.0, 5.0]]), A, b)[0]
        outside = depth_of(np.array([[11.0, 5.0, 5.0]]), A, b)[0]
        self.assertGreater(inside, 0.0)
        self.assertLess(outside, 0.0)


class TestCleanHalf(unittest.TestCase):
    def test_clean_half_removes_deep_voxels(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            half = make_half_n5(tmp / "shell_left.n5", shape=(4, 4, 4),
                                value=255, levels=(1,))
            out_path = tmp / "shell_left_clean.n5"
            # Hull enclosing the whole 4^3 block, from -0.5 to 3.5.
            A, b = cube_hull(-0.5, 3.5)
            clean_half(half, out_path, A, b, threshold=1.0)

            with z5py.File(str(out_path), "r") as f:
                out = f["setup0/timepoint0/s0"][:]

            # The inner 2x2x2 cube (depth 1.5) is removed, every voxel on the
            # block surface (depth 0.5) is kept.
            self.assertEqual(int((out > 0).sum()), 4 ** 3 - 2 ** 3)
            self.assertEqual(int(out[1:3, 1:3, 1:3].sum()), 0)
            for face in (out[0], out[-1], out[:, 0], out[:, -1],
                         out[:, :, 0], out[:, :, -1]):
                self.assertTrue((face == 255).all())
            self.assertTrue(((out > 0) == (out == 255)).all())

    def test_clean_half_keeps_attrs(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            half = make_half_n5(tmp / "shell_left.n5", shape=(4, 4, 4),
                                value=255, levels=(1, 2))
            out_path = tmp / "shell_left_clean.n5"
            A, b = cube_hull(-0.5, 3.5)
            clean_half(half, out_path, A, b, threshold=100.0)

            with z5py.File(str(half), "r") as sf, \
                    z5py.File(str(out_path), "r") as of:
                self.assertEqual(sorted(of["setup0/timepoint0"].keys()),
                                 sorted(sf["setup0/timepoint0"].keys()))
                self.assertEqual(dict(of["setup0"].attrs)["dataType"], "uint8")
                self.assertEqual(
                    list(dict(of["setup0/timepoint0"].attrs)["resolution"]),
                    [0.32, 0.32, 0.4],
                )
                self.assertIs(
                    dict(of["setup0/timepoint0"].attrs)["multiScale"], True)
                for name in ("s0", "s1"):
                    sds = sf["setup0/timepoint0"][name]
                    ods = of["setup0/timepoint0"][name]
                    self.assertEqual(tuple(ods.shape), tuple(sds.shape))
                    self.assertEqual(tuple(ods.chunks), tuple(sds.chunks))
                    self.assertEqual(ods.dtype, np.dtype("uint8"))
                    self.assertEqual(ods.compression, "gzip")
                    self.assertEqual(
                        list(dict(ods.attrs)["downsamplingFactors"]),
                        list(dict(sds.attrs)["downsamplingFactors"]),
                    )
                    np.testing.assert_array_equal(ods[:], sds[:])

    def test_hull_planes_from_mask(self):
        with tempfile.TemporaryDirectory() as tmp:
            mask = make_half_n5(Path(tmp) / "shell.n5", shape=(8, 8, 8),
                                value=255, levels=(1,))
            A, b = hull_planes(mask, stride=2)
            self.assertEqual(A.shape[1], 3)
            self.assertTrue(
                np.allclose(np.linalg.norm(A, axis=1), 1.0, atol=1e-9))
            # The block centre is inside the hull of a solid cube.
            center = np.array([[3.5, 3.5, 3.5]])
            self.assertGreater(float(depth_of(center, A, b)[0]), 0.0)


class TestName(unittest.TestCase):
    def test_name_constant(self):
        self.assertEqual(NAME, "shell_left_clean")


if __name__ == "__main__":
    unittest.main()
