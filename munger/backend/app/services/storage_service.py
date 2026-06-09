"""Storage service for managing source file uploads, downloads, and text extraction."""

import hashlib
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

from app.core.config import Settings

logger = logging.getLogger(__name__)


class StorageService:
    """Manages source file storage on the filesystem."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.sources_dir = Path(settings.sources_dir)
        self.wiki_dir = Path(settings.wiki_dir)
        self.schema_dir = Path(settings.schema_dir)

        # Ensure directories exist
        self.sources_dir.mkdir(parents=True, exist_ok=True)
        self.wiki_dir.mkdir(parents=True, exist_ok=True)
        (
            self.wiki_dir / "entities"
        ).mkdir(exist_ok=True)
        (
            self.wiki_dir / "concepts"
        ).mkdir(exist_ok=True)
        (
            self.wiki_dir / "models"
        ).mkdir(exist_ok=True)
        (
            self.wiki_dir / "summaries"
        ).mkdir(exist_ok=True)
        (
            self.wiki_dir / "analyses"
        ).mkdir(exist_ok=True)
        self.schema_dir.mkdir(parents=True, exist_ok=True)

    def _get_storage_path(self, filename: str) -> Path:
        """Generate a date-based storage path for a file."""
        now = datetime.utcnow()
        year_month = self.sources_dir / str(now.year) / f"{now.month:02d}"
        year_month.mkdir(parents=True, exist_ok=True)

        # Ensure unique filename
        base_name = Path(filename).stem
        ext = Path(filename).suffix
        counter = 0
        unique_name = f"source_{base_name}{ext}"
        while (year_month / unique_name).exists():
            counter += 1
            unique_name = f"source_{base_name}_{counter:03d}{ext}"

        return year_month / unique_name

    def _compute_hash(self, content: bytes) -> str:
        """Compute SHA-256 hash of file content."""
        return hashlib.sha256(content).hexdigest()

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    async def save_upload(self, file: UploadFile) -> dict:
        """Save an uploaded file to the sources directory.

        Returns dict with file_path, content_hash, file_size, file_type.
        """
        content = await file.read()
        file_size = len(content)
        content_hash = self._compute_hash(content)

        storage_path = self._get_storage_path(file.filename or "untitled")
        relative_path = storage_path.relative_to(self.sources_dir.parent)

        # Write file
        storage_path.write_bytes(content)

        file_type = self._detect_file_type(file.filename or "", file.content_type)

        logger.info(f"Saved upload: {storage_path} ({file_size} bytes, {file_type})")

        return {
            "file_path": str(relative_path),
            "absolute_path": str(storage_path),
            "content_hash": content_hash,
            "file_size": file_size,
            "file_type": file_type,
            "filename": file.filename or "untitled",
        }

    async def save_url_content(self, url: str, html_content: str) -> dict:
        """Save web-clipped content as an HTML file.

        Returns dict with file_path, content_hash, file_size, file_type.
        """
        content = html_content.encode("utf-8")
        file_size = len(content)
        content_hash = self._compute_hash(content)

        # Generate filename from URL
        safe_name = self._safe_filename_from_url(url)
        storage_path = self._get_storage_path(f"{safe_name}.html")
        relative_path = storage_path.relative_to(self.sources_dir.parent)

        storage_path.write_bytes(content)

        logger.info(f"Saved URL content: {storage_path} ({file_size} bytes)")

        return {
            "file_path": str(relative_path),
            "absolute_path": str(storage_path),
            "content_hash": content_hash,
            "file_size": file_size,
            "file_type": "html",
            "filename": f"{safe_name}.html",
            "source_url": url,
        }

    async def read_file(self, file_path: str) -> str:
        """Read file content as text."""
        full_path = self.get_file_path(file_path)
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {full_path}")
        try:
            return full_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Fallback for binary files
            return full_path.read_bytes().decode("utf-8", errors="replace")

    async def delete_file(self, file_path: str) -> None:
        """Delete a file from storage."""
        full_path = self.get_file_path(file_path)
        if full_path.exists():
            full_path.unlink()
            logger.info(f"Deleted file: {full_path}")

            # Clean up empty parent directories
            try:
                for parent in full_path.parents:
                    if parent == self.sources_dir.parent:
                        break
                    if parent.exists() and not any(parent.iterdir()):
                        parent.rmdir()
            except OSError:
                pass

    def get_file_path(self, file_path: str) -> Path:
        """Resolve a relative file path to an absolute path."""
        # If it's already relative to data dir
        path = Path(file_path)
        if path.is_absolute():
            return path
        # Try relative to data dir first
        data_path = Path(self.settings.data_dir) / path
        if data_path.exists():
            return data_path
        # Try relative to sources dir
        sources_path = self.sources_dir / path
        if sources_path.exists():
            return sources_path
        return data_path

    # ------------------------------------------------------------------
    # Text extraction
    # ------------------------------------------------------------------

    async def extract_text(self, file_path: str, file_type: str) -> str:
        """Extract plain text from a source file based on its type."""
        full_path = self.get_file_path(file_path)
        if not full_path.exists():
            raise FileNotFoundError(f"Source file not found: {full_path}")

        file_type = file_type.lower()

        try:
            if file_type == "pdf":
                return await self._extract_pdf(full_path)
            elif file_type in ("html", "htm", "url"):
                return await self._extract_html(full_path)
            elif file_type in ("md", "markdown"):
                return await self._extract_markdown(full_path)
            elif file_type in ("txt", "text"):
                return await self._extract_text_file(full_path)
            elif file_type in ("docx", "doc"):
                return await self._extract_docx(full_path)
            else:
                # Fallback: try to read as text
                logger.warning(f"Unknown file type '{file_type}', attempting text extraction")
                return await self._extract_text_file(full_path)
        except Exception as e:
            logger.error(f"Text extraction failed for {full_path}: {e}")
            raise TextExtractionError(f"Failed to extract text from {file_type}: {e}") from e

    async def _extract_pdf(self, file_path: Path) -> str:
        """Extract text from a PDF file using LiteParse, with PyPDF2 fallback."""
        import asyncio

        try:
            from liteparse import LiteParse

            def _parse_with_liteparse() -> str:
                parser = LiteParse(
                    ocr_enabled=self.settings.ocr_enabled,
                    ocr_language=self.settings.ocr_language,
                    tessdata_path=self.settings.tessdata_prefix,
                    quiet=True,
                )
                result = parser.parse(str(file_path))
                return getattr(result, "text", None) or ""

            text = await asyncio.to_thread(_parse_with_liteparse)
            if text.strip():
                return text
            logger.warning("LiteParse returned empty text for %s, falling back to PyPDF2", file_path)
        except ImportError:
            logger.warning("liteparse not installed, falling back to PyPDF2")
        except Exception as exc:
            logger.warning("LiteParse PDF extraction failed for %s: %s", file_path, exc)

        return await self._extract_pdf_pypdf2(file_path)

    async def _extract_pdf_pypdf2(self, file_path: Path) -> str:
        """Fallback PDF extraction using PyPDF2."""
        import asyncio

        def _parse_with_pypdf2() -> str:
            try:
                import PyPDF2
            except ImportError:
                logger.error("PyPDF2 not installed")
                raise TextExtractionError("PyPDF2 not installed") from None

            text_parts = []
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            return "\n\n".join(text_parts)

        try:
            return await asyncio.to_thread(_parse_with_pypdf2)
        except TextExtractionError:
            raise
        except Exception as e:
            raise TextExtractionError(f"PDF extraction failed: {e}") from e

    async def _extract_html(self, file_path: Path) -> str:
        """Extract text from an HTML file using trafilatura."""
        try:
            import trafilatura
        except ImportError:
            logger.warning("trafilatura not installed, falling back to beautifulsoup4")
            return await self._extract_html_fallback(file_path)

        try:
            html_content = file_path.read_text(encoding="utf-8")
            extracted = trafilatura.extract(
                html_content,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
            )
            return extracted or ""
        except Exception as e:
            logger.warning(f"trafilatura extraction failed, using fallback: {e}")
            return await self._extract_html_fallback(file_path)

    async def _extract_html_fallback(self, file_path: Path) -> str:
        """Fallback HTML extraction using BeautifulSoup."""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise TextExtractionError("BeautifulSoup not installed") from None

        html_content = file_path.read_text(encoding="utf-8")
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style", "nav", "header", "footer"]):
            element.decompose()

        # Get text
        text = soup.get_text(separator="\n", strip=True)

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        return "\n".join(chunk for chunk in chunks if chunk)

    async def _extract_markdown(self, file_path: Path) -> str:
        """Read markdown file, optionally converting to plain text."""
        content = file_path.read_text(encoding="utf-8")
        # Return markdown as-is; the LLM can handle markdown
        return content

    async def _extract_text_file(self, file_path: Path) -> str:
        """Read a plain text file."""
        return file_path.read_text(encoding="utf-8")

    async def _extract_docx(self, file_path: Path) -> str:
        """Extract text from a DOCX file."""
        try:
            import docx
        except ImportError:
            raise TextExtractionError("python-docx not installed") from None

        try:
            document = docx.Document(file_path)
            paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
            return "\n\n".join(paragraphs)
        except Exception as e:
            raise TextExtractionError(f"DOCX extraction failed: {e}") from e

    # ------------------------------------------------------------------
    # Wiki file operations
    # ------------------------------------------------------------------

    async def save_wiki_page(
        self, slug: str, content: str, page_type: str = "summary"
    ) -> Path:
        """Save a wiki page to the filesystem."""
        type_dir = self.wiki_dir / page_type
        type_dir.mkdir(exist_ok=True)

        file_path = type_dir / f"{slug}.md"
        file_path.write_text(content, encoding="utf-8")

        logger.info(f"Saved wiki page: {file_path}")
        return file_path

    async def read_wiki_page(self, slug: str, page_type: str = "summary") -> str:
        """Read a wiki page from the filesystem."""
        file_path = self.wiki_dir / page_type / f"{slug}.md"
        if not file_path.exists():
            raise FileNotFoundError(f"Wiki page not found: {file_path}")
        return file_path.read_text(encoding="utf-8")

    async def delete_wiki_page(self, slug: str, page_type: str = "summary") -> None:
        """Delete a wiki page from the filesystem."""
        file_path = self.wiki_dir / page_type / f"{slug}.md"
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted wiki page: {file_path}")

    async def append_to_log(self, entry: str) -> None:
        """Append an entry to the wiki log file."""
        log_path = self.wiki_dir / "log.md"
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"\n## {timestamp}\n\n{entry}\n"

        if log_path.exists():
            existing = log_path.read_text(encoding="utf-8")
            log_path.write_text(existing + log_entry, encoding="utf-8")
        else:
            log_path.write_text(f"# Munger Operation Log\n\n{log_entry}", encoding="utf-8")

    async def write_index(self, content: str) -> None:
        """Write the wiki index file."""
        index_path = self.wiki_dir / "index.md"
        index_path.write_text(content, encoding="utf-8")
        logger.info("Updated wiki index")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _detect_file_type(self, filename: str, content_type: Optional[str] = None) -> str:
        """Detect file type from filename and optional content type."""
        ext = Path(filename).suffix.lower()

        type_map = {
            ".pdf": "pdf",
            ".txt": "txt",
            ".md": "md",
            ".markdown": "md",
            ".html": "html",
            ".htm": "html",
            ".docx": "docx",
            ".doc": "doc",
        }

        if ext in type_map:
            return type_map[ext]

        # Try content type
        if content_type:
            ct_map = {
                "application/pdf": "pdf",
                "text/plain": "txt",
                "text/markdown": "md",
                "text/html": "html",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
            }
            if content_type in ct_map:
                return ct_map[content_type]

        return "unknown"

    def _safe_filename_from_url(self, url: str) -> str:
        """Generate a safe filename from a URL."""
        # Remove protocol
        name = url.replace("https://", "").replace("http://", "")
        # Remove common prefixes
        name = name.replace("www.", "")
        # Replace non-alphanumeric characters
        name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
        # Limit length
        if len(name) > 100:
            name = name[:100]
        return name.strip("_")


class TextExtractionError(Exception):
    """Raised when text extraction from a file fails."""
