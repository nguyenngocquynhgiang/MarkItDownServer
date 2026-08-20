import logging
import os
import sys

# Force UTF-8 encoding for standard output (Fixes Windows charmap error)
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from markitdown import MarkItDown
from utils.vector_handler import process_and_store_markdown, get_existing_vector_db, get_advanced_retriever

# Optional rate limiting support
try:
    # pyrefly: ignore [missing-import]
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    RATE_LIMIT_AVAILABLE = True
except ImportError:
    RATE_LIMIT_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Environment-based configuration
WORKERS = int(os.getenv('WORKERS', '1'))
ENABLE_RATE_LIMIT = os.getenv('ENABLE_RATE_LIMIT', 'false').lower() == 'true'
RATE_LIMIT = os.getenv('RATE_LIMIT', '60/minute')  # Default: 60 requests per minute

# FastAPI app with metadata
app = FastAPI(
    title="MarkItDown Server",
    description="API for converting various document formats to Markdown",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure rate limiting if enabled and available
if ENABLE_RATE_LIMIT and RATE_LIMIT_AVAILABLE:
    limiter = Limiter(key_func=get_remote_address, default_limits=[RATE_LIMIT])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    logger.info(f"Rate limiting enabled: {RATE_LIMIT}")
elif ENABLE_RATE_LIMIT and not RATE_LIMIT_AVAILABLE:
    logger.warning("Rate limiting requested but slowapi not installed. Install with: pip install slowapi")
else:
    logger.info("Rate limiting disabled")

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

# Configuration
ALLOWED_EXTENSIONS = {
    # Document formats
    'doc', 'docx', 'ppt', 'pptx', 'pdf', 'xls', 'xlsx', 'odt', 'ods', 'odp', 'txt',
    # Image formats
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp', 'svg',
    # Audio formats
    'mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a', 'wma'
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Response models
class QueryRequest(BaseModel):
    question: str
    top_k: int = 3

class MarkdownResponse(BaseModel):
    markdown: str

class ErrorResponse(BaseModel):
    error: str

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    service: str
    version: str
    workers: int
    rate_limit_enabled: bool
    rate_limit: str | None

def allowed_file(filename: str | None) -> bool:
    """Check if the uploaded file has an allowed extension.
    
    Args:
        filename: Name of the file to check
        
    Returns:
        True if file extension is allowed, False otherwise
    """
    if not filename:
        return False
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def convert_to_md(filepath: str) -> str:
    """Convert a file to Markdown format.
    
    Args:
        filepath: Path to the file to convert
        
    Returns:
        Markdown content as string
    """
    logger.info(f"Converting file: {filepath}")
    markitdown = MarkItDown()
    result = markitdown.convert(filepath)
    logger.info(f"Conversion result: {result.text_content[:100]}")
    return result.text_content

@app.get("/", summary="Root endpoint", description="Returns service information")
def read_root():
    """Get service information and available endpoints."""
    return {
        "service": "MarkItDown Server",
        "description": "API for converting documents to Markdown",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "process": "/process_file"
        }
    }

@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check endpoint",
    description="Returns the health status of the service with concurrency information"
)
def health_check():
    """Get service health status."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "MarkItDown Server",
        "version": "1.0.0",
        "workers": WORKERS,
        "rate_limit_enabled": ENABLE_RATE_LIMIT and RATE_LIMIT_AVAILABLE,
        "rate_limit": RATE_LIMIT if (ENABLE_RATE_LIMIT and RATE_LIMIT_AVAILABLE) else None
    }

@app.post(
    '/process_file',
    response_model=MarkdownResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file type or file too large"},
        413: {"model": ErrorResponse, "description": "File too large"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Convert document to Markdown",
    description="Upload a document file and receive its content in Markdown format"
)
async def process_file(
    request: Request,
    file: UploadFile = File(..., description="Document file to convert to Markdown")
) -> MarkdownResponse:
    """Process an uploaded file and convert it to Markdown."""
    temp_file_path = None
    
    # Validate filename
    if not file.filename:
        return JSONResponse(
            content={'error': 'Filename is required'}, 
            status_code=400
        )
    
    if not allowed_file(file.filename):
        return JSONResponse(
            content={'error': f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'}, 
            status_code=400
        )
    
    try:
        file_content = await file.read()
        
        # Validate file size
        if len(file_content) > MAX_FILE_SIZE:
            return JSONResponse(
                content={'error': f'File too large. Maximum size: {MAX_FILE_SIZE / (1024*1024):.0f}MB'}, 
                status_code=413
            )
        
        # Validate file is not empty
        if len(file_content) == 0:
            return JSONResponse(
                content={'error': 'File is empty'}, 
                status_code=400
            )
        
        # Save the file to a temporary directory with proper extension
        with tempfile.NamedTemporaryFile(
            delete=False, 
            suffix=Path(file.filename).suffix
        ) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
            logger.info(f"Temporary file path: {temp_file_path}")
        
        # Convert the file to markdown
        markdown_content = convert_to_md(temp_file_path)
        logger.info("File converted to markdown successfully")
        
        # Gọi luồng INGEST: Băm nhỏ và lưu mới/lưu thêm vào ChromaDB
        process_and_store_markdown(markdown_content, collection_name="ielts_materials")
        
        return JSONResponse(content={
            "status": "success",
            "message": "File đã được chuyển đổi sang Markdown và nạp vào Vector DB thành công!",
            "collection": "ielts_materials"
        })
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return JSONResponse(content={'error': str(e)}, status_code=500)
        
    finally:
        # Ensure the temporary file is deleted
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            logger.info(f"Temporary file deleted: {temp_file_path}")

@app.post("/query")
async def query_documents(request: QueryRequest):
    try:
        # Sử dụng Advanced Retriever thay vì Vector DB thuần
        advanced_retriever = get_advanced_retriever(collection_name="ielts_materials")
        
        # Hàm invoke() sẽ tự động làm mọi việc: gọi LLM tạo câu hỏi -> tìm DB -> gộp kết quả
        relevant_docs = advanced_retriever.invoke(request.question)
        
        results = []
        for doc in relevant_docs:
            results.append({
                "content": doc.page_content,
                "metadata": doc.metadata
            })
            
        return {
            "status": "success",
            "query": request.question,
            "total_docs_found": len(results), # Số lượng có thể lớn hơn top_k do tìm từ nhiều câu
            "results": results
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Lỗi xảy ra khi truy vấn dữ liệu: {str(e)}"
        }


if __name__ == "__main__":
    import uvicorn
    
    # Log startup configuration
    logger.info(f"Starting MarkItDown Server with {WORKERS} worker(s)")
    if ENABLE_RATE_LIMIT and RATE_LIMIT_AVAILABLE:
        logger.info(f"Rate limiting: {RATE_LIMIT}")
    
    # Run with configured number of workers
    # When workers > 1, we need to pass the app as a string
    if WORKERS > 1:
        uvicorn.run(
            "app:app",
            host="0.0.0.0", 
            port=int(os.getenv('PORT', '8490')),
            workers=WORKERS
        )
    else:
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=int(os.getenv('PORT', '8490'))
        )     