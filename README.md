# MarkItDownServer - Advanced Document Retrieval System

Một hệ thống backend API mạnh mẽ được xây dựng bằng **FastAPI**, kết hợp khả năng chuyển đổi tài liệu đa định dạng sang Markdown và tích hợp **RAG (Retrieval-Augmented Generation)** nâng cao sử dụng **LangChain**, **ChromaDB** và **Local LLM (Ollama)**. 

Dự án này thể hiện kỹ năng xây dựng một ứng dụng AI/Backend hoàn chỉnh, từ việc xử lý file, tối ưu hóa API, cho đến việc ứng dụng các mô hình ngôn ngữ lớn (LLM) để tìm kiếm và truy xuất thông tin ngữ nghĩa.

##  Các tính năng chính

*   **Chuyển đổi đa định dạng sang Markdown**: Hỗ trợ upload và chuyển đổi hàng loạt các định dạng file khác nhau (PDF, DOCX, PPTX, hình ảnh, âm thanh, v.v.) sang Markdown sử dụng thư viện `markitdown` của Microsoft.
*   **Vector Database (ChromaDB)**: Tự động phân chia nội dung Markdown (Text Splitting dựa trên Header) và nhúng (Embed) thành các vector lưu trữ vào ChromaDB sử dụng `HuggingFaceEmbeddings` (`all-MiniLM-L6-v2`).
*   **Advanced RAG (Multi-Query Retriever)**: 
    *   Tích hợp hệ thống truy xuất thông tin nâng cao bằng LangChain.
    *   Sử dụng **Local LLM (Ollama với mô hình Qwen2)** để tự động sinh ra nhiều câu hỏi phụ (sub-queries) từ câu hỏi gốc của người dùng, giúp tăng độ chính xác và phủ rộng ngữ nghĩa khi tìm kiếm trong Vector DB.
*   **API Hiện đại & Bảo mật**:
    *   Xây dựng bằng **FastAPI** cho hiệu năng cao và tự động generate tài liệu API (Swagger UI).
    *   Tích hợp Middleware bảo mật (CORS, Security Headers).
    *   Hỗ trợ Rate Limiting (giới hạn request) để bảo vệ server khỏi các đợt tấn công DDoS/Spam (thông qua `slowapi`).
    *   Quản lý cấu hình qua Environment Variables (số lượng Worker, Port, v.v.).

##  Tech Stack & Thư viện sử dụng

*   **Backend Framework**: Python 3.10+, FastAPI, Uvicorn
*   **AI / RAG Framework**: LangChain (`langchain-text-splitters`, `langchain-huggingface`, `langchain-community`, `langchain-ollama`)
*   **Vector Database**: ChromaDB
*   **LLM & Embeddings**: Ollama (Qwen2), HuggingFace (`all-MiniLM-L6-v2`, `sentence-transformers`)
*   **Document Processing**: `markitdown` (Microsoft)

##  Cấu trúc thư mục

```text
MarkItDownServer/
├── app.py                 # File chính chạy FastAPI server, định nghĩa các API endpoints
├── utils/
│   └── vector_handler.py  # Xử lý logic LangChain, ChromaDB, và Ollama
├── chroma_db/             # Thư mục lưu trữ dữ liệu Vector Database (Local)
├── requirements.txt       # Danh sách dependencies của dự án
└── Dockerfile             # (Tùy chọn) Cấu hình để chạy server trong container
```

##  API Endpoints

*   `GET /`: Trả về thông tin cơ bản của service.
*   `GET /health`: Kiểm tra trạng thái hoạt động của server.
*   `POST /process_file`: API upload file. File sau khi upload sẽ được:
    1. Chuyển đổi sang Markdown.
    2. Băm nhỏ (Chunking) theo các thẻ Header (`#`, `##`, `###`).
    3. Nhúng (Embedding) và lưu vào ChromaDB (collection `ielts_materials`).
*   `POST /query`: Nhận câu hỏi từ người dùng, dùng LLM sinh ra các câu hỏi phụ, tìm kiếm trong Vector DB và trả về các đoạn nội dung liên quan nhất.

##  Hướng dẫn cài đặt và chạy thử nghiệm

### 1. Yêu cầu hệ thống
*   Python 3.10 trở lên.
*   Cài đặt [Ollama](https://ollama.com/) và tải mô hình Qwen2:
    ```bash
    ollama run qwen2
    ```

### 2. Cài đặt dependencies
Tạo môi trường ảo và cài đặt các thư viện cần thiết:

```bash
python -m venv venv
source venv/bin/activate  # (Trên Windows: venv\Scripts\activate)
pip install -r requirements.txt
```

*(Lưu ý: Nếu cần dùng tính năng Rate Limit, hãy chạy thêm `pip install slowapi`)*

### 3. Khởi chạy Server
Khởi chạy FastAPI server:

```bash
python app.py
```
Mặc định server sẽ chạy tại: `http://localhost:8490`

*   Truy cập Swagger UI (Tài liệu API): `http://localhost:8490/docs`

## Điểm nổi bật cho Nhà tuyển dụng (Why this project?)

Dự án này không chỉ là một ứng dụng CRUD thông thường mà còn giải quyết được bài toán xây dựng luồng xử lý AI (AI Pipeline) hoàn chỉnh:
1.  **Kiến trúc RAG**: Hiểu và triển khai được mô hình RAG - xu hướng cốt lõi trong việc xây dựng các ứng dụng GenAI doanh nghiệp (Enterprise AI).
2.  **Khả năng tối ưu tìm kiếm**: Sử dụng `MultiQueryRetriever` chứng tỏ sự am hiểu về hạn chế của tìm kiếm vector thuần túy (lexical/semantic gap) và cách dùng LLM để bù đắp.
3.  **Clean Code & Modular Design**: Tách biệt rõ ràng tầng API (FastAPI) và tầng logic xử lý AI (LangChain/VectorDB).
4.  **Tư duy hệ thống**: Áp dụng các phương pháp bảo mật (Security headers), tối ưu luồng (Rate limiting), phân mảnh file (Chunking strategy dựa trên Markdown headers thay vì cắt ký tự mù quáng).
5.  **Kinh nghiệm xử lý sự cố thực tế**: Hiểu rõ và xử lý triệt để các vấn đề Encoding (UTF-8 vs cp1252) thường gặp khi triển khai hệ thống đa nền tảng (Windows/Linux), giúp log và hệ thống chạy mượt mà với dữ liệu tiếng Việt.

This project is built upon the original [MarkItDownServer] by El Bruno, licensed under the MIT License
