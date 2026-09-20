from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Page:
    page: int
    per_page: int
    total: int

    @property
    def total_pages(self) -> int:
        return total_pages(self.total, self.per_page)

    @property
    def offset(self) -> int:
        return self.page * self.per_page

    @property
    def has_prev(self) -> bool:
        return self.page > 0

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages - 1


def total_pages(total: int, per_page: int) -> int:
    if per_page <= 0:
        raise ValueError("per_page must be positive")
    if total <= 0:
        return 1
    return math.ceil(total / per_page)


def clamp_page(page: int, total: int, per_page: int) -> int:
    return max(0, min(page, total_pages(total, per_page) - 1))
