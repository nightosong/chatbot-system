"""
Unit tests for File Service
"""

import pytest  # type: ignore
import io
from fastapi import UploadFile  # type: ignore
from services.file_service import FileService


@pytest.fixture
def file_service():
    """Create FileService instance"""
    return FileService()


@pytest.mark.asyncio
async def test_process_text_file(file_service):
    """Test processing text file"""
    content = "Hello, this is a test file."
    file_bytes = content.encode("utf-8")

    upload_file = UploadFile(filename="test.txt", file=io.BytesIO(file_bytes))

    result = await file_service.process_file(upload_file)
    assert result["content"] == content
    assert result["is_summarized"] == False
    assert result["processing_strategy"] == "direct"


@pytest.mark.asyncio
async def test_process_markdown_file(file_service):
    """Test processing markdown file"""
    content = "# Test Markdown\n\nThis is a **test**."
    file_bytes = content.encode("utf-8")

    upload_file = UploadFile(filename="test.md", file=io.BytesIO(file_bytes))

    result = await file_service.process_file(upload_file)
    assert result["content"] == content
    assert result["is_summarized"] == False


@pytest.mark.asyncio
async def test_unsupported_file_format(file_service):
    """Test error handling for unsupported format"""
    upload_file = UploadFile(filename="test.docx", file=io.BytesIO(b"fake content"))

    with pytest.raises(ValueError) as exc_info:
        await file_service.process_file(upload_file)

    assert "Unsupported file format" in str(exc_info.value)


@pytest.mark.asyncio
async def test_file_too_large(file_service):
    """Test error handling for large files"""
    # Create a file larger than 20MB
    large_content = b"x" * (21 * 1024 * 1024)

    upload_file = UploadFile(filename="large.txt", file=io.BytesIO(large_content))

    with pytest.raises(ValueError) as exc_info:
        await file_service.process_file(upload_file)

    assert "File too large" in str(exc_info.value)


def test_get_extension(file_service):
    """Test extension extraction"""
    assert file_service._get_extension("test.txt") == ".txt"
    assert file_service._get_extension("test.PDF") == ".pdf"
    assert file_service._get_extension("file.name.md") == ".md"
    assert file_service._get_extension("photo.JPEG") == ".jpeg"
    assert file_service._get_extension("clip.MP4") == ".mp4"


def test_get_extension_no_extension(file_service):
    """Test error for file without extension"""
    with pytest.raises(ValueError):
        file_service._get_extension("noextension")


def test_chunk_text_small(file_service):
    """Test chunking small text"""
    text = "Short text"
    chunks = file_service.chunk_text(text, chunk_size=100)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_large(file_service):
    """Test chunking large text"""
    # Create text larger than chunk size
    paragraphs = ["Paragraph " + str(i) * 100 for i in range(10)]
    text = "\n\n".join(paragraphs)

    chunks = file_service.chunk_text(text, chunk_size=500)
    assert len(chunks) > 1

    # Verify all content is preserved
    reconstructed = "\n\n".join(chunks)
    # Content should be mostly preserved (may have extra newlines)
    assert len(reconstructed) >= len(text) * 0.9


@pytest.mark.asyncio
async def test_medium_file_summarization(file_service):
    """Test summarization for medium-sized files"""
    # Create a file with 30,000 characters (should trigger chunked_summary)
    content = "This is a test paragraph.\n\n" * 1000  # ~30KB
    file_bytes = content.encode("utf-8")

    upload_file = UploadFile(filename="medium.txt", file=io.BytesIO(file_bytes))

    result = await file_service.process_file(upload_file)
    assert result["is_summarized"] == True
    assert result["processing_strategy"] == "chunked_summary"
    assert len(result["content"]) < result["original_length"]
    assert "DOCUMENT SUMMARY" in result["content"]


@pytest.mark.asyncio
async def test_large_file_aggressive_summarization(file_service):
    """Test aggressive summarization for large files"""
    # Create a file with 100,000 characters (should trigger aggressive_summary)
    content = "This is a test paragraph with more content.\n\n" * 2000  # ~100KB
    file_bytes = content.encode("utf-8")

    upload_file = UploadFile(filename="large.txt", file=io.BytesIO(file_bytes))

    result = await file_service.process_file(upload_file)
    assert result["is_summarized"] == True
    assert result["processing_strategy"] == "aggressive_summary"
    assert len(result["content"]) < result["original_length"]
    assert len(result["content"]) < 15000  # Should be around 10KB


def test_smart_summary(file_service):
    """Test smart summary generation"""
    # Create a long text
    lines = [f"Line {i}: Some content here" for i in range(1000)]
    text = "\n".join(lines)

    summary = file_service._create_smart_summary(text, target_length=5000)

    # Summary should be shorter
    assert len(summary) < len(text)
    # Should contain markers
    assert "DOCUMENT SUMMARY" in summary
    assert "Beginning Section" in summary
    assert "Middle Section" in summary
    assert "End Section" in summary


@pytest.mark.asyncio
async def test_process_image_file(file_service):
    """Test processing image file as media metadata"""
    image_bytes = b"\x89PNG\r\n\x1a\nfakepngdata"
    upload_file = UploadFile(
        filename="test.png", file=io.BytesIO(image_bytes), headers={"content-type": "image/png"}
    )

    result = await file_service.process_file(upload_file)
    assert result["is_summarized"] is False
    assert result["processing_strategy"] == "media_metadata"
    assert "[Uploaded image file]" in result["content"]
    assert "filename: test.png" in result["content"]


@pytest.mark.asyncio
async def test_process_audio_file(file_service):
    """Test processing audio file as media metadata"""
    audio_bytes = b"ID3fake_mp3_data"
    upload_file = UploadFile(
        filename="test.mp3", file=io.BytesIO(audio_bytes), headers={"content-type": "audio/mpeg"}
    )

    result = await file_service.process_file(upload_file)
    assert result["is_summarized"] is False
    assert result["processing_strategy"] == "media_metadata"
    assert "[Uploaded audio file]" in result["content"]
    assert "filename: test.mp3" in result["content"]
