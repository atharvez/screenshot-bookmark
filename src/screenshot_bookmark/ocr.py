"""OCR extraction module for screenshots."""
import logging
import os
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import OCR libraries
try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True

    # Try to find tesseract executable on Windows
    if sys.platform == 'win32':
        # Common Tesseract installation paths on Windows
        tesseract_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            r'C:\Tesseract-OCR\tesseract.exe',
            r'C:\Users\7atha\AppData\Local\Programs\Tesseract-OCR\tesseract.exe',
        ]
        for tpath in tesseract_paths:
            if os.path.exists(tpath):
                pytesseract.pytesseract.tesseract_cmd = tpath
                logger.info(f"Found Tesseract at: {tpath}")
                break
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("pytesseract or PIL not installed. OCR functionality will be limited.")

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    logger.warning("EasyOCR not installed. Fallback OCR option not available.")


class OCRProcessor:
    """Handles OCR processing of images."""

    def __init__(self, lang: str = 'eng', mock: bool = False):
        """
        Initialize OCR processor.

        Args:
            lang: Language code for OCR (default: 'eng' for English)
            mock: If True, use mock OCR for testing without installed backends
        """
        self.lang = lang
        self.mock = mock

        if mock:
            self.tesseract_available = False
            logger.info("Using MOCK OCR (for testing)")
        elif TESSERACT_AVAILABLE:
            self.tesseract_available = True
            logger.info("Using Tesseract OCR")
        elif EASYOCR_AVAILABLE:
            self.tesseract_available = False
            self.easyocr_reader = easyocr.Reader([lang])
            logger.info("Using EasyOCR")
        else:
            self.tesseract_available = False
            logger.warning("No OCR backend available. Install pytesseract or easyocr, or use mock=True for testing.")

    def extract_text(self, image_path: str) -> str:
        """
        Extract text from an image file.

        Args:
            image_path: Path to the image file

        Returns:
            Extracted text as string
        """
        if self.mock:
            return self._extract_mock(image_path)

        if not TESSERACT_AVAILABLE and not EASYOCR_AVAILABLE:
            logger.error("No OCR backend available. Install pytesseract, easyocr, or use mock=True")
            return ""

        image_path = Path(image_path)
        if not image_path.exists():
            logger.error(f"Image file not found: {image_path}")
            return ""

        try:
            if TESSERACT_AVAILABLE:
                return self._extract_with_tesseract(image_path)
            elif EASYOCR_AVAILABLE:
                return self._extract_with_easyocr(image_path)
        except Exception as e:
            logger.exception(f"OCR failed for {image_path}: {e}")
            return ""

        return ""

    def _extract_mock(self, image_path: str) -> str:
        """Mock OCR for testing - returns filename-based text."""
        image_path_obj = Path(image_path)
        logger.info(f"Mock OCR processing: {image_path_obj.name}")
        # Return a realistic mock based on the filename
        name = image_path_obj.stem.lower()
        if 'screenshot' in name or 'screen' in name:
            return f"""Sample Screenshot Content
Title: Example Article from {name}
URL: https://example.com/article/{name}
Description: This is mock OCR text extracted from {image_path_obj.name}.
In real usage, this would be the actual text from the screenshot image."""
        return f"Mock text from {image_path_obj.name}"

    def _extract_with_tesseract(self, image_path: Path) -> str:
        """Extract text using Tesseract."""
        try:
            image = Image.open(image_path)
            # Optional: preprocess image for better OCR
            # image = image.convert('L')  # grayscale
            text = pytesseract.image_to_string(image, lang=self.lang)
            return text.strip()
        except Exception as e:
            logger.exception(f"Tesseract OCR failed: {e}")
            raise

    def _extract_with_easyocr(self, image_path: Path) -> str:
        """Extract text using EasyOCR."""
        try:
            results = self.easyocr_reader.readtext(str(image_path))
            # Extract just the text, ignoring bounding boxes and confidence
            text = ' '.join([result[1] for result in results])
            return text.strip()
        except Exception as e:
            logger.exception(f"EasyOCR failed: {e}")
            raise


def extract_text_from_image(image_path: str, lang: str = 'eng', mock: bool = False) -> str:
    """
    Convenience function to extract text from an image.

    Args:
        image_path: Path to the image file
        lang: Language code for OCR (default: 'eng')
        mock: If True, use mock OCR for testing

    Returns:
        Extracted text as string
    """
    processor = OCRProcessor(lang=lang, mock=mock)
    return processor.extract_text(image_path)


# Tesseract installation instructions
def get_tesseract_install_instructions() -> str:
    """Get Tesseract installation instructions for the current platform."""
    import sys
    if sys.platform == 'win32':
        return """Tesseract OCR Installation (Windows):
1. Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
2. Run the installer (default path: C:\\Program Files\\Tesseract-OCR)
3. Add to PATH or set TESSERACT_CMD environment variable
4. Verify: tesseract --version"""
    elif sys.platform == 'darwin':
        return """Tesseract OCR Installation (macOS):
1. brew install tesseract
2. For language data: brew install tesseract-lang
3. Verify: tesseract --version"""
    else:
        return """Tesseract OCR Installation (Linux):
1. Ubuntu/Debian: sudo apt-get install tesseract-ocr
2. Fedora: sudo dnf install tesseract
3. Arch: sudo pacman -S tesseract
4. Verify: tesseract --version"""