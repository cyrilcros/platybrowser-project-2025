import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from generate_nuclei_proba_images import (
    read_subtype_columns,
    read_probabilities,
    build_value_table,
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
