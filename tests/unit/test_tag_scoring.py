"""Unit tests for the tag scoring helper used by get_tag_path."""

from canary_mcp.server import _score_tag_candidate


def test_scoring_prioritizes_name_over_path():
    """Keywords found in the tag name should yield a higher score than path-only matches."""
    keywords = ["kiln", "temperature"]

    name_score, name_matches = _score_tag_candidate(
        keywords,
        name="Kiln Temperature Sensor",
        path="Plant.Area1.Sensor01",
        description="",
        metadata={},
    )

    path_score, path_matches = _score_tag_candidate(
        keywords,
        name="Generic Sensor",
        path="Plant.Kiln.Section15.Temperature",
        description="",
        metadata={},
    )

    assert name_score > path_score
    assert "kiln" in name_matches["name"]
    assert "kiln" in path_matches["path"]


def test_scoring_includes_description_keyword():
    """Verify that description keywords contribute to the final score."""
    keywords = ["pressure"]

    base_score, _ = _score_tag_candidate(
        keywords,
        name="Steam Flow",
        path="Plant.Boiler.SteamFlow",
        description="",
        metadata={},
    )

    description_score, matches = _score_tag_candidate(
        keywords,
        name="Steam Flow",
        path="Plant.Boiler.SteamFlow",
        description="Differential pressure sensor",
        metadata={},
    )

    assert description_score > base_score
    assert "pressure" in matches["description"]


def test_scoring_handles_metadata_properties():
    """Metadata fields should influence scoring with a smaller weight."""
    keywords = ["shell"]

    score, matches = _score_tag_candidate(
        keywords,
        name="Kiln Temperature",
        path="Plant.Kiln.Temp",
        description="Temperature sensor",
        metadata={"properties": {"location": "kiln shell", "unit": "C"}},
    )

    assert score > 0
    assert "shell" in matches["metadata"]
