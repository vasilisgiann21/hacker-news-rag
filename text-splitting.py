import json
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

# ==================== CONFIGURATION ====================
INPUT_FILE = "output.jsonl"       # Crawler output (JSONL)
OUTPUT_FILE = "chunks.jsonl"      # Semantically split chunks
CHUNK_SIZE = 800                  # Characters per chunk
CHUNK_OVERLAP = 150               # Overlap between chunks
# =======================================================

def load_crawled_pages(input_file):
    """Read JSONL file and return list of page dictionaries."""
    pages = []
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                pages.append(json.loads(line))
    return pages

def split_code_snippet(code, max_chars=CHUNK_SIZE):
    """
    Split a code snippet intelligently, keeping lines intact when possible.
    If a single line exceeds max_chars, it is hard‑split to avoid oversized chunks.
    """
    if len(code) <= max_chars:
        return [code]

    lines = code.split('\n')
    chunks = []
    current_chunk = []
    current_len = 0

    for line in lines:
        # If a single line is longer than max_chars, hard split it
        if len(line) > max_chars:
            # Flush current chunk first
            if current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = []
                current_len = 0
            # Hard split the long line into pieces of size max_chars
            for i in range(0, len(line), max_chars):
                chunks.append(line[i:i+max_chars])
            continue

        # Normal line – check if adding it exceeds chunk size
        if current_len + len(line) + 1 > max_chars and current_chunk:
            chunks.append('\n'.join(current_chunk))
            current_chunk = [line]
            current_len = len(line)
        else:
            current_chunk.append(line)
            current_len += len(line) + 1  # +1 for newline

    if current_chunk:
        chunks.append('\n'.join(current_chunk))

    return chunks

def main():
    pages = load_crawled_pages(INPUT_FILE)

    # Markdown splitter – relies on '#' style headers
    headers_to_split_on = [("#", "h1"), ("##", "h2"), ("###", "h3")]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)

    # Recursive splitter for enforcing size limit while preserving metadata
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f_out:
        for page in pages:
            url = page.get("url", "")
            title = page.get("title", "")
            content = page.get("content", "")
            markdown_content = page.get("markdown", content)  # fallback to plain text
            code_snippets = page.get("code_snippets", [])
            depth = page.get("depth", 0)

            # ----- 1. Split textual content -----
            final_text_chunks = []

            if markdown_content:
                # Step 1: Split by Markdown headers → Documents with header metadata
                md_docs = markdown_splitter.split_text(markdown_content)

                if md_docs:
                    # Step 2: Chain into RecursiveCharacterTextSplitter to enforce size limit
                    # This preserves metadata automatically
                    sized_docs = text_splitter.split_documents(md_docs)

                    for doc in sized_docs:
                        chunk_text = doc.page_content
                        metadata = doc.metadata

                        # Build breadcrumb from preserved header metadata
                        breadcrumb_parts = []
                        if "h1" in metadata:
                            breadcrumb_parts.append(metadata["h1"])
                        if "h2" in metadata:
                            breadcrumb_parts.append(metadata["h2"])
                        if "h3" in metadata:
                            breadcrumb_parts.append(metadata["h3"])
                        if breadcrumb_parts:
                            breadcrumb = " > ".join(breadcrumb_parts)
                            chunk_text = f"[{breadcrumb}]\n\n{chunk_text}"

                        final_text_chunks.append(chunk_text)
                else:
                    # No headers found → fallback to direct recursive splitting
                    final_text_chunks = text_splitter.split_text(markdown_content)
            else:
                # No content
                pass

            # ----- 2. Write text chunks with metadata -----
            for i, chunk_text in enumerate(final_text_chunks):
                chunk_obj = {
                    "chunk_id": f"{url}#text{i}",
                    "url": url,
                    "title": title,
                    "depth": depth,
                    "chunk_text": chunk_text,
                    "chunk_type": "text"
                }
                f_out.write(json.dumps(chunk_obj, ensure_ascii=False) + "\n")

            # ----- 3. Process code snippets (with global index to avoid ID collision) -----
            code_global_idx = 0
            for snippet in code_snippets:
                code_parts = split_code_snippet(snippet)
                for part in code_parts:
                    chunk_obj = {
                        "chunk_id": f"{url}#code{code_global_idx}",
                        "url": url,
                        "title": title,
                        "depth": depth,
                        "chunk_text": f"```\n{part}\n```",
                        "chunk_type": "code"
                    }
                    f_out.write(json.dumps(chunk_obj, ensure_ascii=False) + "\n")
                    code_global_idx += 1

    print(f"✅ Splitting complete. Chunks saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()