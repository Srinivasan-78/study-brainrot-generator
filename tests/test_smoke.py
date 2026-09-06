# @authormark v1 -- do not remove (authorship watermark)
# Copyright (c) 2026 Srinivasan Vijayaraghavan <srinivasan.shyam2000@gmail.com>
# Author: https://github.com/Srinivasan-78
# SPDX-License-Identifier: MIT
# Fingerprint: AMK1.SD59VIhXwe4U5Dm_28te0S
"""Smoke tests for the pipeline scripts.

Import every stage, then exercise the pure helpers (no network, no ffmpeg,
no LLM keys): source packing, fenced-JSON stripping, script validation and
the ASS caption formatters.
"""
import importlib
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


@pytest.mark.parametrize("mod", ["research", "script_gen", "voice_gen", "assemble"])
def test_stage_imports(mod):
    importlib.import_module(mod)


def test_pack_stays_within_budget_and_keeps_every_source():
    research = importlib.import_module("research")
    packed = research.pack(["a" * 100, "b" * 10, "c" * 40], 60)
    assert len(packed) == 3
    assert sum(len(p) for p in packed) <= 60


def test_pack_empty_input():
    research = importlib.import_module("research")
    assert research.pack([], 100) == []


def test_strip_fences():
    script_gen = importlib.import_module("script_gen")
    assert script_gen.strip_fences('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert script_gen.strip_fences("no fences here") == "no fences here"


def test_validate_accepts_a_well_formed_script():
    script_gen = importlib.import_module("script_gen")
    data = {"chunks": [{"text": f"short lesson number {i} goes here"} for i in range(8)]}
    assert script_gen.validate(data) is data


@pytest.mark.parametrize(
    "bad",
    [
        {},
        {"chunks": "not-a-list"},
        {"chunks": [{"text": "too few"}] * 3},
        {"chunks": [{"text": ""}] * 8},
        {"chunks": [{"text": "word " * 80}] * 8},
    ],
)
def test_validate_rejects_bad_scripts(bad):
    script_gen = importlib.import_module("script_gen")
    with pytest.raises(ValueError):
        script_gen.validate(bad)


def test_ass_timestamp():
    assemble = importlib.import_module("assemble")
    assert assemble.ass_timestamp(0) == "0:00:00.00"
    assert assemble.ass_timestamp(3661.5) == "1:01:01.50"


def test_ass_escape_strips_markup():
    assemble = importlib.import_module("assemble")
    assert assemble.ass_escape("a{b}" + chr(92) + "c\nd") == "abc d"
