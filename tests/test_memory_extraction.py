import pytest
from unittest.mock import patch, MagicMock


def _mock(json_str):
    m = MagicMock()
    m.content = json_str
    return m


class TestExtraction:
    @patch("src.memory.extraction.llm")
    def test_evening_preference(self, mock_llm):
        from src.memory.extraction import extract_memory_updates

        mock_llm.invoke.return_value = _mock('{"preferred_study_time": "evening"}')
        assert extract_memory_updates("I prefer evening") == {
            "preferred_study_time": "evening"
        }

    @patch("src.memory.extraction.llm")
    def test_invalid_time_rejected(self, mock_llm):
        from src.memory.extraction import extract_memory_updates

        mock_llm.invoke.return_value = _mock(
            '{"preferred_study_time": "late afternoon"}'
        )
        assert extract_memory_updates("test") == {}

    @patch("src.memory.extraction.llm")
    def test_empty_for_questions(self, mock_llm):
        from src.memory.extraction import extract_memory_updates

        mock_llm.invoke.return_value = _mock("{}")
        assert extract_memory_updates("What's due?") == {}

    @patch("src.memory.extraction.llm")
    def test_temporary_not_extracted(self, mock_llm):
        from src.memory.extraction import extract_memory_updates

        mock_llm.invoke.return_value = _mock("{}")
        assert extract_memory_updates("I studied Python tonight") == {}
