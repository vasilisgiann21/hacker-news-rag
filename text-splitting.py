from langchain_text_splitters import RecursiveCharacterTextSplitter

with open("hackernews.txt", "r", encoding="utf-8") as f:
    raw_text = f.read()
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000,chunk_overlap=200)
new_text = text_splitter.split_text(raw_text)
print(len(new_text))
