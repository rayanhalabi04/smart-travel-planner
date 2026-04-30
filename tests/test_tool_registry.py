import sys
import types

import pytest
from pydantic import ValidationError

# The test only validates allowlist/schema wiring and does not execute ML inference.
if "pandas" not in sys.modules:
    pandas_stub = types.ModuleType("pandas")
    pandas_stub.DataFrame = object  # type: ignore[attr-defined]
    sys.modules["pandas"] = pandas_stub

if "sentence_transformers" not in sys.modules:
    sentence_transformers_stub = types.ModuleType("sentence_transformers")
    sentence_transformers_stub.SentenceTransformer = object  # type: ignore[attr-defined]
    sys.modules["sentence_transformers"] = sentence_transformers_stub

from app.tools.registry import get_tool, is_tool_allowed


def test_three_required_tools_are_registered() -> None:
    assert is_tool_allowed("weather")
    assert is_tool_allowed("destination_search")
    assert is_tool_allowed("classify_style")


def test_unknown_tool_is_not_allowed() -> None:
    assert not is_tool_allowed("not_a_real_tool")
    assert get_tool("not_a_real_tool") is None


def test_classify_style_schema_rejects_missing_inputs() -> None:
    definition = get_tool("classify_style")
    assert definition is not None

    with pytest.raises(ValidationError):
        definition.input_schema.model_validate({})
