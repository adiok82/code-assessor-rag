import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Import komponen LangChain yang modern dan stabil
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI

# Memuat environment variables dari file .env (berisi GOOGLE_API_KEY)
load_dotenv()

# --- 1. Konfigurasi Aplikasi Flask ---
app = Flask(__name__)
# Mengizinkan Cross-Origin Resource Sharing (CORS) agar frontend bisa mengakses backend
CORS(app)

# --- 2. Inisialisasi Model dan Database (dilakukan sekali saat server start) ---
print("🚀 Memuat model AI dan Vector Database...")
try:
    # Inisialisasi model embedding untuk mencari data di database
    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
    
    # Muat Vector Database yang sudah dibuat oleh build_database.py
    db = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    
    # Buat retriever untuk mengambil dokumen relevan dari database.
    # 'mmr' (Maximal Marginal Relevance) dipilih untuk hasil yang relevan dan beragam.
    retriever = db.as_retriever(search_type="mmr", search_kwargs={'k': 1, 'fetch_k': 5})
    
    # Inisialisasi model LLM (Gemini 1.5 Flash)
    # Meminta output dalam format JSON secara langsung ke model.
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash-latest",
        temperature=0.1, # Suhu rendah untuk jawaban yang konsisten dan faktual
        generation_config={"response_mime_type": "application/json"}
    )
    print("✅ Model dan Database siap digunakan.")
except Exception as e:
    print(f"❌ Gagal memuat model atau database: {e}")
    # Jika gagal, hentikan aplikasi agar tidak berjalan dalam kondisi error
    exit()

# --- 3. Definisi Prompt Template ---
# Ini adalah template yang akan menginstruksikan AI cara menilai kode.
prompt_template = (
    "Anda adalah seorang asisten pengajar ahli untuk mata pelajaran pemrograman C++ yang sangat teliti.\n"
    "Tugas Anda adalah menilai kode siswa secara objektif berdasarkan konteks soal dan rubrik yang diberikan.\n\n"
    "[KONTEKS SOAL, SOLUSI IDEAL, DAN RUBRIK PENILAIAN]:\n"
    "{context}\n\n"
    "[KODE YANG DITULIS SISWA]:\n"
    "```cpp\n"
    "{student_code}\n"
    "```\n\n"
    "[INSTRUKSI]:\n"
    "1. Analisis kode siswa dan bandingkan dengan konteks yang diberikan.\n"
    "2. Berikan skor numerik (0-100) untuk setiap kriteria dalam rubrik.\n"
    "3. Hitung skor akhir berdasarkan bobot yang tersirat dalam rubrik.\n"
    "4. Berikan umpan balik kualitatif yang jelas, positif, dan konstruktif.\n\n"
    "[FORMAT OUTPUT]:\n"
    "Berikan jawaban Anda HANYA dalam format JSON yang valid tanpa teks atau markdown formatting tambahan. Strukturnya harus sebagai berikut:\n"
    "{\n"
    '  "skor_akhir": "<nilai numerik antara 0-100>",\n'
    '  "evaluasi_per_kriteria": {\n'
    '    "kebenaran_fungsional": { "skor": "<nilai 0-100>", "catatan": "<penjelasan singkat>" },\n'
    '    "efisiensi": { "skor": "<nilai 0-100>", "catatan": "<penjelasan singkat>" },\n'
    '    "keterbacaan": { "skor": "<nilai 0-100>", "catatan": "<penjelasan singkat>" },\n'
    '    "praktik_baik": { "skor": "<nilai 0-100>", "catatan": "<penjelasan singkat>" }\n'
    '  },\n'
    '  "umpan_balik_kualitatif": {\n'
    '    "poin_positif": "<jelaskan apa yang sudah baik dari kode siswa>",\n'
    '    "area_perbaikan": "<jelaskan aspek utama yang perlu diperbaiki>",\n'
    '    "saran_konkret": "<berikan 1-2 saran langkah perbaikan yang bisa dilakukan siswa>"\n'
    '  }\n'
    "}"
)
prompt = ChatPromptTemplate.from_template(prompt_template)

# --- 4. Endpoint API ---

@app.route('/problems', methods=['GET'])
def get_problems():
    """Endpoint untuk memberikan daftar soal yang ada di knowledge_base."""
    problems = []
    knowledge_base_dir = 'knowledge_base'
    if not os.path.exists(knowledge_base_dir):
        return jsonify({"error": "Folder knowledge_base tidak ditemukan"}), 500
        
    for filename in os.listdir(knowledge_base_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(knowledge_base_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    problems.append({"id": data.get('problem_id'), "title": data.get('title')})
            except Exception as e:
                print(f"Gagal membaca file {filename}: {e}")
                continue # Lanjut ke file berikutnya jika ada error
    return jsonify(sorted(problems, key=lambda x: x['id']))


@app.route('/assess', methods=['POST'])
def assess_code():
    """Endpoint utama untuk melakukan penilaian kode menggunakan RAG."""
    data = request.json
    problem_id = data.get('problem_id')
    student_code = data.get('student_code')

    if not problem_id or not student_code:
        return jsonify({"error": "Parameter 'problem_id' dan 'student_code' dibutuhkan"}), 400

    try:
        # --- 5. RAG Chain dengan LCEL (LangChain Expression Language) ---
        
        # Fungsi sederhana untuk memformat hasil dari retriever
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)

        # Merangkai alur kerja RAG menggunakan LCEL
        rag_chain = (
            # Langkah 1: Ambil input 'student_code' dan 'problem_id'
            #            Gunakan 'problem_id' untuk mengambil 'context' dari retriever.
            {"context": retriever | format_docs, "student_code": RunnablePassthrough()}
            # Langkah 2: Masukkan 'context' dan 'student_code' ke dalam prompt
            | prompt
            # Langkah 3: Kirim prompt ke LLM
            | llm
            # Langkah 4: Parse output dari LLM sebagai JSON
            | JsonOutputParser()
        )
        
        # Menjalankan RAG chain dengan input dari request
        result = rag_chain.invoke({"student_code": student_code, "problem_id": problem_id})
        
        return jsonify(result)

    except json.JSONDecodeError:
        # Error ini terjadi jika LLM tidak mengembalikan JSON yang valid
        print("❌ Error: LLM tidak mengembalikan JSON yang valid.")
        return jsonify({"error": "Gagal mem-parsing output dari model AI. Coba lagi."}), 500
    except Exception as e:
        # Menangani error umum lainnya
        print(f"❌ Error tidak terduga: {e}")
        return jsonify({"error": "Terjadi kesalahan internal pada server."}), 500

# --- 6. Menjalankan Server ---
if __name__ == '__main__':
    # Menjalankan server Flask di port 5001 dalam mode debug
    app.run(debug=True, port=5001)