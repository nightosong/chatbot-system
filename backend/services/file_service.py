"""
File Service - Handles file upload and processing
Supports text documents and media files
"""
from fastapi import UploadFile
import PyPDF2
import io
from typing import Dict, List


class FileService:
    """Service for processing uploaded files"""

    TEXT_EXTENSIONS = {".txt", ".md", ".pdf"}
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
    VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
    AUDIO_EXTENSIONS = {".mp3", ".wav", ".aac", ".flac", ".m4a", ".ogg"}
    SUPPORTED_EXTENSIONS = (
        TEXT_EXTENSIONS | IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | AUDIO_EXTENSIONS
    )
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
    
    # Token estimation: roughly 1 token ≈ 4 characters for English, 1 token ≈ 2 characters for Chinese
    MAX_CHARS_DIRECT = 20000  # ~5000 tokens, suitable for direct processing
    MAX_CHARS_WITH_SUMMARY = 80000  # ~20000 tokens, need summarization
    
    async def process_file(self, file: UploadFile) -> Dict[str, any]:
        """
        Process uploaded file and extract text content with intelligent handling
        
        Args:
            file: Uploaded file object
            
        Returns:
            Dictionary containing:
                - content: Processed text content (may be summarized)
                - original_length: Original text length
                - is_summarized: Whether content was summarized
                - processing_strategy: Strategy used (direct/chunked/summarized)
            
        Raises:
            ValueError: If file format is not supported or file is too large
        """
        if not file.filename:
            raise ValueError("Filename is required")

        # Check file extension
        filename = file.filename
        extension = self._get_extension(filename)

        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file format. Supported: {', '.join(sorted(self.SUPPORTED_EXTENSIONS))}"
            )

        # Read file content
        content_bytes = await file.read()

        # Check file size
        if len(content_bytes) > self.MAX_FILE_SIZE:
            raise ValueError(
                f"File too large. Maximum size: {self.MAX_FILE_SIZE / (1024*1024)}MB"
            )

        # Process based on file type
        if extension in self.IMAGE_EXTENSIONS:
            return self._process_media(
                filename=filename,
                extension=extension,
                content_type=file.content_type,
                file_size=len(content_bytes),
                media_type="image",
            )

        if extension in self.VIDEO_EXTENSIONS:
            return self._process_media(
                filename=filename,
                extension=extension,
                content_type=file.content_type,
                file_size=len(content_bytes),
                media_type="video",
            )

        if extension in self.AUDIO_EXTENSIONS:
            return self._process_media(
                filename=filename,
                extension=extension,
                content_type=file.content_type,
                file_size=len(content_bytes),
                media_type="audio",
            )

        if extension == ".pdf":
            text_content = self._process_pdf(content_bytes)
        else:  # .txt or .md
            text_content = self._process_text(content_bytes)

        # Apply intelligent processing based on content length
        return self._apply_intelligent_processing(text_content, filename)
    
    def _get_extension(self, filename: str) -> str:
        """Extract file extension"""
        if '.' not in filename:
            raise ValueError("File must have an extension")
        return '.' + filename.rsplit('.', 1)[1].lower()
    
    def _process_text(self, content_bytes: bytes) -> str:
        """Process text/markdown files"""
        try:
            # Try UTF-8 first
            return content_bytes.decode('utf-8')
        except UnicodeDecodeError:
            # Fallback to other encodings
            for encoding in ['gbk', 'gb2312', 'latin-1']:
                try:
                    return content_bytes.decode(encoding)
                except UnicodeDecodeError:
                    continue
            raise ValueError("Unable to decode file with supported encodings")
    
    def _process_pdf(self, content_bytes: bytes) -> str:
        """Process PDF files"""
        try:
            pdf_file = io.BytesIO(content_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text_parts = []
            for page_num, page in enumerate(pdf_reader.pages, 1):
                text = page.extract_text()
                if text.strip():
                    text_parts.append(f"--- Page {page_num} ---\n{text}")
            
            if not text_parts:
                raise ValueError("No text content found in PDF")
            
            return "\n\n".join(text_parts)
        except Exception as e:
            raise ValueError(f"Error processing PDF: {str(e)}")

    def _process_media(
        self,
        filename: str,
        extension: str,
        content_type: str | None,
        file_size: int,
        media_type: str,
    ) -> Dict[str, any]:
        """
        Process media file by generating metadata context.
        """
        content = (
            f"[Uploaded {media_type} file]\n"
            f"filename: {filename}\n"
            f"type: {media_type}\n"
            f"extension: {extension}\n"
            f"mime_type: {content_type or 'unknown'}\n"
            f"size_bytes: {file_size}\n\n"
            "Note: This system currently stores media metadata only. "
            "If analysis of media content is required, please use an external media analysis tool."
        )
        return {
            "content": content,
            "original_length": len(content),
            "is_summarized": False,
            "processing_strategy": "media_metadata",
            "filename": filename,
        }
    
    def _apply_intelligent_processing(self, text: str, filename: str) -> Dict[str, any]:
        """
        Apply intelligent processing strategy based on text length
        
        Strategy:
        - Small files (<20K chars): Direct processing
        - Medium files (20K-80K chars): Chunked with summary
        - Large files (>80K chars): Aggressive summarization
        
        Args:
            text: Extracted text content
            filename: Original filename
            
        Returns:
            Dictionary with processed content and metadata
        """
        original_length = len(text)
        
        # Strategy 1: Small files - direct processing
        if original_length <= self.MAX_CHARS_DIRECT:
            return {
                "content": text,
                "original_length": original_length,
                "is_summarized": False,
                "processing_strategy": "direct",
                "filename": filename
            }
        
        # Strategy 2: Medium files - chunked summary
        elif original_length <= self.MAX_CHARS_WITH_SUMMARY:
            summarized = self._create_smart_summary(text, target_length=15000)
            return {
                "content": summarized,
                "original_length": original_length,
                "is_summarized": True,
                "processing_strategy": "chunked_summary",
                "filename": filename,
                "compression_ratio": f"{len(summarized)/original_length:.1%}"
            }
        
        # Strategy 3: Large files - aggressive summarization
        else:
            summarized = self._create_smart_summary(text, target_length=10000)
            return {
                "content": summarized,
                "original_length": original_length,
                "is_summarized": True,
                "processing_strategy": "aggressive_summary",
                "filename": filename,
                "compression_ratio": f"{len(summarized)/original_length:.1%}"
            }
    
    def _create_smart_summary(self, text: str, target_length: int) -> str:
        """
        Create an intelligent summary of the text
        
        Uses a combination of:
        1. Beginning and end preservation
        2. Paragraph sampling
        3. Structure preservation
        
        Args:
            text: Full text content
            target_length: Target length for summary
            
        Returns:
            Summarized text with metadata
        """
        lines = text.split('\n')
        total_lines = len(lines)
        
        # Calculate how many lines to keep
        chars_per_line_avg = len(text) / max(total_lines, 1)
        target_lines = int(target_length / chars_per_line_avg)
        
        if target_lines >= total_lines:
            return text
        
        # Strategy: Keep beginning (30%), sample middle (40%), keep end (30%)
        beginning_lines = int(target_lines * 0.3)
        end_lines = int(target_lines * 0.3)
        middle_lines = target_lines - beginning_lines - end_lines
        
        # Extract sections
        beginning = lines[:beginning_lines]
        end = lines[-end_lines:] if end_lines > 0 else []
        
        # Sample middle section intelligently
        middle_start = beginning_lines
        middle_end = total_lines - end_lines
        middle_section = lines[middle_start:middle_end]
        
        if middle_lines > 0 and len(middle_section) > 0:
            # Sample evenly from middle
            step = len(middle_section) / middle_lines
            middle = [middle_section[int(i * step)] for i in range(middle_lines)]
        else:
            middle = []
        
        # Combine sections with markers
        summary_parts = [
            f"=== DOCUMENT SUMMARY (Original: {len(text)} chars, {total_lines} lines) ===\n",
            "\n=== Beginning Section ===\n",
            '\n'.join(beginning),
            f"\n\n=== Middle Section (Sampled from {len(middle_section)} lines) ===\n",
            '\n'.join(middle),
            "\n\n=== End Section ===\n",
            '\n'.join(end),
            "\n\n=== END OF SUMMARY ===\n",
            "\nNote: This is an automatically generated summary. Some content has been omitted."
        ]
        
        return ''.join(summary_parts)
    
    def chunk_text(self, text: str, chunk_size: int = 4000) -> List[str]:
        """
        Split long text into chunks for processing
        Useful for handling very long documents
        
        Args:
            text: Input text
            chunk_size: Maximum characters per chunk
            
        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        # Split by paragraphs
        paragraphs = text.split('\n\n')
        
        for para in paragraphs:
            para_size = len(para)
            
            if current_size + para_size <= chunk_size:
                current_chunk.append(para)
                current_size += para_size
            else:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_size = para_size
        
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
