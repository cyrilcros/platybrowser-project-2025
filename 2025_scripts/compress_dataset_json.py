#!/usr/bin/env python3
"""Compress dataset.json by removing viewer-default-valued keys.

Removes keys whose values equal the MoBIE viewer's Java defaults, per
AGENTS.md "Writing concise views (omit viewer defaults)". Idempotent:
running it on an already-compressed file is a no-op.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_PATH = Path("data/platybrowser_6dpf/dataset.json")

IMAGE_DISPLAY_DEFAULTS = {
    "opacity": 1.0,
    "visible": True,
    "invert": False,
    "showImagesIn3d": False,
    "blendingMode": "sum",
}

ANNOTATION_DISPLAY_DEFAULTS = {
    "visible": True,
    "opacity": 0.5,
    "showTable": True,
    "lut": "glasbey",
    "showAsBoundaries": False,
    "boundaryThickness": 1.0,
    "showScatterPlot": False,
    "scatterPlotAxes": ["anchor_x", "anchor_y"],
    "showSelectedSegmentsIn3d": False,
    "randomColorSeed": 42,
    "opacityNotSelected": 0.15,
    "blendingMode": "alpha",
}

WHITE_COLORS = ("white", "r=255,g=255,b=255,a=255")

DISPLAY_TYPES = (
    "imageDisplay",
    "segmentationDisplay",
    "spotDisplay",
    "regionDisplay",
)


def count_keys(obj):
    """Count every key in nested dicts (used for the removal summary)."""
    if isinstance(obj, dict):
        return len(obj) + sum(count_keys(v) for v in obj.values())
    if isinstance(obj, list):
        return sum(count_keys(v) for v in obj)
    return 0


def _strip_defaults(display, defaults):
    for key, default in defaults.items():
        if display.get(key) == default:
            del display[key]
    sources = display.get("sources")
    if sources and display.get("name") == sources[0]:
        del display["name"]


def compress_display(display_type, display):
    """Return a copy of a display dict with default-valued keys removed."""
    display = dict(display)
    if display_type == "imageDisplay":
        _strip_defaults(display, IMAGE_DISPLAY_DEFAULTS)
        if display.get("color") in WHITE_COLORS:
            del display["color"]
    else:
        _strip_defaults(display, ANNOTATION_DISPLAY_DEFAULTS)
    return display


def compress_view(view):
    """Return a copy of a view dict with default-valued keys removed."""
    view = dict(view)
    if view.get("isExclusive") is False:
        del view["isExclusive"]
    if view.get("sourceTransforms") == []:
        del view["sourceTransforms"]
    vt = view.get("viewerTransform")
    if isinstance(vt, dict) and vt.get("timepoint") == 0:
        vt = dict(vt)
        del vt["timepoint"]
        view["viewerTransform"] = vt
    sds = view.get("sourceDisplays")
    if isinstance(sds, list):
        new_sds = []
        for sd in sds:
            sd = dict(sd)
            for display_type in DISPLAY_TYPES:
                if display_type in sd:
                    sd[display_type] = compress_display(display_type, sd[display_type])
            new_sds.append(sd)
        view["sourceDisplays"] = new_sds
    return view


def compress_dataset(data):
    """Return a copy of the dataset with every view compressed."""
    data = dict(data)
    views = data.get("views")
    if isinstance(views, dict):
        data["views"] = {name: compress_view(v) for name, v in views.items()}
    return data
