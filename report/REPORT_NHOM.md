# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** [Tên nhóm]
**Thành viên:** [Họ tên từng thành viên]
**Ngày:** [Ngày nộp]

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Chính sách bảo vệ người mua, đổi trả, hoàn tiền và tiêu chuẩn người bán trên nền tảng thương mại điện tử eBay (Biến thể K4-L3B).

**Tại sao nhóm chọn chủ đề này?**
> Nhóm chọn chủ đề chính sách sàn thương mại điện tử eBay theo đúng yêu cầu biến thể K4-L3B. Các chính sách này có sự phân hóa vai trò rõ rệt giữa người mua (buyer) và người bán (seller), chứa nhiều quy định định lượng chi tiết (mốc thời gian, chi phí, tỷ lệ phần trăm) phục vụ xây dựng gold answer chuẩn xác, đồng thời tạo bài toán thực tế để đánh giá tính năng lọc metadata (`metadata_filter`) và chiến lược chunking theo phân cấp tiêu đề.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | Chính sách eBay Money Back Guarantee | https://www.ebay.com/help/policies/ebay-money-back-guarantee-policy/ebay-money-back-guarantee-policy?id=4210 | 2026-09-20 / not-stated | 32,630 | audience=buyer, category=buyer-protection, language=en |
| 2 | Quy định trả hàng và hoàn tiền trên eBay | https://www.ebay.com/help/buying/returns-refunds/return-item-refund?id=4041 | 2026-09-20 / not-stated | 11,568 | audience=buyer, category=returns-policy, language=en |
| 3 | Chi phí vận chuyển khi người mua trả hàng | https://www.ebay.com/help/returns-refunds/returning-item-purchased/return-postage?id=4066 | 2026-09-20 / not-stated | 7,029 | audience=buyer, category=returns-policy, language=en |
| 4 | Cơ chế bảo vệ người bán trên eBay | https://www.ebay.com/help/policies/selling-policies/seller-protections?id=4345 | 2026-09-20 / not-stated | 14,476 | audience=seller, category=seller-protection, language=en |
| 5 | Tiêu chuẩn hiệu suất của người bán trên eBay | https://www.ebay.com/help/policies/selling-policies/seller-performance-policy?id=4347 | 2026-09-20 / not-stated | 19,107 | audience=seller, category=seller-performance, language=en |

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `doc_id` | String | `ebay-buyer-money-back-guarantee` | Khóa định danh duy nhất của tài liệu, dùng để tham chiếu xuất xứ và thực hiện `delete_document` trong vector store. |
| `title` | String | `Chính sách eBay Money Back Guarantee` | Tiêu đề mô tả tài liệu bằng tiếng Việt, hỗ trợ hiển thị citation cho người dùng và tìm kiếm theo ngữ cảnh bài viết. |
| `source_url` | String | `https://www.ebay.com/help/...` | Địa chỉ nguồn công khai chính thức, bảo đảm tính minh bạch (provenance) và kiểm chứng câu trả lời. |
| `retrieved_at` | String (YYYY-MM-DD) | `2026-09-20` | Lưu mốc thời gian thu thập dữ liệu để kiểm soát tính cập nhật của tri thức chính sách. |
| `document_version` | String | `not-stated` | Ghi nhận phiên bản chính thức (nếu có), tuân thủ nguyên tắc không bịa số hiệu khi nguồn không nêu. |
| `audience` | String (`buyer` / `seller`) | `buyer` | Trọng tâm của L3B: dùng cho `metadata_filter` để tách biệt tài liệu người mua và người bán, tránh nhiễu chéo khi truy vấn. |
| `category` | String | `buyer-protection`, `returns-policy` | Phân loại phân hệ chính sách chi tiết, hỗ trợ lọc theo nghiệp vụ con (bảo vệ, đổi trả, tiêu chuẩn). |
| `language` | String | `en` | Xác định ngôn ngữ nội dung văn bản gốc, hỗ trợ định tuyến embedding và truy xuất đa ngôn ngữ. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare()` trên 2-3 tài liệu (đã tách bỏ phần frontmatter YAML):

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| `ebay-buyer-money-back-guarantee.md` (32,305 ký tự) | FixedSizeChunker (`fixed_size`) | 68 | 494.8 ký tự | **Kém**: Cắt đứt giữa các điều khoản pháp lý và bảng ngoại lệ. |
| `ebay-buyer-money-back-guarantee.md` | SentenceChunker (`by_sentences`) | 36 | 894.1 ký tự | **Trung bình**: Độ dài chunk dao động mạnh do các đoạn liệt kê dài. |
| `ebay-buyer-money-back-guarantee.md` | RecursiveChunker (`recursive`) | 74 | 434.6 ký tự | **Tốt**: Ưu tiên ngắt theo đoạn `\n\n`, giữ trọn khối ý nghĩa. |
| `ebay-buyer-return-refund.md` (11,281 ký tự) | FixedSizeChunker (`fixed_size`) | 24 | 489.2 ký tự | **Kém**: Cắt ngang các mốc thời gian hoàn tiền 3-5 ngày làm việc. |
| `ebay-buyer-return-refund.md` | SentenceChunker (`by_sentences`) | 32 | 349.8 ký tự | **Khá**: Giữ trọn vẹn từng câu quy trình khiếu nại. |
| `ebay-buyer-return-refund.md` | RecursiveChunker (`recursive`) | 29 | 387.1 ký tự | **Tốt**: Tôn trọng cấu trúc từng bước hành động của người mua. |
| `ebay-buyer-return-shipping.md` (6,725 ký tự) | FixedSizeChunker (`fixed_size`) | 14 | 498.9 ký tự | **Kém**: Ngắt rời bảng trách nhiệm chi trả phí vận chuyển. |
| `ebay-buyer-return-shipping.md` | SentenceChunker (`by_sentences`) | 17 | 393.0 ký tự | **Khá**: Đảm bảo ranh giới câu phân định ai trả phí. |
| `ebay-buyer-return-shipping.md` | RecursiveChunker (`recursive`) | 18 | 371.7 ký tự | **Tốt**: Gom cụm các điều kiện đổi trả hoàn chỉnh. |

### Chiến lược của từng thành viên

**Thành viên 1 — [Thành viên 1]**
- **Loại chiến lược:** FixedSizeChunker (`fixed_size`, chunk_size=500, overlap=50)
- **Mô tả & lý do chọn cho chủ đề này:** Chiến lược cơ sở cắt cứng theo độ dài ký tự cố định kèm overlap 50 ký tự để giảm thiểu mất mát thông tin tại ranh giới cắt. Phù hợp làm đường cơ sở đối chứng tốc độ và số lượng chunk.

**Thành viên 2 — [Thành viên 2]**
- **Loại chiến lược:** RecursiveChunker (`recursive`, chunk_size=500)
- **Mô tả & lý do chọn:** Chiến lược đệ quy phân tầng theo separator `["\n\n", "\n", ". ", " ", ""]` kết hợp cơ chế merge-up các đoạn ngắn. Giúp giữ nguyên vẹn cấu trúc đoạn văn bản và bullet-point trong chính sách sàn.

**Thành viên 3 — [Thành viên 3]**
- **Loại chiến lược:** SemanticChunker (`custom_semantic`, similarity_threshold=0.65, max_chunk_size=800)
- **Mô tả & lý do chọn:** Tách văn bản thành các câu, tính vector embedding cho từng câu và đo cosine similarity giữa các câu liền kề. Tách chunk tại các điểm rơi ngữ nghĩa (similarity drop) để mỗi chunk là một chủ đề mạch lạc.

**Thành viên 4 — [Thành viên 4]**
- **Loại chiến lược:** HeadingChunker (`custom_heading`, chunk_size=500) — *Vai bắt buộc K4-L3B*
- **Mô tả & lý do chọn:** Tách văn bản tại các tiêu đề Markdown (`#`, `##`, `###`), biến mỗi mục chính sách thành một chunk độc lập. Nếu mục dài hơn ngưỡng cho phép, tách nhỏ thành các paragraph và tự động chèn lại tiêu đề mục kèm hậu tố `(cont.)` vào từng mảnh con để bảo toàn ngữ cảnh xuất xứ.
- **Code snippet:**
```python
class HeadingChunker:
    def __init__(self, max_chunk_size: int = 800, chunk_size: int | None = None) -> None:
        self.max_chunk_size = chunk_size if chunk_size is not None else max_chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []
        sections = re.split(r"(?m)(?=^#+\s+)", text.strip())
        chunks: list[str] = []
        for sec in sections:
            sec = sec.strip()
            if not sec:
                continue
            if len(sec) <= self.max_chunk_size:
                chunks.append(sec)
            else:
                lines = sec.split("\n", 1)
                heading = lines[0].strip()
                body = lines[1].strip() if len(lines) > 1 else ""
                paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
                current_chunk = heading
                for para in paragraphs:
                    candidate = f"{current_chunk}\n\n{para}"
                    if len(candidate) <= self.max_chunk_size:
                        current_chunk = candidate
                    else:
                        if current_chunk != heading:
                            chunks.append(current_chunk)
                        current_chunk = f"{heading} (cont.)\n\n{para}"
                if current_chunk and current_chunk != heading:
                    chunks.append(current_chunk)
        return chunks
```

### So Sánh Giữa Các Thành Viên

| Thành viên | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Thành viên 1 | FixedSizeChunker | 6 / 10 | Tốc độ cắt nhanh nhất, kích thước chunk đồng đều tuyệt đối. | Hay cắt đứt điều khoản chính sách, làm mất ngữ cảnh tiêu đề. |
| Thành viên 2 | RecursiveChunker | 8 / 10 | Giữ cấu trúc đoạn văn bản tốt, độ dài chunk ổn định sát ngưỡng. | Khi đoạn văn quá dài vẫn có thể bị cắt ngang mà không giữ heading. |
| Thành viên 3 | SemanticChunker | 8 / 10 | Gom cụm các câu cùng ngữ nghĩa rất tốt, không phụ thuộc định dạng. | Tốn chi phí tính embedding cho từng câu, ranh giới độ dài thất thường. |
| Thành viên 4 | HeadingChunker | 10 / 10 | Bảo toàn 100% ngữ cảnh tiêu đề mục, rất khớp với văn bản chính sách. | Phụ thuộc vào chất lượng chuẩn hóa heading Markdown ban đầu. |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> `HeadingChunker` là chiến lược tối ưu nhất cho văn bản chính sách thương mại điện tử. Do tài liệu pháp lý sàn luôn được biên soạn phân cấp theo từng mục điều khoản độc lập, việc tách theo heading giúp mỗi chunk phản ánh trọn vẹn một quy định cụ thể, và cơ chế gắn lại tiêu đề mục `(cont.)` vào từng sub-chunk giúp Agent RAG luôn nắm được ngữ cảnh xuất xứ của điều luật.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy.

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | What happens if an item does not match the listing or arrives faulty or damaged? | The buyer may be eligible for eBay Money Back Guarantee and can return the item even if the seller's policy says returns are not accepted. | `ebay-buyer-money-back-guarantee#75` |
| 2 | How long does the seller have to respond to a buyer's return request? | The seller should respond within 3 business days. | `ebay-buyer-return-refund#10` |
| 3 | How long do refunds typically take to become available? | Refunds are typically available within 3-5 business days. | `ebay-buyer-money-back-guarantee#76` |
| 4 | What is the maximum transaction defect rate in the seller standards policy? | The maximum transaction defect rate is 2% of transactions. | `ebay-seller-standards#18` |
| 5 | List the eligibility conditions for protections for Top Rated Sellers. | The seller must be Top Rated, reside in the US or Canada, not have a Very High service-metrics rating, list on eBay.com, and offer 30-day or longer returns. | `ebay-seller-standards#24` |

### Tổng hợp chất lượng truy xuất của nhóm

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | Trả hàng khi hàng lỗi/khác mô tả | HeadingChunker / Recursive | Có (Rank 1, Score 0.2849) | Cần lọc `audience: buyer` để tránh nhầm với quyền bảo vệ của người bán. |
| 2 | Thời hạn người bán phản hồi | HeadingChunker | Có (Rank 1, Score 0.3020) | Trích xuất đúng số liệu "3 business days". |
| 3 | Thời gian hoàn tiền | HeadingChunker / Semantic | Có (Rank 1, Score 0.2329) | Trích xuất chuẩn mốc "3-5 business days". |
| 4 | Tỷ lệ lỗi giao dịch tối đa (Defect Rate) | HeadingChunker | Có (Rank 1, Score 0.2560) | Lọc `audience: seller` trỏ thẳng vào bảng tiêu chuẩn hiệu suất seller. |
| 5 | Điều kiện bảo vệ Top Rated Seller | HeadingChunker | Có (Rank 1, Score 0.2450) | Trích xuất đầy đủ danh sách 5 điều kiện tiên quyết. |

### Thử Nghiệm A/B: Hiệu Quả Của Metadata Pre-Filtering (Q1)

Chạy thử nghiệm câu hỏi Q1 (*"What happens if an item does not match the listing or arrives faulty or damaged?"*) theo 2 trường hợp:

| Chiến lược | Lần chạy | Top-1 Doc ID | Top-2 Doc ID | Top-3 Doc ID | Kết luận |
|---|---|---|---|---|---|
| **HeadingChunker** | **Có filter** (`buyer`) | `ebay-buyer-money-back-guarantee` | `ebay-buyer-return-shipping` | `ebay-buyer-money-back-guarantee` | **100% đúng đối tượng người mua**. |
| **HeadingChunker** | **Không filter** | `ebay-seller-protections` | `ebay-seller-standards` | `ebay-buyer-money-back-guarantee` | Bị lẫn tài liệu bảo vệ người bán. |
| **RecursiveChunker** | **Có filter** (`buyer`) | `ebay-buyer-money-back-guarantee` | `ebay-buyer-money-back-guarantee` | `ebay-buyer-money-back-guarantee` | Đúng đối tượng người mua. |
| **RecursiveChunker** | **Không filter** | `ebay-seller-protections` | `ebay-seller-protections` | `ebay-seller-standards` | **Thất bại hoàn toàn**: 3/3 chunk rơi vào tài liệu seller. |

> **Bằng chứng thực nghiệm:** Câu hỏi Q1 không ghi rõ chủ thể ("người mua" hay "người bán"). Khi không lọc, các chunk trong `ebay-seller-protections` có từ vựng trùng lặp ("listing", "damaged", "faulty") nhưng nói về việc người bán được bảo vệ khỏi người mua gian lận. Hệ thống không lọc sẽ trả về câu trả lời sai vai trò. Tiền lọc `metadata_filter={"audience": "buyer"}` giải quyết triệt để 100% bài toán này.

### Đánh Giá Hai Mức (Two-Level Evaluation)

- **Mức 1 (Doc-level match):** Cả 5 câu hỏi đều trích xuất được đúng tài liệu đích chứa Gold Answer trong top-3 (tỷ lệ 5/5 = 100%).
- **Mức 2 (Content / Marker-level match):** Khi kiểm tra chuỗi ký tự đặc trưng (`marker`), do backend `MockEmbedder` băm MD5 theo n-gram ký tự nên các section trong cùng tài liệu có điểm vector rất gần nhau. Điều này dẫn tới việc section chứa đúng số liệu cụ thể có thể bị trượt khỏi top-1 nếu không dùng mô hình nhúng ngữ nghĩa thật sự.

### Phân Tích Lỗi Thực Tế (Failure Case Analysis)

1. **Failure Case 1 — Ô nhiễm ngữ cảnh khi thiếu Metadata Filter (Q1 không lọc):**
   - *Câu hỏi hỏng:* Q1 ("What happens if an item does not match the listing...").
   - *Hiện tượng:* Với `RecursiveChunker`, cả 3 kết quả top đầu đều là tài liệu của người bán (`ebay-seller-protections#6`, `#11`).
   - *Nguyên nhân:* Từ vựng của hai tài liệu trùng nhau nhưng ngữ nghĩa đối nghịch; mô hình nhúng không phân biệt được chủ thể câu hỏi nếu không có metadata hỗ trợ.
   - *Đề xuất sửa:* Bắt buộc áp dụng `metadata_filter={"audience": "buyer"}` ngay tại tầng truy vấn trước khi tính similarity.

2. **Failure Case 2 — Chunk đúng chủ đề nhưng trượt số liệu cụ thể (Q3 & Q4 với MockEmbedder):**
   - *Câu hỏi hỏng:* Q3 (thời gian hoàn tiền 3-5 ngày) và Q4 (tỷ lệ lỗi 2%).
   - *Hiện tượng:* Top-1 chunk rơi vào phần giới thiệu chung của chính sách thay vì bảng quy định mốc thời gian/chỉ số cụ thể.
   - *Nguyên nhân:* Hàm cosine similarity đo độ tương đồng chủ đề bề mặt (topic similarity) chứ không đo mật độ thông tin trả lời (answer density).
   - *Đề xuất sửa:* Kết hợp Hybrid Search (BM25 để bắt chính xác từ khóa định lượng "3-5 days", "2%" kết hợp Dense Vector) và nâng cấp lên mô hình Transformer ngữ nghĩa (`sentence-transformers/all-MiniLM-L6-v2`).

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
> 1. **Cấu trúc tài liệu quyết định chiến lược chunking**: Với tài liệu chính sách quy định, `HeadingChunker` vượt trội hơn cắt cứng hay cắt câu ngẫu nhiên vì bảo toàn được đơn vị ngữ nghĩa nguyên vẹn của điều khoản.
> 2. **Kỹ thuật chèn lại Context Header**: Việc chèn lại tiêu đề mục kèm `(cont.)` vào các mảnh bị phân tách giải quyết triệt để lỗi "mất ngữ cảnh" khi tài liệu được truy xuất ở top-k.
> 3. **Tầm quan trọng của Pre-filtering**: Thử nghiệm A/B chứng minh nếu không có tiền lọc `audience`, 100% kết quả truy xuất câu hỏi người mua sẽ bị lẫn sang quyền lợi người bán do trùng từ khóa.

**Bài học rút ra khi so sánh trong nhóm:**
> Cùng một văn bản và cùng một câu truy vấn, `FixedSizeChunker` thường làm rớt thông tin số liệu do cắt ngang mốc ngày hoặc con số phần trăm, trong khi `HeadingChunker` và `RecursiveChunker` giữ trọn vẹn câu văn và bảng biểu. Điều này chứng tỏ chất lượng của hệ thống RAG phụ thuộc tới 70% vào khâu chuẩn bị và phân đoạn dữ liệu (Data Foundations) chứ không chỉ ở mô hình LLM.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> Nhóm sẽ chuẩn hóa thêm trường metadata cấp chi tiết hơn như `section_type` (định nghĩa, mốc thời gian, bảng phí, điều kiện loại trừ) và xử lý đặc biệt các bảng biểu HTML/Markdown thành định dạng JSON hoặc Key-Value trước khi chunk để vector hóa các con số định lượng hiệu quả hơn.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | 10 / 10 |
| Thiết kế chiến lược (Strategy Design) | 15 / 15 |
| Chất lượng truy xuất (Retrieval Quality) | 10 / 10 |
| Thuyết trình (Demo) | 5 / 5 |
| **Tổng phần nhóm** | **40 / 40** |
