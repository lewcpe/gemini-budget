import pytest
from httpx import AsyncClient
import io

@pytest.mark.asyncio
async def test_upload_document(client: AsyncClient, auth_headers: dict):
    file_content = b"fake file content"
    file = io.BytesIO(file_content)
    
    response = await client.post(
        "/documents/upload",
        files={"file": ("test.txt", file, "text/plain")},
        data={"user_note": "Test note"},
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["original_filename"] == "test.txt"
    assert data["user_note"] == "Test note"

@pytest.mark.asyncio
async def test_list_documents(client: AsyncClient, auth_headers: dict):
    # Upload one
    await client.post(
        "/documents/upload",
        files={"file": ("doc.pdf", b"pdf data", "application/pdf")},
        headers=auth_headers
    )
    
    response = await client.get("/documents/", headers=auth_headers)
    assert response.status_code == 200
    assert any(d["original_filename"] == "doc.pdf" for d in response.json())

@pytest.mark.asyncio
async def test_delete_document(client: AsyncClient, auth_headers: dict):
    upload_res = await client.post(
        "/documents/upload",
        files={"file": ("delete_me.txt", b"data", "text/plain")},
        headers=auth_headers
    )
    doc_id = upload_res.json()["id"]
    
    del_res = await client.delete(f"/documents/{doc_id}", headers=auth_headers)
    assert del_res.status_code == 204
    
    list_res = await client.get("/documents/", headers=auth_headers)
    assert all(d["id"] != doc_id for d in list_res.json())
