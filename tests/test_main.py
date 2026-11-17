import pytest
from starlette.testclient import TestClient

from app.main import app, seed_data


@pytest.fixture
def client():
    seed_data()
    return TestClient(app)


def test_root(client):
    assert client.get("/").json() == {"service": "book-catalog", "books": 3}


def test_list_books_pagination(client):
    r = client.get("/books?skip=1&limit=1")
    assert r.status_code == 200
    assert [b["id"] for b in r.json()] == [2]


def test_list_books_filter_by_author(client):
    r = client.get("/books?author=kernighan")
    assert [b["title"] for b in r.json()] == ["The C Programming Language"]


def test_read_book_not_found(client):
    r = client.get("/books/999")
    assert r.status_code == 404
    assert r.json() == {"detail": "Book not found"}


def test_create_book_normalizes_input(client):
    r = client.post(
        "/books",
        json={"title": "  Clean Code ", "author": "Robert Martin", "year": 2008,
              "tags": ["Craft", " craft", "", "Java"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == 4
    assert body["title"] == "Clean Code"
    assert body["tags"] == ["craft", "java"]


def test_create_book_validation_error(client):
    r = client.post("/books", json={"title": "", "author": "X", "year": 1200})
    assert r.status_code == 422


def test_create_book_rejects_extra_fields(client):
    r = client.post("/books", json={"title": "A", "author": "B", "year": 2000, "isbn": "x"})
    assert r.status_code == 422


def test_update_and_delete(client):
    r = client.put("/books/1", json={"title": "SICP", "author": "Abelson", "year": 1996})
    assert r.json()["title"] == "SICP"
    assert client.delete("/books/1").json() == {"deleted": 1}
    assert client.get("/books/1").status_code == 404


def test_openapi_schema(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert "/books/{book_id}" in r.json()["paths"]
