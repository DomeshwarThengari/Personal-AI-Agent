import os
from typing import Any
from unittest.mock import patch, MagicMock
from PIL import Image
from src.application.tools.vision_tools import (
    VisionTakeScreenshotTool,
    VisionAnalyzeImageTool,
)


def test_vision_take_screenshot_tool() -> None:
    tool = VisionTakeScreenshotTool()
    assert tool.name == "vision_take_screenshot"

    temp_path = os.path.abspath("test_screenshot.png")
    if os.path.exists(temp_path):
        os.remove(temp_path)

    try:
        # Run execution
        res = tool.execute(output_path=temp_path)
        assert "Screenshot successfully captured" in res
        assert os.path.exists(temp_path)
        assert os.path.getsize(temp_path) > 0
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@patch("src.application.tools.vision_tools.settings")
def test_vision_analyze_image_tool_simulated(mock_settings: Any) -> None:
    mock_settings.GEMINI_API_KEY = "your_gemini_api_key_here"
    tool = VisionAnalyzeImageTool()
    assert tool.name == "vision_analyze_image"

    # Write a dummy file to analyze
    temp_path = os.path.abspath("dummy_screen.png")
    img = Image.new("RGB", (10, 10))
    img.save(temp_path, "PNG")

    try:
        # Test file check
        err_res = tool.execute(image_path="nonexistent.png", prompt="What is this?")
        assert "does not exist" in err_res

        # Test Error Prompt
        res_error = tool.execute(
            image_path=temp_path, prompt="Describe the error message shown."
        )
        assert "ModuleNotFoundError" in res_error

        # Test Text Prompt
        res_text = tool.execute(image_path=temp_path, prompt="Extract all text.")
        assert "AI Agent Desktop - Active" in res_text

        # Test Layout Prompt
        res_layout = tool.execute(
            image_path=temp_path, prompt="Explain layout problems."
        )
        assert "UI Layout Debugging Analysis" in res_layout
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@patch("google.generativeai.GenerativeModel")
@patch("src.application.tools.vision_tools.settings")
def test_vision_analyze_image_real_api(
    mock_settings: Any, mock_model_class: Any
) -> None:
    # Setup mock API key
    mock_settings.GEMINI_API_KEY = "valid_real_api_key_123"

    # Setup mock generative model behavior
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is a real model description of the screenshot."
    mock_model.generate_content.return_value = mock_response
    mock_model_class.return_value = mock_model

    tool = VisionAnalyzeImageTool()
    temp_path = os.path.abspath("dummy_real.png")
    img = Image.new("RGB", (10, 10))
    img.save(temp_path, "PNG")

    try:
        with patch("google.generativeai.configure") as mock_configure:
            res = tool.execute(image_path=temp_path, prompt="Describe screenshot")
            assert res == "This is a real model description of the screenshot."
            mock_configure.assert_called_once_with(api_key="valid_real_api_key_123")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
