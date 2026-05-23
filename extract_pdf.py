from langchain_community.document_loaders import PyPDFLoader
loader = PyPDFLoader(r"d:/buildathon/CVision/Linnify challenge - AI Talent Pool Manager.pdf")
pages = loader.load()
for p in pages:
    print(p.page_content)
    print("---PAGE BREAK---")
