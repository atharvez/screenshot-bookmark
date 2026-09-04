"""Claude API analyzer for extracting metadata from OCR text."""
import anthropic
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class BookmarkMetadata:
    """Metadata extracted from a screenshot."""
    title: str = ""
    url: str = ""
    description: str = ""
    tags: str = ""  # comma-separated tags

class ClaudeAnalyzer:
    """Analyzes OCR text using Claude API to extract bookmark metadata."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-opus-5"):
        """
        Initialize the Claude analyzer.

        Args:
            api_key: Optional API key (if not provided, uses environment)
            model: Claude model to use (default: claude-opus-5)
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        logger.info(f"Initialized ClaudeAnalyzer with model {model}")

    def analyze_ocr_text(self, ocr_text: str, image_path: str = "") -> BookmarkMetadata:
        """
        Analyze OCR text to extract bookmark metadata.

        Args:
            ocr_text: Text extracted from screenshot via OCR
            image_path: Path to the screenshot (for context)

        Returns:
            BookmarkMetadata with extracted information
        """
        if not ocr_text.strip():
            logger.warning("Empty OCR text provided")
            return BookmarkMetadata()

        # Truncate very long OCR text to avoid excessive token usage
        # Claude Opus 5 supports up to 200K context, but we'll be conservative
        max_ocr_length = 8000  # chars
        if len(ocr_text) > max_ocr_length:
            logger.info(f"Truncating OCR text from {len(ocr_text)} to {max_ocr_length} chars")
            ocr_text = ocr_text[:max_ocr_length] + "..."

        prompt = self._build_analysis_prompt(ocr_text, image_path)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,  # We expect a relatively short response
                thinking={"type": "adaptive"},
                system="You are an expert at extracting structured information from screenshot OCR text. "
                       "Your task is to identify the title, URL, description, and relevant tags for a bookmark. "
                       "Be concise and accurate. If information is not present, leave fields empty.",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Extract the text response
            response_text = ""
            for block in response.content:
                if block.type == "text":
                    response_text = block.text
                    break

            # Parse the JSON response
            metadata = self._parse_response(response_text)
            logger.info(f"Extracted metadata: {metadata}")
            return metadata

        except Exception as e:
            logger.exception(f"Claude API analysis failed: {e}")
            # Return empty metadata on failure
            return BookmarkMetadata()

    def _build_analysis_prompt(self, ocr_text: str, image_path: str) -> str:
        """Build the prompt for Claude analysis."""
        return f"""
Analyze the following OCR text extracted from a screenshot and extract bookmark metadata.

OCR Text:
{ocr_text}

Image Path: {image_path}

Please extract:
1. Title: The main title or headline of the content (if present)
2. URL: Any website URL visible in the screenshot (look for http/https links)
3. Description: A brief 1-2 sentence summary of what the screenshot shows
4. Tags: Relevant comma-separated tags describing the content (e.g., "news,tech,article", "product,shopping", "tutorial,programming")

Return the result as a JSON object with exactly these fields: title, url, description, tags.
If a field is not found or not applicable, use an empty string.
Do not include any additional text or explanation outside the JSON.

Example response:
{{
  "title": "How to Build a Neural Network from Scratch",
  "url": "https://example.com/tutorial/neural-network",
  "description": "A step-by-step tutorial showing how to implement a neural network using Python and NumPy.",
  "tags": "tutorial,programming,machine-learning,python"
}}
""".strip()

    def _parse_response(self, response_text: str) -> BookmarkMetadata:
        """Parse Claude's JSON response into BookmarkMetadata."""
        try:
            # Find JSON in the response (handle cases where Claude might add extra text)
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                data = json.loads(json_str)
                return BookmarkMetadata(
                    title=data.get('title', '').strip(),
                    url=data.get('url', '').strip(),
                    description=data.get('description', '').strip(),
                    tags=data.get('tags', '').strip()
                )
            else:
                logger.warning(f"No JSON found in response: {response_text}")
                return BookmarkMetadata()
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from response: {response_text}. Error: {e}")
            return BookmarkMetadata()
        except Exception as e:
            logger.exception(f"Unexpected error parsing response: {e}")
            return BookmarkMetadata()

# Convenience function for simple usage
def analyze_screenshot(ocr_text: str, image_path: str = "", api_key: Optional[str] = None) -> BookmarkMetadata:
    """
    Analyze screenshot OCR text to extract bookmark metadata.

    Args:
        ocr_text: Text extracted from screenshot
        image_path: Path to the screenshot file
        api_key: Optional Claude API key

    Returns:
        BookmarkMetadata with extracted information
    """
    analyzer = ClaudeAnalyzer(api_key=api_key)
    return analyzer.analyze_ocr_text(ocr_text, image_path)