"""A small book-catalog API written against FastAPI 0.1.0 (December 2018).

Deliberately uses the APIs of that era so it can serve as an upgrade target:
  - FastAPI is imported from `fastapi.applications` (0.1.0 had no top-level exports)
  - HTTPException comes from Starlette
  - pydantic 0.x `Schema`, `constr`, `Config.ignore_extra`, `@validator(whole=True)`, `.dict()`
  - `@app.on_event("startup")` for initialization
"""
from typing import Dict, List

from fastapi.applications import FastAPI
from fastapi.params import Depends, Path, Query
from pydantic import BaseModel, Schema, constr, validator
from starlette.exceptions import HTTPException

app = FastAPI(title="Book Catalog", version="0.1.0")

# In-memory storage, populated at startup.
BOOKS: Dict[int, dict] = {}


class BookIn(BaseModel):
    title: constr(strip_whitespace=True, min_length=1, max_length=200)
    author: constr(strip_whitespace=True, min_length=1, max_length=100)
    year: int = Schema(..., ge=1450, le=2100)
    tags: List[str] = []

    @validator("tags", whole=True)
    def normalize_tags(cls, v):
        return sorted({t.strip().lower() for t in v if t.strip()})

    class Config:
        ignore_extra = False  # reject unknown fields


class BookOut(BookIn):
    id: int


class Pagination:
    """Reusable query-parameter dependency."""

    def __init__(
        self,
        skip: int = Query(0, ge=0),
        limit: int = Query(10, ge=1, le=100),
    ):
        self.skip = skip
        self.limit = limit


def get_book_or_404(book_id: int) -> dict:
    book = BOOKS.get(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@app.on_event("startup")
def seed_data():
    BOOKS.clear()
    for i, (title, author, year) in enumerate(
        [
            ("Structure and Interpretation of Computer Programs", "Abelson & Sussman", 1985),
            ("The C Programming Language", "Kernighan & Ritchie", 1978),
            ("Design Patterns", "Gamma et al.", 1994),
        ],
        start=1,
    ):
        BOOKS[i] = {"id": i, "title": title, "author": author, "year": year, "tags": []}


@app.get("/")
def root():
    return {"service": "book-catalog", "books": len(BOOKS)}


@app.get("/books", response_model=List[BookOut])
def list_books(
    author: str = Query(None, max_length=100),
    page: Pagination = Depends(Pagination),
):
    books = sorted(BOOKS.values(), key=lambda b: b["id"])
    if author:
        books = [b for b in books if author.lower() in b["author"].lower()]
    return books[page.skip : page.skip + page.limit]


@app.get("/books/{book_id}", response_model=BookOut)
def read_book(book_id: int = Path(..., ge=1)):
    return get_book_or_404(book_id)


@app.post("/books", response_model=BookOut)
def create_book(book: BookIn):
    new_id = max(BOOKS, default=0) + 1
    BOOKS[new_id] = {"id": new_id, **book.dict()}
    return BOOKS[new_id]


@app.put("/books/{book_id}", response_model=BookOut)
def update_book(book: BookIn, book_id: int = Path(..., ge=1)):
    get_book_or_404(book_id)
    BOOKS[book_id] = {"id": book_id, **book.dict()}
    return BOOKS[book_id]


@app.delete("/books/{book_id}")
def delete_book(book_id: int = Path(..., ge=1)):
    get_book_or_404(book_id)
    del BOOKS[book_id]
    return {"deleted": book_id}
