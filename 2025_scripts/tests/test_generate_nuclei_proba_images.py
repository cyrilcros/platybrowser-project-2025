import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import z5py

from generate_nuclei_proba_images import (
    read_subtype_columns,
    read_probabilities,
    build_value_table,
    mirror_level_info,
    relabel_block,
    write_outputs,
)


def make_fixture_tsv(path: Path) -> Path:
    path.write_text(
        "label_id\tclade1sub1\tclade6sub19\tnocladesub3\tzero\tautofluorescence\tmost probable cluster\n"
        "1.0\t0.95\t0.0003\t0.0\t0.0\t0.0\tclade1sub1\n"
        "2.0\t0.4996\t0.9996\t0.5\t0.0\t0.0\tclade6sub19\n"
        "3.0\t0.0\t0.0\t1.0\t0.0\t0.0\tnocladesub3\n",
        encoding="utf-8",
    )
    return path


def make_mask_n5(path: Path) -> Path:
    """Minimal 2-level nuclei-like mask: s0 16^3, s1 8^3, labels {1, 2}."""
    import z5py
    with z5py.File(str(path), "a") as f:
        g = f.create_group("setup0").create_group("timepoint0")
        s0 = g.create_dataset("s0", shape=(16, 16, 16), chunks=(8, 8, 8),
                              dtype="uint32", compression="gzip", fillvalue=0)
        s0.attrs["resolution"] = [0.08, 0.08, 0.1]
        s0.attrs["downsamplingFactors"] = [1, 1, 1]
        s0.attrs["offset"] = [0.0, 0.0, 0.0]
        a0 = np.zeros((16, 16, 16), dtype=np.uint32)
        a0[2:5, 2:5, 2:5] = 1
        a0[10:13, 10:13, 10:13] = 2
        s0[...] = a0
        s1 = g.create_dataset("s1", shape=(8, 8, 8), chunks=(8, 8, 8),
                              dtype="uint32", compression="gzip", fillvalue=0)
        s1.attrs["resolution"] = [0.08, 0.08, 0.1]
        s1.attrs["downsamplingFactors"] = [2, 2, 2]
        s1.attrs["offset"] = [0.0, 0.0, 0.0]
        a1 = np.zeros((8, 8, 8), dtype=np.uint32)
        a1[1:3, 1:3, 1:3] = 1
        a1[5:7, 5:7, 5:7] = 2
        s1[...] = a1
    return path


class TestReadSubtypeColumns(unittest.TestCase):
    def test_returns_only_clade_and_nocladesub_columns(self):
        with tempfile.TemporaryDirectory() as d:
            tsv = make_fixture_tsv(Path(d) / "proba.tsv")
            cols = read_subtype_columns(tsv)
            self.assertEqual(cols, ["clade1sub1", "clade6sub19", "nocladesub3"])


class TestReadProbabilities(unittest.TestCase):
    def test_returns_label_to_float(self):
        with tempfile.TemporaryDirectory() as d:
            tsv = make_fixture_tsv(Path(d) / "proba.tsv")
            probs = read_probabilities(tsv, "clade1sub1")
            self.assertEqual(probs[1], 0.95)
            self.assertEqual(probs[3], 0.0)


class TestBuildValueTable(unittest.TestCase):
    def test_rounds_to_0_001_and_maps_zero_for_missing_and_background(self):
        table = build_value_table({1: 0.95, 2: 0.4996, 3: 0.0003})
        self.assertEqual(table.dtype, np.uint16)
        self.assertEqual(table[0], 0)      # background
        self.assertEqual(table[1], 950)    # round(0.95 * 1000)
        self.assertEqual(table[2], 500)    # round(0.4996 * 1000)
        self.assertEqual(table[3], 0)      # round(0.0003 * 1000) -> 0
        self.assertEqual(len(table), 4)    # max_label + 1


class TestMirrorLevelInfo(unittest.TestCase):
    def test_mirror_level_info_reads_pyramid(self):
        with tempfile.TemporaryDirectory() as d:
            mask = make_mask_n5(Path(d) / "mask.n5")
            levels = mirror_level_info(mask)
            self.assertEqual([lv["name"] for lv in levels], ["s0", "s1"])
            self.assertEqual(levels[0]["shape"], (16, 16, 16))
            self.assertEqual(levels[0]["chunks"], (8, 8, 8))
            self.assertEqual(levels[1]["shape"], (8, 8, 8))
            self.assertEqual(levels[1]["attrs"]["downsamplingFactors"], [2, 2, 2])


class TestRelabelBlock(unittest.TestCase):
    def test_relabel_block(self):
        mask_block = np.zeros((2, 2, 2), dtype=np.uint32)
        mask_block[0, 0, 0] = 1
        mask_block[0, 0, 1] = 2
        mask_block[1, 1, 1] = 99  # not in table -> 0
        table = build_value_table({1: 0.95, 2: 0.4996})
        out = relabel_block(mask_block, table)
        self.assertEqual(out.dtype, np.uint16)
        self.assertEqual(int(out[0, 0, 0]), 950)
        self.assertEqual(int(out[0, 0, 1]), 500)
        self.assertEqual(int(out[1, 1, 1]), 0)


class TestWriteOutputs(unittest.TestCase):
    def test_writes_pyramid_mirroring_mask_with_relabeled_values(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            mask = make_mask_n5(d / "mask.n5")
            levels = mirror_level_info(mask)
            value_tables = {
                "clade1sub1": build_value_table({1: 0.95, 2: 0.4996}),
                "nocladesub3": build_value_table({1: 0.0, 2: 1.0}),
            }
            stage = d / "out"
            written = write_outputs(mask, value_tables, stage, levels)
            self.assertEqual(len(written), 2)
            self.assertTrue((stage / "clade1sub1_proba.n5").is_dir())

            with z5py.File(str(stage / "clade1sub1_proba.n5"), "r") as f:
                s0 = f["setup0/timepoint0/s0"]
                self.assertEqual(s0.shape, (16, 16, 16))
                self.assertEqual(s0.dtype, np.uint16)
                self.assertEqual(tuple(s0.chunks), (8, 8, 8))
                self.assertEqual(s0.attrs["resolution"], [0.08, 0.08, 0.1])
                self.assertEqual(s0.attrs["downsamplingFactors"], [1, 1, 1])
                a0 = s0[...]
                self.assertEqual(int(a0[3, 3, 3]), 950)      # label 1 -> 0.95
                self.assertEqual(int(a0[11, 11, 11]), 500)   # label 2 -> 0.4996
                self.assertEqual(int(a0[0, 0, 0]), 0)        # background
                s1 = f["setup0/timepoint0/s1"]
                self.assertEqual(s1.shape, (8, 8, 8))
                self.assertEqual(s1.attrs["downsamplingFactors"], [2, 2, 2])
                a1 = s1[...]
                self.assertEqual(int(a1[2, 2, 2]), 950)      # relabeled s1
                self.assertEqual(int(a1[6, 6, 6]), 500)

            with z5py.File(str(stage / "nocladesub3_proba.n5"), "r") as f:
                a0 = f["setup0/timepoint0/s0"][...]
                self.assertEqual(int(a0[3, 3, 3]), 0)
                self.assertEqual(int(a0[11, 11, 11]), 1000)  # label 2 -> 1.0
