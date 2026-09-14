import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import z5py

from generate_shell_halves import (
    HALVES,
    HALF_NAMES,
    block_slices,
    main,
    mask_block,
    mirror_group_attrs,
    mirror_level_info,
    write_halves,
    write_local_xmls,
    write_s3_xmls,
)


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


def make_mask_n5(path: Path, shape=(3, 4, 5)) -> Path:
    """Tiny single-level uint8 mask N5 with shell-like group attributes."""
    with z5py.File(str(path), "a") as f:
        setup = f.create_group("setup0")
        setup.attrs["dataType"] = "uint8"
        setup.attrs["downsamplingFactors"] = [[1, 1, 1]]
        tp = setup.create_group("timepoint0")
        tp.attrs["multiScale"] = True
        tp.attrs["resolution"] = [0.32, 0.32, 0.4]
        ds = tp.create_dataset(
            "s0", shape=shape, chunks=(2, 2, 2),
            dtype="uint8", compression="gzip", level=1, fillvalue=0,
        )
        ds.attrs["downsamplingFactors"] = [1, 1, 1]
        ds[:] = 1
    return path


class TestWriteHalves(unittest.TestCase):
    def test_writes_four_masked_uint8_n5s(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            mask = make_mask_n5(tmp / "mask.n5")
            levels = mirror_level_info(mask)
            attrs = mirror_group_attrs(mask)
            stage = tmp / "stage"
            write_halves(mask, stage, levels, attrs, offset=0, gzip_level=1)

            self.assertEqual(
                sorted(p.name for p in stage.glob("*.n5")),
                sorted(f"{n}.n5" for n in HALF_NAMES),
            )
            for name, keep in HALVES.items():
                with z5py.File(str(stage / f"{name}.n5"), "r") as f:
                    ds = f["setup0/timepoint0/s0"]
                    self.assertEqual(tuple(ds.shape), (3, 4, 5))
                    self.assertEqual(ds.dtype, np.dtype("uint8"))
                    data = ds[:]
                # Two-directional check against the fixture (all-ones mask):
                # non-empty, and exactly the kept voxels present.
                self.assertTrue(data.any(), name)
                expected = mask_block(
                    np.ones((3, 4, 5), dtype=np.uint8), 0, 0, keep, 0
                )
                np.testing.assert_array_equal(data, expected)

    def test_group_attrs_mirrored(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            mask = make_mask_n5(tmp / "mask.n5")
            levels = mirror_level_info(mask)
            attrs = mirror_group_attrs(mask)
            stage = tmp / "stage"
            write_halves(mask, stage, levels, attrs)
            with z5py.File(str(stage / "shell_sag_left.n5"), "r") as f:
                self.assertEqual(dict(f["setup0"].attrs)["dataType"], "uint8")
                self.assertIn("downsamplingFactors", dict(f["setup0"].attrs))
                self.assertIs(
                    dict(f["setup0/timepoint0"].attrs)["multiScale"], True
                )
                self.assertEqual(
                    list(dict(f["setup0/timepoint0"].attrs)["resolution"]),
                    [0.32, 0.32, 0.4],
                )
                ds = f["setup0/timepoint0/s0"]
                self.assertEqual(tuple(ds.chunks), (2, 2, 2))
                self.assertEqual(ds.compression, "gzip")
                # z5py's Dataset exposes no fillvalue attribute in this version,
                # so fillvalue 0 is not directly assertable here.
                self.assertEqual(
                    list(dict(ds.attrs)["downsamplingFactors"]),
                    [1, 1, 1],
                )


class TestXml(unittest.TestCase):
    def test_local_xml_points_at_staged_n5(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            stage = tmp / "rawdata" / "shell_halves"
            local = tmp / "images" / "local"
            out = write_local_xmls(["shell_sag_left"], local, stage)
            root = ET.parse(out[0]).getroot()
            self.assertEqual(
                root.find(".//ViewSetup/name").text, "shell_sag_left")
            self.assertEqual(
                root.find(".//ImageLoader").get("format"), "bdv.n5")
            n5 = root.find(".//ImageLoader/n5")
            self.assertTrue(
                n5.text.replace("\\", "/").endswith(
                    "rawdata/shell_halves/shell_sag_left.n5"),
                n5.text,
            )

    def test_s3_xml_has_bucket_key_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = write_s3_xmls(["shell_cor_back"], Path(tmp) / "s3")
            root = ET.parse(out[0]).getroot()
            self.assertEqual(
                root.find(".//ViewSetup/name").text, "shell_cor_back")
            self.assertEqual(
                root.find(".//ImageLoader").get("format"), "bdv.n5.s3")
            self.assertEqual(
                root.find(".//Key").text,
                "images/bdv-n5-s3/shell_halves/shell_cor_back.n5",
            )
            self.assertEqual(root.find(".//BucketName").text, "platybrowser-2025")
            self.assertEqual(
                root.find(".//ServiceEndpoint").text, "https://s3.embl.de")
            self.assertEqual(root.find(".//SigningRegion").text, "us-west-2")


class TestCli(unittest.TestCase):
    def test_main_writes_n5s_and_xmls(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            mask = make_mask_n5(tmp / "mask.n5")
            stage = tmp / "stage"
            local = tmp / "local"
            s3 = tmp / "s3"
            import sys as _sys
            argv = _sys.argv
            _sys.argv = [
                "generate_shell_halves.py",
                "--mask", str(mask),
                "--stage-dir", str(stage),
                "--local-xml-dir", str(local),
                "--s3-xml-dir", str(s3),
            ]
            try:
                main()
            finally:
                _sys.argv = argv
            self.assertEqual(len(list(stage.glob("*.n5"))), 4)
            self.assertEqual(len(list(local.glob("*.xml"))), 4)
            self.assertEqual(len(list(s3.glob("*.xml"))), 4)


if __name__ == "__main__":
    unittest.main()
