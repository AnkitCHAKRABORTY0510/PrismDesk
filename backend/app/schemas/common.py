from typing import Generic, TypeVar

from pydantic import BaseModel, Field
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class PageParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class MessageResponse(BaseModel):
    message: str


def paginate(
    db: Session,
    statement: Select,
    params: PageParams,
    scalars: bool = True,
) -> tuple[list, int]:
    """Run ``statement`` with LIMIT/OFFSET and return (rows, total).

    The total is computed in SQL from the unordered statement so whole
    tables are never loaded into Python.
    """

    total = db.scalar(
        select(func.count()).select_from(
            statement.order_by(None).subquery()
        )
    ) or 0

    paged = statement.limit(params.page_size).offset(params.offset)
    result = db.execute(paged)
    rows = list(result.scalars().unique().all()) if scalars else list(result.all())

    return rows, total
