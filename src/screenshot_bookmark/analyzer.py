"""Google Gemini analyzer for extracting metadata from OCR text."""
import json
import logging
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover - allow import without the package for tooling
    genai = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# Default Gemini model. Override with the GEMINI_MODEL env var or the
# ``model`` constructor argument.
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

SYSTEM_INSTRUCTION = (
    "You are an expert at extracting structured information from screenshot OCR "
    "text. Your task is to identify the title, URL, description, and relevant "
    "tags for a bookmark. Be concise and accurate. If information is not "
    "present, leave fields empty."
)


@dataclass
class BookmarkMetadata:
    """Metadata extracted from a screenshot."""
    title: str = ""
    url: str = ""
    description: str = ""
    tags: str = ""  # comma-separated tags


class GeminiAnalyzer:
    """Analyzes OCR text using the Google Gemini API to extract bookmark metadata."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
    ):
        """
        Initialize the Gemini analyzer.

        Args:
            api_key: Optional API key. If not provided, falls back to
                ``GOOGLE_API_KEY`` or ``GEMINI_API_KEY`` env vars.
            model: Gemini model name (default: ``gemini-2.0-flash``).
        """
        if genai is None:
            raise ImportError(
                "google-generativeai is not installed. "
                "Install it with: pip install google-generativeai"
            )

        resolved_key = (
            api_key
            or os.getenv("GOOGLE_API_KEY")
            or os.getenv("GEMINI_API_KEY")
        )
        self.model_name = model
        self._model = None
        self.has_api_key = False

        if resolved_key:
            try:
                genai.configure(api_key=resolved_key)
                self._model = genai.GenerativeModel(
                    model_name=model,
                    generation_config={
                        "response_mime_type": "application/json",
                        "max_output_tokens": 1000,
                    },
                )
                self.has_api_key = True
                logger.info(f"Initialized GeminiAnalyzer with model {model}")
            except Exception as e:
                logger.warning(f"Failed to configure Gemini model {model}: {e}. Falling back to heuristic analysis.")
        else:
            logger.info("No Gemini API key provided. Operating in heuristic metadata extraction mode.")

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

        # Truncate very long OCR text to avoid excessive token usage.
        # Gemini 2.0 Flash supports 1M context, but we stay conservative.
        max_ocr_length = 8000  # chars
        if len(ocr_text) > max_ocr_length:
            logger.info(f"Truncating OCR text from {len(ocr_text)} to {max_ocr_length} chars")
            ocr_text = ocr_text[:max_ocr_length] + "..."

        if not self._model or not self.has_api_key:
            return self._heuristic_analysis(ocr_text, image_path)

        prompt = self._build_analysis_prompt(ocr_text, image_path)

        try:
            response = self._model.generate_content(
                [SYSTEM_INSTRUCTION, prompt]
            )
            response_text = response.text or ""
            metadata = self._parse_response(response_text)
            if not metadata.title and not metadata.url:
                # If Gemini returned empty data, use heuristic extraction
                return self._heuristic_analysis(ocr_text, image_path)
            logger.info(f"Extracted metadata: {metadata}")
            return metadata

        except Exception as e:
            logger.warning(f"Gemini API analysis failed: {e}. Falling back to heuristic extraction.")
            return self._heuristic_analysis(ocr_text, image_path)

    def _heuristic_analysis(self, ocr_text: str, image_path: str = "") -> BookmarkMetadata:
        """Extract metadata using heuristic rules and regex when AI is not configured or fails."""
        import re

        lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
        if not lines:
            title = Path(image_path).stem.replace('_', ' ').replace('-', ' ').title() if image_path else "Untitled Bookmark"
            return BookmarkMetadata(title=title)

        # 1. Look for URL
        url = ""
        url_match = re.search(r'https?://[^\s<>"{}|\\^`]+', ocr_text)
        if url_match:
            url = url_match.group(0).rstrip('.,;:)]>')
        else:
            www_match = re.search(r'(?:www\.)[^\s<>"{}|\\^`]+', ocr_text)
            if www_match:
                url = "https://" + www_match.group(0).rstrip('.,;:)]>')

        # 2. Extract Title (first line that looks like a title, ignoring pure URLs or timestamps)
        title_candidates = []
        for line in lines:
            clean = re.sub(r'https?://\S+', '', line).strip()
            if len(clean) >= 3 and not re.match(r'^\d+[\s:\-/.]*\d*$', clean):
                title_candidates.append(clean)

        if title_candidates:
            title = title_candidates[0]
            if len(title) > 90:
                title = title[:87] + "..."
        elif image_path:
            title = Path(image_path).stem.replace('_', ' ').replace('-', ' ').title()
        else:
            title = "Untitled Bookmark"

        # 3. Extract Description (next 1-2 lines)
        desc_lines = []
        for line in title_candidates[1:4]:
            if line != title and not line.startswith('http'):
                desc_lines.append(line)
        description = " ".join(desc_lines)
        if len(description) > 200:
            description = description[:197] + "..."

        # 4. Extract Tags from keywords
        text_lower = ocr_text.lower()
        keyword_map = [
            ("python", "python"), ("javascript", "javascript"), ("typescript", "typescript"),
            ("react", "react"), ("github", "github"), ("docker", "docker"), ("api", "api"),
            ("ai", "ai"), ("machine learning", "machine-learning"), ("tutorial", "tutorial"),
            ("guide", "guide"), ("documentation", "docs"), ("article", "article"),
            ("news", "news"), ("recipe", "recipe"), ("shopping", "shopping"),
            ("youtube", "video"), ("twitter", "social"), ("reddit", "community"),
            ("design", "design"), ("css", "css"), ("html", "web"), ("database", "database"),
            ("linux", "linux"), ("windows", "windows"), ("security", "security")
        ]
        tags = []
        for kw, tag in keyword_map:
            if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                tags.append(tag)

        if not tags and title:
            words = [w.lower() for w in re.findall(r'[a-zA-Z]{4,}', title)]
            if words:
                tags.append(words[0])

        return BookmarkMetadata(
            title=title,
            url=url,
            description=description,
            tags=",".join(tags[:5])
        )

    def _build_analysis_prompt(self, ocr_text: str, image_path: str) -> str:
        """Build the prompt for Gemini analysis."""
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
        """Parse Gemini's JSON response into BookmarkMetadata."""
        try:
            # With response_mime_type=application/json, the response is usually
            # already a clean JSON object, but be defensive in case the model
            # wraps it.
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                data = json.loads(json_str)
                return BookmarkMetadata(
                    title=str(data.get('title', '')).strip(),
                    url=str(data.get('url', '')).strip(),
                    description=str(data.get('description', '')).strip(),
                    tags=str(data.get('tags', '')).strip(),
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


# Backwards-compatible aliases — older code (and the CLI/web modules) imported
# ``ClaudeAnalyzer`` and the ``analyze_screenshot`` helper. Keep them around
# so the swap is non-breaking at the call sites.
ClaudeAnalyzer = GeminiAnalyzer


def analyze_screenshot(ocr_text: str, image_path: str = "", api_key: Optional[str] = None) -> BookmarkMetadata:
    """
    Analyze screenshot OCR text to extract bookmark metadata.

    Args:
        ocr_text: Text extracted from screenshot
        image_path: Path to the screenshot file
        api_key: Optional Gemini API key (falls back to GOOGLE_API_KEY env var)

    Returns:
        BookmarkMetadata with extracted information
    """
    analyzer = GeminiAnalyzer(api_key=api_key)
    return analyzer.analyze_ocr_text(ocr_text, image_path)
