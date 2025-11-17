from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from tqdm import tqdm
import json
import argparse
from uuid import uuid4

def create_db(json_path: str, 
              persist_directory: str, 
              embedding_model: str = "intfloat/multilingual-e5-large",
              use_cuda: bool = True,
              chunk_size: int = 5000,
              chunk_overlap: int = 1000,
              min_length: int = 0,
              separators: list[str] = ["\n\n", "\n", " "],
              ) -> None:
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    inputs = []
    for item in data:
        if isinstance(item, str):
            inputs.append(data[item].get('content', ''))
        else:
            inputs.append(item.get('content', ''))
            
    documents = [Document(page_content=text) for text in inputs]
    
    text_splitter = RecursiveCharacterTextSplitter(separators=separators, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = text_splitter.split_documents(documents)
    chunks = [chunk for chunk in chunks if len(chunk.page_content) >= min_length]
    
    embedding = HuggingFaceEmbeddings(model_name=embedding_model, model_kwargs={"device": "cuda" if use_cuda else "cpu"})
    vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embedding)
    
    uuids = [str(uuid4()) for _ in range(len(chunks))]
    vectorstore.add_documents(documents=chunks, ids=uuids)
    
    print(f"Database created at {persist_directory} with {len(chunks)} chunks.")
    
def delete_db(persist_directory: str) -> None:
    vectorstore = Chroma(persist_directory=persist_directory)
    vectorstore._client.delete_collection(name=vectorstore._collection.name)
    print(f"Database at {persist_directory} has been deleted.")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage the vector database.")
    parser.add_argument("action", choices=["create", "delete"], help="Action to perform: create or delete the database.")
    parser.add_argument("--json_path", type=str, help="Path to the JSON file containing the data.")
    parser.add_argument("--persist_directory", type=str, required=True, help="Directory to persist the vector database.")
    parser.add_argument("--embedding_model", type=str, default="intfloat/multilingual-e5-large", help="Embedding model to use.")
    parser.add_argument("--use_cuda", action="store_true", help="Whether to use CUDA for embeddings.")
    parser.add_argument("--chunk_size", type=int, default=5000, help="Chunk size for text splitting.")
    parser.add_argument("--chunk_overlap", type=int, default=1000, help="Chunk overlap for text splitting.")
    parser.add_argument("--min_length", type=int, default=0, help="Minimum length for text chunks.")
    parser.add_argument("--separators", type=str, nargs='+', default=["\n\n", "\n", " "], help="List of separators for text splitting.")
    parser.add_argument("--db_path", type=str, help="Path to the database to delete.")
    args = parser.parse_args()
    
    if args.action == "create":
        if not args.json_path:
            raise ValueError("json_path is required for creating the database.")
        create_db(
            json_path=args.json_path,
            persist_directory=args.persist_directory,
            embedding_model=args.embedding_model,
            use_cuda=args.use_cuda,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            min_length=args.min_length,
            separators=args.separators
        )
    
    elif args.action == "delete":
        if not args.persist_directory:
            raise ValueError("persist_directory is required for deleting the database.")
        delete_db(persist_directory=args.persist_directory)
        