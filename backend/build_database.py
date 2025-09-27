import os
import json
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.docstore.document import Document
from dotenv import load_dotenv

load_dotenv()

print("Memulai proses indexing...")

# Inisialisasi model embedding
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
all_docs = []
knowledge_base_dir = 'knowledge_base'

# Membaca semua file JSON dari knowledge base
for filename in os.listdir(knowledge_base_dir):
    if filename.endswith('.json'):
        filepath = os.path.join(knowledge_base_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Gabungkan semua info relevan menjadi satu teks untuk di-embed
            content = (
                f"Judul Soal: {data['title']}\n\n"
                f"Deskripsi Soal: {data['description']}\n\n"
                f"Solusi Ideal: {data['ideal_solution']}\n\n"
                f"Rubrik Penilaian: {json.dumps(data['rubric'], ensure_ascii=False, indent=2)}"
            )
            # Buat dokumen dengan metadata untuk filtering
            doc = Document(
                page_content=content,
                metadata={"problem_id": data['problem_id'], "title": data['title']}
            )
            all_docs.append(doc)
            print(f"Memproses file: {filename}")

if not all_docs:
    print("Tidak ada dokumen yang ditemukan di knowledge_base. Proses dihentikan.")
else:
    # Buat dan simpan Vector Database di folder 'chroma_db'
    db = Chroma.from_documents(
        all_docs, 
        embeddings, 
        persist_directory="./chroma_db"
    )
    print("\nDatabase berhasil dibuat di folder 'chroma_db'!")