document.addEventListener('DOMContentLoaded', () => {
    // 
    // ⚠️ PENTING: Ganti URL ini dengan URL backend Anda setelah di-deploy di Render.
    // 
    const BACKEND_URL = 'http://127.0.0.1:5001'; 

    // Mengambil referensi ke semua elemen HTML yang dibutuhkan
    const problemSelector = document.getElementById('problemSelector');
    const codeInput = document.getElementById('studentCode');
    const assessButton = document.getElementById('assessButton');
    const resultCard = document.getElementById('resultCard');
    const loadingDiv = document.getElementById('loading');
    const errorDiv = document.getElementById('error');
    const resultDiv = document.getElementById('result');

    /**
     * Fungsi untuk memuat daftar soal dari backend saat halaman pertama kali dibuka.
     */
    async function loadProblems() {
        try {
            const response = await fetch(`${BACKEND_URL}/problems`);
            if (!response.ok) {
                throw new Error('Gagal memuat daftar soal dari server.');
            }
            
            const problems = await response.json();
            problemSelector.innerHTML = '<option value="">-- Pilih Soal --</option>'; // Reset
            
            problems.forEach(problem => {
                const option = document.createElement('option');
                option.value = problem.id;
                option.textContent = `${problem.id}: ${problem.title}`;
                problemSelector.appendChild(option);
            });
            
            assessButton.disabled = false; // Aktifkan tombol "Nilai Kode" setelah soal berhasil dimuat
        } catch (e) {
            problemSelector.innerHTML = '<option>Gagal memuat soal</option>';
            showError(`Tidak dapat terhubung ke backend: ${e.message}`);
        }
    }

    /**
     * Event listener untuk tombol "Nilai Kode".
     * Mengirim data ke backend dan menangani respons.
     */
    assessButton.addEventListener('click', async () => {
        // Reset UI sebelum memulai
        resultCard.classList.remove('hidden');
        loadingDiv.classList.remove('hidden');
        errorDiv.classList.add('hidden');
        resultDiv.innerHTML = '';

        const problemId = problemSelector.value;
        const studentCode = codeInput.value;

        // Validasi input sederhana
        if (!problemId || !studentCode.trim()) {
            showError("Harap pilih soal dan isi kode siswa terlebih dahulu.");
            return;
        }

        try {
            // Mengirim request ke backend
            const response = await fetch(`${BACKEND_URL}/assess`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ problem_id: problemId, student_code: studentCode })
            });

            const resultData = await response.json();

            if (!response.ok) {
                 throw new Error(resultData.error || 'Terjadi kesalahan di server backend.');
            }
            
            // Jika berhasil, tampilkan hasilnya
            displayResult(resultData);

        } catch (e) {
            // Jika gagal, tampilkan pesan error
            showError(`Terjadi kesalahan: ${e.message}`);
        } finally {
            // Selalu sembunyikan loading indicator setelah selesai
            loadingDiv.classList.add('hidden');
        }
    });
    
    // --- FUNGSI-FUNGSI BANTU UNTUK MENAMPILKAN UI ---

    /**
     * Menampilkan pesan error di UI.
     * @param {string} message - Pesan error yang akan ditampilkan.
     */
    function showError(message) {
        loadingDiv.classList.add('hidden');
        errorDiv.textContent = message;
        errorDiv.classList.remove('hidden');
    }

    /**
     * Menampilkan hasil penilaian yang terstruktur di UI.
     * @param {object} data - Objek JSON hasil penilaian dari backend.
     */
    function displayResult(data) {
        resultDiv.innerHTML = `
            <div class="text-center mb-6">
                <p class="text-lg text-slate-600">Skor Akhir</p>
                <p class="text-6xl font-bold text-sky-600">${data.skor_akhir}</p>
            </div>
            <div class="space-y-4">
                <div>
                    <h3 class="text-xl font-semibold mb-2">Evaluasi per Kriteria</h3>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        ${renderCriteria(data.evaluasi_per_kriteria)}
                    </div>
                </div>
                <div>
                    <h3 class="text-xl font-semibold mb-2">Umpan Balik Kualitatif</h3>
                    <div class="bg-slate-50 p-4 rounded-lg border border-slate-200 space-y-3">
                        <div>
                            <h4 class="font-semibold text-green-700">✅ Poin Positif</h4>
                            <p class="text-slate-700">${data.umpan_balik_kualitatif.poin_positif}</p>
                        </div>
                         <div>
                            <h4 class="font-semibold text-amber-700">⚠️ Area Perbaikan</h4>
                            <p class="text-slate-700">${data.umpan_balik_kualitatif.area_perbaikan}</p>
                        </div>
                         <div>
                            <h4 class="font-semibold text-sky-700">💡 Saran Konkret</h4>
                            <p class="text-slate-700">${data.umpan_balik_kualitatif.saran_konkret}</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Helper untuk membuat HTML dari data kriteria penilaian.
     * @param {object} criteria - Objek evaluasi_per_kriteria dari JSON.
     * @returns {string} String HTML yang akan dirender.
     */
    function renderCriteria(criteria) {
        let html = '';
        const criteriaMap = {
            'kebenaran_fungsional': 'Kebenaran Fungsional',
            'efisiensi': 'Efisiensi & Optimalisasi',
            'keterbacaan': 'Keterbacaan & Gaya Kode',
            'praktik_baik': 'Praktik Pemrograman Baik'
        };
        for (const key in criteria) {
            html += `
                <div class="bg-slate-50 p-3 rounded-lg border border-slate-200">
                    <div class="flex justify-between items-center mb-1">
                        <h4 class="font-semibold">${criteriaMap[key] || key}</h4>
                        <span class="font-bold text-lg text-sky-600">${criteria[key].skor}</span>
                    </div>
                    <p class="text-sm text-slate-600">${criteria[key].catatan}</p>
                </div>
            `;
        }
        return html;
    }

    // Memanggil fungsi untuk memuat soal saat halaman pertama kali dibuka
    loadProblems();
});