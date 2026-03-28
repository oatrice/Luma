import pytest
from luma_core.metrics_summarizer import _format_duration

def test_format_duration_seconds():
    # Less than 60 seconds
    assert _format_duration(5000) == "5s"
    assert _format_duration(55500) == "56s" # It uses f"{s:.0f}s" which rounds if >= 0.5

def test_format_duration_minutes():
    # 1 minute to 59 minutes
    assert _format_duration(60000) == "1m 0s"
    assert _format_duration(3599000) == "59m 59s"

def test_format_duration_hours():
    # 1 hour or more (Expected to fail currently)
    # 3600000 ms = 1 hour
    assert _format_duration(3600000) == "1h 0m 0s"
    
    # 103m 18s = 1h 43m 18s
    # (103 * 60 + 18) * 1000 = 6198000 ms
    assert _format_duration(6198000) == "1h 43m 18s"

def test_format_duration_edge_cases():
    assert _format_duration(0) == "0s"
    assert _format_duration(None) == "0s"
