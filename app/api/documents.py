import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from app.auth.jwt_handler import get_current_admin, get_current_user
from app.database.connection import get_collection
from app.services.document_parser import extract_text
from app.services.embedding import embedding_service
from app.services.vector_search import perform_vector_search
from app.utils.text_splitter import split_document_pages
from bson import ObjectId

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["Documents"])

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_admin: dict = Depends(get_current_admin)
):
    """
    Upload a document (PDF, DOCX, TXT) and process it.
    Extracts text, splits into chunks, computes embeddings, and stores in database.
    Only accessible by administrators.
    """
    filename = file.filename
    ext = filename.split(".")[-1].lower()
    if ext not in ["pdf", "docx", "txt", "md"]:
        logger.warning(f"File upload rejected: Unsupported extension .{ext} for {filename}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format: .{ext}. Only PDF, DOCX, TXT, and MD are supported."
        )

    try:
        # Read file bytes
        file_bytes = await file.read()
        
        # Save file to disk under uploads folder
        import os
        uploads_dir = os.path.join("backend", "app", "uploads")
        if not os.path.exists(uploads_dir):
            uploads_dir = os.path.join("app", "uploads")
            os.makedirs(uploads_dir, exist_ok=True)
            
        file_path = os.path.join(uploads_dir, filename)
        with open(file_path, "wb") as f:
            f.write(file_bytes)
        logger.info(f"Saved file {filename} to disk at {file_path}")
        
        # Step 1: Extract Text
        logger.info(f"Admin {current_admin.get('email')} uploading file: {filename}")
        pages = extract_text(filename, file_bytes)
        if not pages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No text could be extracted from this document."
            )
            
        # Step 2: Split text into chunks
        chunks = split_document_pages(pages)
        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document split generated 0 chunks."
            )

        # Step 3: Generate embeddings for chunks
        chunk_texts = [c["chunk"] for c in chunks]
        logger.info(f"Generating embeddings for {len(chunk_texts)} chunks...")
        start_time = datetime.utcnow()
        embeddings = embedding_service.get_embeddings(chunk_texts)
        emb_duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Generated embeddings in {emb_duration:.2f} seconds.")

        # Step 4: Write Document record to DB
        docs_collection = get_collection("documents")
        doc_record = {
            "title": filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title(),
            "filename": filename,
            "uploadedBy": ObjectId(current_admin["_id"]),
            "uploadedAt": datetime.utcnow()
        }
        doc_result = await docs_collection.insert_one(doc_record)
        doc_id = doc_result.inserted_id

        # Step 5: Write Chunks to DB
        chunks_collection = get_collection("document_chunks")
        db_chunks = []
        for idx, chunk in enumerate(chunks):
            db_chunks.append({
                "documentId": ObjectId(doc_id),
                "chunk": chunk["chunk"],
                "embedding": embeddings[idx],
                "page": chunk["page"],
                "metadata": {
                    "document_name": doc_record["title"],
                    "filename": filename,
                    "uploaded_at": datetime.utcnow().isoformat(),
                    "start_idx": chunk["start_idx"],
                    "end_idx": chunk["end_idx"]
                }
            })
            
        await chunks_collection.insert_many(db_chunks)
        logger.info(f"Successfully uploaded and indexed document: {filename} with ID: {doc_id}")
        
        return {
            "message": "Document uploaded and indexed successfully",
            "document_id": str(doc_id),
            "filename": filename,
            "chunks_count": len(db_chunks)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload document {filename}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}"
        )

@router.get("", response_model=List[dict])
async def list_documents(current_user: dict = Depends(get_current_user)):
    """Retrieve list of all indexed college documents."""
    docs_collection = get_collection("documents")
    cursor = docs_collection.find()
    documents = []
    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        doc["uploadedBy"] = str(doc["uploadedBy"])
        documents.append(doc)
    return documents

@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
async def delete_document(
    document_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    """Delete a document and all its indexed chunks from vector database."""
    if not ObjectId.is_valid(document_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID"
        )
        
    obj_id = ObjectId(document_id)
    docs_collection = get_collection("documents")
    
    # Check if document exists
    doc = await docs_collection.find_one({"_id": obj_id})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
        
    try:
        # Delete the file from disk if it exists
        import os
        filename = doc.get("filename")
        if filename:
            for parent_dir in ["backend/app/uploads", "app/uploads"]:
                file_path = os.path.join(parent_dir, filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Deleted file from disk: {file_path}")
                    break
                    
        # Delete document chunks first
        chunks_collection = get_collection("document_chunks")
        chunk_delete_result = await chunks_collection.delete_many({"documentId": obj_id})
        
        # Delete main document record
        await docs_collection.delete_one({"_id": obj_id})
        
        logger.info(
            f"Admin {current_admin['email']} deleted document {doc['filename']} "
            f"and {chunk_delete_result.deleted_count} vector chunks."
        )
        
        return {
            "message": "Document deleted successfully",
            "chunks_deleted": chunk_delete_result.deleted_count
        }
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )

@router.get("/search")
async def search_documents(
    q: str = Query(..., min_length=1),
    limit: int = Query(5, ge=1, le=20),
    current_user: dict = Depends(get_current_user)
):
    """
    Search indexed college documents semantically using vector similarity.
    Returns the most relevant chunks, similarity scores, pages, and titles.
    """
    logger.info(f"User {current_user.get('email')} performing document search: '{q}'")
    results = await perform_vector_search(q, limit)
    return results
