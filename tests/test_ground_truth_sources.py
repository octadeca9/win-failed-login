"""Ground-truth can be supplied via env var (for env-only platforms) or file."""
import base64
from pathlib import Path

import pytest

from app import config
from app.services import loaders


@pytest.fixture
def gt_env():
    """Isolate ground-truth config + cache for each test, then restore."""
    loaders.load_ground_truth.cache_clear()
    saved = (config.GROUND_TRUTH_B64, config.GROUND_TRUTH_YAML, config.GROUND_TRUTH_PATH)
    with open(config.GROUND_TRUTH_PATH, "r", encoding="utf-8") as fh:
        text = fh.read()
    yield text
    config.GROUND_TRUTH_B64, config.GROUND_TRUTH_YAML, config.GROUND_TRUTH_PATH = saved
    loaders.load_ground_truth.cache_clear()


def test_loads_from_b64_env(gt_env):
    config.GROUND_TRUTH_B64 = base64.b64encode(gt_env.encode()).decode()
    config.GROUND_TRUTH_YAML = None
    config.GROUND_TRUTH_PATH = Path("/nonexistent/nope.yaml")
    gt = loaders.load_ground_truth()
    assert gt["tasks"]["T1"]["expected"] == "4625"
    assert gt["tasks"]["T8"]["expected"] == 3


def test_loads_from_yaml_env(gt_env):
    config.GROUND_TRUTH_B64 = None
    config.GROUND_TRUTH_YAML = gt_env
    config.GROUND_TRUTH_PATH = Path("/nonexistent/nope.yaml")
    assert loaders.load_ground_truth()["tasks"]["T3"]["expected"] == "198.51.100.42"


def test_b64_takes_precedence_over_yaml(gt_env):
    config.GROUND_TRUTH_B64 = base64.b64encode(gt_env.encode()).decode()
    config.GROUND_TRUTH_YAML = "tasks: {}"  # would break if used
    gt = loaders.load_ground_truth()
    assert gt["tasks"]["T1"]["expected"] == "4625"


def test_missing_source_raises(gt_env):
    config.GROUND_TRUTH_B64 = None
    config.GROUND_TRUTH_YAML = None
    config.GROUND_TRUTH_PATH = Path("/nonexistent/nope.yaml")
    with pytest.raises(loaders.GroundTruthNotConfigured):
        loaders.load_ground_truth()


def test_invalid_b64_raises(gt_env):
    config.GROUND_TRUTH_B64 = "!!! not base64 !!!"
    config.GROUND_TRUTH_YAML = None
    with pytest.raises(loaders.GroundTruthNotConfigured):
        loaders.load_ground_truth()
