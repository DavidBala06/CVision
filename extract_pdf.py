from langchain_community.document_loaders import PyPDFLoader

loader = PyPDFLoader(r"d:/buildathon/CVision/Linnify challenge - AI Talent Pool Manager.pdf")
pages = loader.load()

with open("challenge_text.txt", "w", encoding="utf-8") as f:
    for i, p in enumerate(pages):
        f.write(f"=== PAGE {i+1} ===\n")
        f.write(p.page_content)
        f.write("\n\n")

print(f"Done! Extracted {len(pages)} pages to challenge_text.txt")
