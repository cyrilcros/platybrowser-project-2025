"""Tests for add_individual_hcr_sources_and_views.py."""

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from add_individual_hcr_sources_and_views import (
    PALETTE,
    add_sources_and_views,
    build_groups,
    color_for_rep,
    display_label,
    distinct_colors,
    parse_stem,
    source_definition,
    view_definition,
)

STEMS = [
    "Ache2_AP155--vsx2-ache2_pl1-2",
    "Ache2_AP155--vsx2-ache2_pl4-2",
    "Arx--ptf1-arx_pl1-1",
    "Arx--ptf1-arx_pl2-1",
    "Bsx_AP203--Bsx-Hoxa1_Pl1-2",
    "NoProbe--panel-x_pl5",
    "Prox--prox-brn3-sfg_pl3",
    "Prox_prox-brn3-sfg_pl3",
]

EXISTING = {
    "is2D": False,
    "defaultLocation": {"position": [1.0, 2.0, 3.0]},
    "sources": {
        "raw": {"image": {"imageData": {"bdv.n5": {"relativePath": "x.xml"}}}},
    },
    "views": {
        "default": {
            "uiSelectionGroup": "Figures Vergara2021",
            "sourceDisplays": [{"imageDisplay": {"sources": ["raw"]}}],
        },
    },
}


def make_xml_dir(tmp_path, stems=STEMS):
    xml_dir = tmp_path / "HCR_individual"
    xml_dir.mkdir()
    for stem in stems:
        (xml_dir / f"{stem}.xml").write_text("<xml/>")
    return xml_dir


# --- parsing ---------------------------------------------------------------

def test_gene_grouping_and_sort():
    groups = build_groups(STEMS)
    assert list(groups) == ["Ache2", "Arx", "Bsx", "NoProbe", "Prox"]
    # within a gene: replicate ascending
    assert [p["rep"] for _, p in groups["Ache2"]] == [1, 4]
    assert [p["rep"] for _, p in groups["Arx"]] == [1, 2]


def test_pl_casing_is_treated_like_lowercase_pl():
    parsed = parse_stem("Bsx_AP203--Bsx-Hoxa1_Pl1-2")
    assert parsed["gene"] == "Bsx"
    assert parsed["probe"] == "203"
    assert parsed["panel"] == "Bsx-Hoxa1"
    assert parsed["rep"] == 1
    assert parsed["run"] == 2


def test_missing_probe():
    parsed = parse_stem("Arx--ptf1-arx_pl1-1")
    assert parsed["gene"] == "Arx"
    assert parsed["probe"] is None
    assert display_label(parsed) == "Arx | ptf1-arx | pl1-1"


def test_missing_run():
    parsed = parse_stem("NoProbe--panel-x_pl5")
    assert parsed["probe"] is None
    assert parsed["run"] is None
    assert display_label(parsed) == "NoProbe | panel-x | pl5"


def test_underscore_separator_fallback():
    parsed = parse_stem("Prox_prox-brn3-sfg_pl3")
    assert parsed["gene"] == "Prox"
    assert parsed["probe"] is None
    assert parsed["panel"] == "prox-brn3-sfg"
    assert parsed["rep"] == 3
    assert parsed["run"] is None
    assert display_label(parsed) == "Prox | prox-brn3-sfg | pl3"


def test_unparseable_stem_raises():
    with pytest.raises(ValueError):
        parse_stem("totally_unparseable")


# --- views -----------------------------------------------------------------

def test_one_image_display_per_replicate(tmp_path):
    groups = build_groups(STEMS)
    view = view_definition(groups["Ache2"], "all_HCRs")
    assert len(view["sourceDisplays"]) == 2
    assert [sd["imageDisplay"]["sources"][0] for sd in view["sourceDisplays"]] == [
        "Ache2_AP155--vsx2-ache2_pl1-2",
        "Ache2_AP155--vsx2-ache2_pl4-2",
    ]
    assert all(len(sd["imageDisplay"]["sources"]) == 1 for sd in view["sourceDisplays"])


def test_palette_colour_per_replicate(tmp_path):
    groups = build_groups(STEMS)
    view = view_definition(groups["Ache2"], "all_HCRs")
    assert view["sourceDisplays"][0]["imageDisplay"]["color"] == _argb(PALETTE[1])
    assert view["sourceDisplays"][1]["imageDisplay"]["color"] == _argb(PALETTE[4])
    # same replicate -> same colour in a different gene
    arx1 = view_definition(groups["Arx"], "all_HCRs")["sourceDisplays"][0]
    assert arx1["imageDisplay"]["color"] == _argb(PALETTE[1])


def test_color_out_of_palette_raises():
    assert color_for_rep(12) == _argb(PALETTE[12])
    with pytest.raises(ValueError):
        color_for_rep(13)


def test_multi_panel_replicate_colours_are_distinct():
    # One gene, two panels with overlapping replicate numbers (reps 1,2,1,2).
    stems = [
        "X--a_pl1-0",
        "X--a_pl2-0",
        "X_AP9--b_pl1-1",
        "X_AP9--b_pl2-1",
    ]
    entries = [(stem, parse_stem(stem)) for stem in stems]
    view = view_definition(entries, "all_HCRs")
    colours = [sd["imageDisplay"]["color"] for sd in view["sourceDisplays"]]

    assert len(colours) == 4
    assert len(set(colours)) == 4  # (a) all four colours distinct
    # (b) the first occurrence of each replicate keeps PALETTE[rep]
    assert colours[0] == _argb(PALETTE[1])
    assert colours[1] == _argb(PALETTE[2])


def test_distinct_colors_advance_past_used_entries():
    # reps [1, 2, 1, 2]: 2nd rep1 advances to P3, then 2nd rep2 to P4.
    colours = distinct_colors([1, 2, 1, 2])
    assert colours == [_argb(PALETTE[1]), _argb(PALETTE[2]),
                       _argb(PALETTE[3]), _argb(PALETTE[4])]
    assert len(set(colours)) == 4


def test_too_many_displays_for_palette_raises():
    with pytest.raises(ValueError):
        distinct_colors([1] * 13)


def test_no_default_valued_keys_emitted():
    groups = build_groups(STEMS)
    view = view_definition(groups["Arx"], "all_HCRs")
    assert set(view) == {"uiSelectionGroup", "sourceDisplays"}
    assert "isExclusive" not in view
    for sd in view["sourceDisplays"]:
        assert set(sd) == {"imageDisplay"}
        assert set(sd["imageDisplay"]) == {"sources", "color", "contrastLimits", "name"}
        assert sd["imageDisplay"]["contrastLimits"] == [0.0, 0.1]


def test_label_collision_disambiguation(tmp_path):
    groups = build_groups(STEMS)
    view = view_definition(groups["Prox"], "all_HCRs")
    names = [sd["imageDisplay"]["name"] for sd in view["sourceDisplays"]]
    assert names == [
        "Prox | prox-brn3-sfg | pl3",
        "Prox | prox-brn3-sfg | pl3 [2]",
    ]
    assert len(set(names)) == len(names)


# --- sources ---------------------------------------------------------------

def test_source_definition_points_at_s3_xml():
    src = source_definition("Ache2_AP155--vsx2-ache2_pl1-2")
    assert src == {
        "image": {
            "imageData": {
                "bdv.n5.s3": {
                    "relativePath": (
                        "images/bdv-n5-s3/HCR_individual/"
                        "Ache2_AP155--vsx2-ache2_pl1-2.xml"
                    )
                }
            }
        }
    }


# --- integration -----------------------------------------------------------

def test_add_preserves_existing_and_appends(tmp_path):
    xml_dir = make_xml_dir(tmp_path)
    data = copy.deepcopy(EXISTING)
    summary = add_sources_and_views(data, xml_dir)
    assert data["sources"]["raw"] == EXISTING["sources"]["raw"]
    assert data["views"]["default"] == EXISTING["views"]["default"]
    assert list(data["sources"])[0] == "raw"  # existing key order preserved
    assert list(data["views"])[0] == "default"
    assert len(data["sources"]) == 1 + len(STEMS)
    assert len(data["views"]) == 1 + 5  # 5 genes
    assert data["views"]["Ache2"]["uiSelectionGroup"] == "all_HCRs"
    # clean dataset -> bare gene names, no suffix
    assert "Ache2" in data["views"]
    assert not any(name.endswith("(individual)") for name in data["views"])
    assert summary == {
        "xmls": len(STEMS),
        "genes": 5,
        "sources_added": len(STEMS),
        "views_added": 5,
        "views_updated": 0,
    }


def test_gene_name_taken_by_other_group_gets_individual_suffix(tmp_path):
    xml_dir = make_xml_dir(tmp_path)
    data = copy.deepcopy(EXISTING)
    other = {
        "uiSelectionGroup": "HCR_combined",
        "sourceDisplays": [{"imageDisplay": {"sources": ["raw"], "name": "Arx"}}],
    }
    data["views"]["Arx"] = copy.deepcopy(other)

    summary = add_sources_and_views(data, xml_dir)

    assert data["views"]["Arx"] == other  # existing view untouched
    assert "Arx (individual)" in data["views"]
    assert data["views"]["Arx (individual)"]["uiSelectionGroup"] == "all_HCRs"
    # every gene got a view
    assert summary["views_added"] == 5
    assert summary["views_updated"] == 0
    assert "Ache2" in data["views"]


def test_gene_already_in_target_group_is_replaced_in_place(tmp_path):
    xml_dir = make_xml_dir(tmp_path)
    data = copy.deepcopy(EXISTING)
    stale = {
        "uiSelectionGroup": "all_HCRs",
        "sourceDisplays": [{"imageDisplay": {"sources": ["raw"], "name": "Arx"}}],
    }
    data["views"]["Arx"] = copy.deepcopy(stale)
    order_before = list(data["views"])

    summary = add_sources_and_views(data, xml_dir)

    # stale target-group view refreshed in place (colour fix lands), not renamed
    assert data["views"]["Arx"] != stale
    assert data["views"]["Arx"]["uiSelectionGroup"] == "all_HCRs"
    assert "Arx (individual)" not in data["views"]
    # pre-existing keys keep their relative order (new views are appended)
    assert [k for k in data["views"] if k in order_before] == order_before
    assert summary["views_added"] == 4  # the other 4 genes
    assert summary["views_updated"] == 1  # the refreshed Arx view
    assert summary["sources_added"] == len(STEMS)


def test_idempotent_in_memory(tmp_path):
    xml_dir = make_xml_dir(tmp_path)
    once = copy.deepcopy(EXISTING)
    add_sources_and_views(once, xml_dir)
    twice = copy.deepcopy(EXISTING)
    add_sources_and_views(twice, xml_dir)
    summary = add_sources_and_views(twice, xml_dir)
    assert twice == once
    assert summary["sources_added"] == 0
    assert summary["views_added"] == 0
    assert summary["views_updated"] == 0


def test_idempotent_byte_identical_on_disk(tmp_path):
    from add_individual_hcr_sources_and_views import main

    xml_dir = make_xml_dir(tmp_path)
    ds_path = tmp_path / "dataset.json"
    with open(ds_path, "w", encoding="utf-8") as f:
        json.dump(copy.deepcopy(EXISTING), f, indent=2)
        f.write("\n")

    main(["--dataset-json", str(ds_path), "--xml-dir", str(xml_dir), "--write"])
    first = ds_path.read_bytes()
    assert first.endswith(b"}\n") and not first.endswith(b"}\n\n")
    main(["--dataset-json", str(ds_path), "--xml-dir", str(xml_dir), "--write"])
    assert ds_path.read_bytes() == first


def test_second_run_after_collision_is_noop(tmp_path):
    """A collision-suffixed view must not be renamed on a later run."""
    from add_individual_hcr_sources_and_views import main

    xml_dir = make_xml_dir(tmp_path)
    ds_path = tmp_path / "dataset.json"
    seed = copy.deepcopy(EXISTING)
    seed["views"]["Arx"] = {
        "uiSelectionGroup": "HCR_combined",
        "sourceDisplays": [{"imageDisplay": {"sources": ["raw"], "name": "Arx"}}],
    }
    with open(ds_path, "w", encoding="utf-8") as f:
        json.dump(seed, f, indent=2)
        f.write("\n")

    main(["--dataset-json", str(ds_path), "--xml-dir", str(xml_dir), "--write"])
    first = ds_path.read_bytes()
    assert b'"Arx (individual)"' in first
    main(["--dataset-json", str(ds_path), "--xml-dir", str(xml_dir), "--write"])
    assert ds_path.read_bytes() == first
    data = json.loads(ds_path.read_text())
    assert data["views"]["Arx"]["uiSelectionGroup"] == "HCR_combined"
    assert data["views"]["Arx (individual)"]["uiSelectionGroup"] == "all_HCRs"
    assert "Arx (individual) (individual)" not in data["views"]


def _argb(rgb):
    red, green, blue = rgb
    return f"r={red},g={green},b={blue},a=255"
