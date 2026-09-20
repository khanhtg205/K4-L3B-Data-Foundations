# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Trần Gia Khánh
**Nhóm:** manngusidan
**Ngày:** 20/09/2026

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Độ tương tự cosine cao (tiến gần về 1.0) nghĩa là góc giữa hai vector biểu diễn văn bản trong không gian vector rất nhỏ, thể hiện hai câu/đoạn văn bản có sự tương đồng sâu sắc về mặt ngữ nghĩa và chủ đề, bất kể độ dài hay từ vựng cụ thể có thể khác nhau.

**Ví dụ có độ tương tự CAO:**
- Câu A: "Người mua có quyền yêu cầu hoàn trả đầy đủ tiền nếu sản phẩm bị lỗi hoặc bể vỡ khi nhận hàng."
- Câu B: "Khách hàng được nhận lại 100% chi phí khi kiện hàng giao đến bị hư hỏng hoặc không hoạt động."
- Tại sao tương đồng: Hai câu sử dụng các từ vựng hoàn toàn khác biệt (người mua vs khách hàng, hoàn trả đầy đủ tiền vs nhận lại 100% chi phí, lỗi/bể vỡ vs hư hỏng/không hoạt động) nhưng diễn đạt cùng một bản chất quyền lợi đổi trả trong chính sách TMĐT, do đó mô hình embedding sẽ ánh xạ chúng vào hai vector có hướng gần như trùng khít nhau.

**Ví dụ có độ tương tự THẤP:**
- Câu A: "Người mua có quyền yêu cầu hoàn trả đầy đủ tiền nếu sản phẩm bị lỗi hoặc bể vỡ khi nhận hàng."
- Câu B: "Người bán cần nộp đầy đủ tờ khai thuế giá trị gia tăng hàng quý theo quy định của cơ quan nhà nước."
- Tại sao khác: Hai câu thuộc hai đối tượng (người mua vs người bán) và hai phạm trù nghiệp vụ hoàn toàn khác nhau (chính sách đổi trả sản phẩm vs nghĩa vụ kê khai thuế), dẫn đến góc giữa hai vector lớn và độ tương tự cosine thấp (gần 0 hoặc âm).

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Độ tương tự cosine đo góc (hướng ngữ nghĩa) độc lập với độ dài (độ lớn vector), trong khi khoảng cách Euclid bị chi phối bởi độ dài văn bản. Một câu ngắn và một đoạn văn dài diễn đạt cùng một ý sẽ có vector norm chênh lệch lớn khiến khoảng cách Euclid xa nhau, nhưng góc cosine giữa chúng vẫn nhỏ, giúp truy xuất ngữ nghĩa chính xác hơn.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> *Trình bày phép tính:* `ceil((10000 - 50) / (500 - 50)) = ceil(9950 / 450) = ceil(22.111...) = 23`
> *Đáp án:* 23 chunks (đã kiểm chứng bằng mã nguồn `FixedSizeChunker(500, 50).chunk('a'*10000)`).

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Số lượng chunk tăng lên 25 (`ceil((10000 - 100) / (500 - 100)) = ceil(9900 / 400) = 25`). Ta muốn tăng overlap để bảo toàn ngữ cảnh tại các ranh giới cắt (boundary context preservation), tránh việc một câu, con số hoặc mệnh đề điều khoản quan trọng bị cắt đôi khiến mô hình mất thông tin khi truy xuất.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Sử dụng biểu thức chính quy Lookbehind `(?<=[.!?])\s+` để tách câu tại khoảng trắng hoặc ký tự xuống dòng ngay sau dấu câu mà không làm nuốt mất các dấu chấm, chấm than, chấm hỏi. Gom các câu lại thành từng chunk theo tham số `max_sentences_per_chunk` và loại bỏ khoảng trắng thừa. Edge case nhận biết chưa xử lý triệt để: các chữ viết tắt (TS., v.v., e.g.) và số thập phân (3.14) có thể bị nhận nhầm thành dấu kết thúc câu.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Thuật toán hoạt động theo hai chiều: (1) Đệ quy xuống sâu các phân mảnh vượt quá `chunk_size` theo thứ tự ưu tiên separator `["\n\n", "\n", ". ", " ", ""]`, và (2) Gom lên (merge up) các mảnh liền kề nhỏ cho đến sát ngưỡng `chunk_size` để tránh sinh ra các chunk vụn. Ba trường hợp dừng (base case): text rỗng trả `[]`, text nhỏ hơn `chunk_size` trả `[text]`, và khi hết separator khả dụng thì fallback cắt chuỗi theo lát cắt `chunk_size`.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> Lưu trữ các tài liệu dạng in-memory danh sách các dictionary gồm `id`, `content`, `metadata` và vector `embedding` sinh từ hàm `_embedding_fn`. Khi thực hiện `search`, truy vấn được nhúng thành vector rồi tính tích vô hướng / cosine similarity (`compute_similarity`) với toàn bộ vector lưu trữ, sau đó sắp xếp theo điểm tương đồng giảm dần và trích xuất top-k kết quả.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> Áp dụng chiến lược tiền lọc (pre-filtering): lọc danh sách lưu trữ trước bằng điều kiện so khớp chính xác mọi cặp key-value trong `metadata_filter`, sau đó mới tính toán độ tương đồng vector trên tập con đã lọc để tối ưu tốc độ và loại bỏ nhiễu chéo audience. Xóa tài liệu (`delete_document`) bằng cách lọc bỏ tất cả các chunk có `id == doc_id` hoặc trường `metadata['doc_id'] == doc_id`, trả về True nếu kích thước kho lưu trữ giảm đi.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Triển khai kiến trúc RAG cổ điển: bước 1 truy xuất `top_k` chunk tài liệu liên quan nhất từ kho tri thức qua `store.search()`, bước 2 ghép các chunk thành chuỗi ngữ cảnh `Context` và đưa vào cấu trúc prompt chuẩn (`Context: ... \n\nQuestion: ... \nAnswer:`), bước 3 gọi hàm ngôn ngữ `llm_fn(prompt)` để sinh câu trả lời bám sát ngữ cảnh thực tế.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
============================= test session starts =============================
platform win32 -- Python 3.14.0, pytest-9.1.1, pluggy-1.6.0 -- D:\GitHub\LAB\K4-L3B-Data-Foundations\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\GitHub\LAB\K4-L3B-Data-Foundations
plugins: anyio-4.15.1
collecting ... collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED [  2%]
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED [  4%]
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED [  7%]
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED [  9%]
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED [ 11%]
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED [ 14%]
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED [ 16%]
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED [ 19%]
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED [ 21%]
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED   [ 23%]
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED [ 26%]
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED [ 28%]
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED [ 30%]
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED    [ 33%]
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED [ 35%]
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED [ 38%]
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED [ 40%]
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED [ 42%]
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED   [ 45%]
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED [ 47%]
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED [ 50%]
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED [ 52%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED [ 54%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED [ 57%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED [ 59%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED [ 61%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED [ 64%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED [ 66%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED [ 69%]
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED [ 71%]
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED [ 73%]
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED [ 76%]
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED [ 78%]
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED [ 80%]
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED [ 83%]
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED [ 85%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED [ 88%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED [ 90%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED [ 92%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED [ 95%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED [ 97%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED [100%]

============================= 42 passed in 0.07s ==============================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | The buyer may return the item if it arrived damaged or faulty. | Customers can request a return when products are broken or defective upon arrival. | cao | 0.0588 | Sai (do mock) |
| 2 | The seller must respond to return requests within 3 business days. | Merchants have three working days to reply to return inquiries. | cao | 0.0587 | Sai (do mock) |
| 3 | Refunds are typically processed to the original payment method within 3 to 5 business days. | Sellers must maintain a transaction defect rate below 2% to avoid performance penalties. | thấp | 0.0579 | Đúng |
| 4 | Top Rated Sellers in the US or Canada are eligible for additional seller protections. | Top Rated Sellers are required to pay higher listing insertion fees for each product category. | thấp | 0.0752 | Sai |
| 5 | Return postage costs are covered by the seller when the item does not match the listing. | The seller pays for return shipping if the item is not as described. | cao | -0.0803 | Sai (do mock) |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Kết quả bất ngờ nhất là ở cặp 4: hai câu có ngữ nghĩa nghiệp vụ đối lập hoàn toàn (quyền lợi bảo vệ vs nghĩa vụ nộp phí) lại có điểm tương đồng cao nhất (0.0752), vượt cả hai cặp đồng nghĩa (cặp 1 và 2). Điều này phản ánh rõ ràng bản chất của hàm embedding giả lập (`MockEmbedder` dựa trên băm ký tự n-gram bề mặt) khi nó chỉ bắt chước sự trùng lặp từ khóa "Top Rated Sellers" chứ không nắm bắt được ngữ nghĩa ngữ cảnh (semantics), chứng minh rằng để ứng dụng thực tế cần các mô hình Embedding Transformer chuyên sâu (như MiniLM hoặc OpenAI Embeddings).

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | What happens if an item does not match the listing or arrives faulty or damaged? | `ebay-buyer-return-refund#18`: Quy định người mua được trả hàng và hoàn tiền khi sản phẩm không đúng mô tả hoặc hư hỏng. | 0.7032 | Có (Relevant) | Người mua có thể mở yêu cầu trả hàng và nhận lại tiền kể cả khi người bán để chính sách không chấp nhận đổi trả. |
| 2 | How long does the seller have to respond to a buyer's return request? | `ebay-buyer-return-refund#11`: Quy định người bán có trách nhiệm phản hồi yêu cầu đổi trả của khách hàng trong vòng 3 ngày làm việc. | 0.7881 | Có (Relevant) | Người bán có thời hạn tối đa 3 ngày làm việc để đưa ra phản hồi hoặc phương án xử lý trước khi eBay can thiệp. |
| 3 | How long do refunds typically take to become available? | `ebay-buyer-return-refund#4`: Hướng dẫn thời gian xử lý và nhận tiền hoàn trả. Chunk rank 3 (`#24`, score 0.6554) chứa đúng marker `typically available`. | 0.7064 | Có (Relevant - Marker YES) | Tiền hoàn trả thông thường sẽ sẵn sàng trong tài khoản của người mua trong vòng 3 đến 5 ngày làm việc. |
| 4 | What is the maximum transaction defect rate in the seller standards policy? | `ebay-seller-standards#12`: Bảng tiêu chuẩn đánh giá hiệu suất của người bán, nêu rõ ngưỡng tỷ lệ lỗi giao dịch cho phép. | 0.6849 | Có (Relevant) | Tỷ lệ lỗi giao dịch tối đa cho phép đối với người bán để duy trì chuẩn hiệu suất là 2% tổng số giao dịch. |
| 5 | List the eligibility conditions for protections for Top Rated Sellers. | `ebay-seller-protections#3`: Chứa đầy đủ danh sách 5 điều kiện tiên quyết để được bảo vệ dành riêng cho Top Rated Seller. | 0.7488 | Có (Relevant - Marker YES Rank 1) | Điều kiện gồm: đạt chuẩn Top Rated, cư trú tại US/Canada, không bị đánh giá dịch vụ Very High, niêm yết trên eBay.com và có chính sách đổi trả tối thiểu 30 ngày. |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 5 / 5

> *Ghi chú về Backend Embedding:* Benchmark cá nhân đã được chạy thành công trên mô hình nhúng thật **`sentence-transformers/all-MiniLM-L6-v2`** (sau khi thử nghiệm với `MockEmbedder`). Điểm cosine similarity tăng vọt lên mức **0.65 – 0.79** phản ánh sự thấu hiểu ngữ nghĩa thực thụ; các chuỗi đặc trưng (`marker`) đã chuyển thành **`YES`** (đặc biệt Q5 đạt `marker=YES` ngay tại Rank 1). Điều này kết hợp hoàn hảo với chiến lược `HeadingChunker` (243 chunks) và cơ chế tiền lọc `metadata_filter` mang lại độ chính xác 100%.

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Chiến lược `HeadingChunker` vượt trội hơn `FixedSizeChunker` ở khả năng giữ nguyên cấu trúc phân cấp điều khoản chính sách của sàn TMĐT và bảo toàn tiêu đề mục ở đầu mỗi sub-chunk, giúp câu trả lời của Agent luôn chuẩn xác theo phạm vi điều luật. Đặc biệt, việc áp dụng cơ chế tiền lọc `metadata_filter={"audience": "buyer"}` là yếu tố quyết định loại bỏ hoàn toàn việc truy xuất nhầm tài liệu của người bán (`seller`), đem lại độ chính xác 100% cho hệ thống RAG.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 10 / 10 |
| **Tổng phần cá nhân** | **60 / 60** |
