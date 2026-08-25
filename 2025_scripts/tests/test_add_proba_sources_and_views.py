import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from add_proba_sources_and_views import (
    source_definition,
    view_definition,
    add_sources_and_views,
)

EXISTING = {
    "is2D": False,
    "defaultLocation": {"position": [1.0, 2.0, 3.0]},
    "sources": {
        "raw": {"image": {"imageData": {"bdv.n5": {"relativePath": "x.xml"}}}},
        "nuclei": {"segmentation": {"imageData": {"bdv.n5": {"relativePath": "n.xml"}}}},
    },
    "views": {
        "default": {"uiSelectionGroup": "Figures Vergara2021",
                    "sourceDisplays": [{"imageDisplay": {"sources": ["raw"]}}]},
    },
}


class TestDefinitions(unittest.TestCase):
    def test_source_definition_has_both_paths(self):
        src = source_definition("clade1sub1_proba")
        self.assertEqual(src["image"]["imageData"]["bdv.n5"]["relativePath"],
                         "images/local/clade1sub1_proba.xml")
        self.assertEqual(src["image"]["imageData"]["bdv.n5.s3"]["relativePath"],
                         "images/bdv-n5-s3/celltype_proba/clade1sub1_proba.xml")

    def test_view_definition_is_concise(self):
        view = view_definition("clade1sub1_proba")
        self.assertEqual(view["uiSelectionGroup"], "nuclei_probabilities")
        self.assertNotIn("isExclusive", view)
        self.assertNotIn("viewerTransform", view)
        disp = view["sourceDisplays"][0]["imageDisplay"]
        self.assertEqual(disp["sources"], ["clade1sub1_proba"])
        self.assertEqual(disp["contrastLimits"], [0.0, 1000.0])
        self.assertEqual(disp["name"], "clade1sub1_proba")
        self.assertEqual(set(disp.keys()), {"sources", "contrastLimits", "name"})


class TestAddSourcesAndViews(unittest.TestCase):
    def test_adds_and_preserves_existing(self):
        import copy
        data = add_sources_and_views(copy.deepcopy(EXISTING), ["clade1sub1", "clade6sub19"])
        self.assertIn("clade1sub1_proba", data["sources"])
        self.assertIn("clade6sub19_proba", data["views"])
        self.assertIn("raw", data["sources"])          # untouched
        self.assertIn("default", data["views"])        # untouched
        self.assertEqual(len(data["sources"]), 4)
        self.assertEqual(len(data["views"]), 3)

    def test_idempotent(self):
        import copy
        once = add_sources_and_views(copy.deepcopy(EXISTING), ["clade1sub1"])
        twice = add_sources_and_views(copy.deepcopy(once), ["clade1sub1"])
        self.assertEqual(twice, once)

    def test_sources_only_skips_views(self):
        import copy
        data = add_sources_and_views(copy.deepcopy(EXISTING), ["clade1sub1", "clade6sub19"],
                                     with_views=False)
        self.assertIn("clade1sub1_proba", data["sources"])
        self.assertIn("clade6sub19_proba", data["sources"])
        self.assertNotIn("clade1sub1_proba", data["views"])
        self.assertNotIn("clade6sub19_proba", data["views"])
        self.assertEqual(set(data["views"]), set(EXISTING["views"]))  # views untouched
