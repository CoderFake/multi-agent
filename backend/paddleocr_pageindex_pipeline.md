# PaddleOCR + PageIndex Pipeline

## Tổng quan

```
[Image / Scanned PDF]
       ↓
  MinIO upload            ← lưu file gốc, nhận object_key
       ↓
  PP-StructureV3          ← layout detection + OCR, giữ bbox + page_index
       ↓
  Markdown Assembly       ← embed bbox metadata vào HTML comment
       ↓
  PageIndex (md_path)     ← build hierarchical tree index
       ↓
  PostgreSQL              ← tree JSON + node metadata (bbox, page, minio_key)
       ↓
  Reasoning-based RAG     ← LLM chọn node → content + presigned URL trả về
```

---

## Bước 0 — Upload file gốc lên MinIO

Lưu file gốc trước khi OCR để mỗi node sau này có thể reference ngược về đúng vị trí.

```python
import uuid
from minio import Minio

minio_client = Minio(
    "localhost:29000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False
)

def upload_original(file_path: str, bucket: str = "documents") -> str:
    """Upload original file to MinIO, return object_key."""
    ext = file_path.rsplit(".", 1)[-1]
    object_key = f"{uuid.uuid4()}.{ext}"

    minio_client.fput_object(bucket, object_key, file_path)
    return object_key
```

---



**Model sử dụng:** `PP-StructureV3` (PaddleOCR 3.0)

Đây là model tốt nhất hiện tại vì xử lý được:
- Văn bản thường, bảng biểu, công thức, chữ viết tay
- Layout đa cột, tài liệu nghiên cứu, báo cáo phức tạp
- Reading order tự động với X-Y Cut cải tiến

```python
from paddleocr import PPStructureV3

pipeline = PPStructureV3()
result = pipeline.predict("document.pdf")

# result trả về list theo từng page, mỗi page có:
# - layout_type: "text" | "table" | "figure" | "title" | "formula"
# - bbox: [x1, y1, x2, y2]
# - text / html (với table)
# - page_index
```

---

## Bước 2 — Assembly thành Markdown chuẩn cấu trúc

Mục tiêu: tạo Markdown có **heading hierarchy** cho PageIndex, đồng thời **nhúng bbox metadata vào HTML comment** để sau này map ngược về file gốc trên MinIO.

| Layout type từ PP-StructureV3 | Mapping sang Markdown |
|---|---|
| `title` (font lớn / bold) | `# H1` hoặc `## H2` theo font size |
| `text` | Paragraph thường |
| `table` | Markdown table hoặc giữ nguyên HTML |
| `figure_caption` | `> caption text` |
| `formula` | `` `formula` `` inline hoặc block |

```python
import json

def assemble_markdown(result: list, minio_key: str) -> tuple[str, list]:
    """
    Assemble PP-StructureV3 output into structured Markdown.
    Returns markdown string and bbox_index (list of block metadata per page).
    """
    lines = []
    bbox_index = []

    for page_idx, page in enumerate(result):
        for block in sorted(page, key=lambda x: (x["bbox"][1], x["bbox"][0])):
            layout_type = block.get("layout_type", "text")
            text = block.get("text", "").strip()
            bbox = block.get("bbox")

            block_meta = {
                "page": page_idx,
                "bbox": bbox,
                "layout_type": layout_type,
                "minio_key": minio_key,
            }
            bbox_index.append(block_meta)

            # nhúng metadata vào comment để trace lại sau
            meta_comment = f'<!-- meta:{json.dumps(block_meta, ensure_ascii=False)} -->'

            if layout_type == "title":
                font_size = block.get("font_size", 12)
                level = "#" if font_size >= 18 else "##"
                lines.append(f"\n{meta_comment}\n{level} {text}\n")

            elif layout_type == "table":
                lines.append(f"\n{meta_comment}\n{block.get('html', text)}\n")

            elif layout_type == "text" and text:
                lines.append(f"\n{meta_comment}\n{text}\n")

    return "\n".join(lines), bbox_index
```

> **Tại sao nhúng vào HTML comment?** PageIndex đọc Markdown thuần, comment không ảnh hưởng heading hierarchy nhưng vẫn được lưu trong node content → khi fetch node ra, parse lại comment là có đủ page + bbox để tạo presigned URL chính xác.

---

## Bước 3 — Build PageIndex Tree & Lưu vào PostgreSQL

> **Không cần Milvus hay bất kỳ vector DB nào.** PageIndex lưu tree dưới dạng JSON thuần.

```python
import json
import psycopg2
from pageindex import run_pipeline

md_path = "./output/document.md"
tree = run_pipeline(md_path=md_path, model="gpt-4o-2024-11-20")

# tree output dạng:
# {
#   "node_id": "0001",
#   "title": "Chương 1",
#   "summary": "...",
#   "start_index": 0,
#   "end_index": 5,
#   "nodes": [ { "node_id": "0002", ... } ]  ← sub-nodes đệ quy
# }
```

**Schema PostgreSQL — 3 bảng:**

```sql
CREATE TABLE documents (
    doc_id      TEXT PRIMARY KEY,
    file_name   TEXT,
    minio_key   TEXT,            -- object key trên MinIO (file gốc)
    bucket      TEXT DEFAULT 'documents',
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE document_trees (
    doc_id      TEXT PRIMARY KEY REFERENCES documents(doc_id),
    tree_json   JSONB
);

-- Mỗi node ánh xạ về đúng vùng trên file gốc qua page + bbox
CREATE TABLE document_nodes (
    node_id     TEXT,
    doc_id      TEXT REFERENCES documents(doc_id),
    title       TEXT,
    summary     TEXT,
    content     TEXT,
    start_index INT,
    end_index   INT,
    -- reference về MinIO
    pages       INT[],           -- danh sách page index node này cover
    bboxes      JSONB,           -- list bbox của các block trong node
    PRIMARY KEY (node_id, doc_id)
);
```

```python
import re

def extract_bbox_from_content(content: str) -> tuple[list, list]:
    """Extract page numbers and bboxes from HTML comments in node content."""
    pattern = r'<!-- meta:(.*?) -->'
    matches = re.findall(pattern, content)

    pages, bboxes = set(), []
    for m in matches:
        meta = json.loads(m)
        pages.add(meta["page"])
        if meta.get("bbox"):
            bboxes.append({"page": meta["page"], "bbox": meta["bbox"]})

    return sorted(pages), bboxes


def save_to_postgres(conn, doc_id: str, file_name: str, minio_key: str, tree: dict, md_path: str):
    """Save document, tree and nodes to PostgreSQL with MinIO reference."""
    pages = open(md_path).read().split("\f")

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO documents (doc_id, file_name, minio_key) VALUES (%s, %s, %s)",
            (doc_id, file_name, minio_key)
        )
        cur.execute(
            "INSERT INTO document_trees (doc_id, tree_json) VALUES (%s, %s)",
            (doc_id, json.dumps(tree))
        )
        for node in flatten_nodes(tree):
            content = "\n".join(pages[node["start_index"]:node["end_index"] + 1])
            page_list, bbox_list = extract_bbox_from_content(content)
            cur.execute(
                "INSERT INTO document_nodes VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (node["node_id"], doc_id, node["title"],
                 node.get("summary", ""), content,
                 node["start_index"], node["end_index"],
                 page_list, json.dumps(bbox_list))
            )
    conn.commit()
```

---

## Bước 4 — Reasoning Retrieval + Presigned URL từ MinIO

LLM chọn node → fetch content + bbox từ DB → generate presigned URL trỏ đúng page/vùng file gốc.

```python
import json
from datetime import timedelta
from openai import OpenAI
from minio import Minio

client = OpenAI()
minio_client = Minio("localhost:9000", access_key="minioadmin", secret_key="minioadmin", secure=False)

def get_presigned_url(bucket: str, minio_key: str, expires_hours: int = 1) -> str:
    """Generate presigned URL for original file on MinIO."""
    return minio_client.presigned_get_object(
        bucket, minio_key, expires=timedelta(hours=expires_hours)
    )

def retrieve_and_answer(conn, doc_id: str, query: str) -> dict:
    """
    Reasoning-based retrieval using PageIndex tree.
    Returns answer text and citation references with presigned URLs.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT d.minio_key, d.bucket, t.tree_json FROM documents d "
            "JOIN document_trees t ON d.doc_id = t.doc_id WHERE d.doc_id = %s",
            (doc_id,)
        )
        minio_key, bucket, tree_json = cur.fetchone()

    resp = client.chat.completions.create(
        model="gpt-4o-2024-11-20",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a document navigator. Given a tree index and a query, "
                    "return node_ids most likely to contain the answer. "
                    'Reply ONLY as JSON: {"thinking": "...", "node_list": ["id1", "id2"]}'
                )
            },
            {
                "role": "user",
                "content": f"Query: {query}\n\nDocument tree:\n{json.dumps(tree_json, ensure_ascii=False)}"
            }
        ]
    )

    node_ids = json.loads(resp.choices[0].message.content)["node_list"]

    with conn.cursor() as cur:
        cur.execute(
            "SELECT node_id, title, content, pages, bboxes "
            "FROM document_nodes WHERE doc_id = %s AND node_id = ANY(%s)",
            (doc_id, node_ids)
        )
        rows = cur.fetchall()

    presigned_url = get_presigned_url(bucket, minio_key)

    citations = []
    context_parts = []
    for node_id, title, content, pages, bboxes in rows:
        context_parts.append(f"[{title}]\n{content}")
        citations.append({
            "node_id": node_id,
            "title": title,
            "pages": pages,
            "bboxes": bboxes,
            "source_url": presigned_url,   # URL file gốc, client dùng page+bbox để highlight
        })

    final = client.chat.completions.create(
        model="gpt-4o-2024-11-20",
        messages=[
            {"role": "system", "content": "Answer using only the provided document content."},
            {"role": "user", "content": f"Query: {query}\n\nContent:\n{chr(10).join(context_parts)}"}
        ]
    )

    return {
        "answer": final.choices[0].message.content,
        "citations": citations   # client dùng source_url + page + bbox để render highlight
    }
```

**Response trả về client:**

```json
{
  "answer": "Điều khoản thanh toán quy định...",
  "citations": [
    {
      "node_id": "0003",
      "title": "Điều 5 — Thanh toán",
      "pages": [4, 5],
      "bboxes": [
        {"page": 4, "bbox": [120, 340, 890, 420]},
        {"page": 5, "bbox": [120, 80, 890, 200]}
      ],
      "source_url": "https://minio.host/documents/uuid.pdf?X-Amz-..."
    }
  ]
}
```

---

## Lưu ý quan trọng

**Giới hạn OSS cần biết:**
- OSS repo chỉ build tree, không có sẵn query engine — traversal và answer synthesis phải tự implement
- Mỗi node summary là 1 LLM call → tài liệu nhiều trang sẽ tốn token khi build index
- Prompts được tuned cho GPT-4 class, chưa hỗ trợ multi-provider
