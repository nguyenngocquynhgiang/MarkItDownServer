import os
import logging
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_classic.retrievers.multi_query import MultiQueryRetriever
from langchain_ollama import ChatOllama

# Khởi tạo thư mục chứa database cục bộ
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db")

# Thiết lập logging để theo dõi câu hỏi phụ do LLM sinh ra
logging.basicConfig()
logging.getLogger("langchain_classic.retrievers.multi_query").setLevel(logging.INFO)

def get_embedding_model():
    """Khởi tạo mô hình nhúng dùng chung"""
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# ==========================================
# HÀM 1: NẠP DỮ LIỆU (INGEST)
# ==========================================
def process_and_store_markdown(markdown_text: str, collection_name: str = "ielts_materials"):
    print("--- [INGEST] ĐANG NẠP DỮ LIỆU MỚI ---")
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    chunks = markdown_splitter.split_text(markdown_text)
    
    embeddings = get_embedding_model()
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=DB_DIR,
        collection_name=collection_name
    )
    print(f"[+] Đã băm nhỏ và lưu {len(chunks)} đoạn vào Collection: {collection_name}")
    return True

# ==========================================
# HÀM 2: TRUY VẤN CƠ BẢN (READ ONLY)
# ==========================================
def get_existing_vector_db(collection_name: str = "ielts_materials"):
    embeddings = get_embedding_model()
    vectorstore = Chroma(
        persist_directory=DB_DIR,
        embedding_function=embeddings,
        collection_name=collection_name
    )
    return vectorstore

# ==========================================
# HÀM 3: TRUY VẤN NÂNG CAO MULTI-QUERY
# ==========================================
def get_advanced_retriever(collection_name: str = "ielts_materials"):
    # Load database
    db = get_existing_vector_db(collection_name)
    
    # Kết nối với Local LLM (Ollama)
    llm = ChatOllama(model="qwen2") 
    
    # Tạo Advanced Retriever
    retriever = MultiQueryRetriever.from_llm(
        retriever=db.as_retriever(search_kwargs={"k": 3}),
        llm=llm
    )
    return retriever