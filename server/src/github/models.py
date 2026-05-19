from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = [
    "Author",
    "Label",
    "LinkedIssue",
    "MergeableState",
    "PRContext",
]

MergeableState = Literal["MERGEABLE", "CONFLICTING", "UNKNOWN"]


class Label(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str


class Author(BaseModel):
    model_config = ConfigDict(frozen=True)

    login: str


def _flatten_connection(value: Any) -> Any:
    if isinstance(value, dict):
        return [node for node in (value.get("nodes") or []) if node]
    return value


class LinkedIssue(BaseModel):
    model_config = ConfigDict(frozen=True)

    number: int
    title: str
    body: str | None = None
    labels: list[Label] = Field(default_factory=list)

    @field_validator("labels", mode="before")
    @classmethod
    def _flatten_labels(cls, value: Any) -> Any:
        return _flatten_connection(value)


class PRContext(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    number: int
    title: str
    body: str | None = None
    url: str
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    author: Author | None = None
    head_ref_name: str = Field(alias="headRefName")
    mergeable: MergeableState = "UNKNOWN"
    additions: int
    deletions: int
    changed_files: int = Field(alias="changedFiles")
    labels: list[Label] = Field(default_factory=list)
    linked_issues: list[LinkedIssue] = Field(
        default_factory=list, alias="closingIssuesReferences"
    )

    @field_validator("labels", mode="before")
    @classmethod
    def _flatten_labels(cls, value: Any) -> Any:
        return _flatten_connection(value)

    @field_validator("linked_issues", mode="before")
    @classmethod
    def _flatten_linked_issues(cls, value: Any) -> Any:
        return _flatten_connection(value)

    @field_validator("mergeable", mode="before")
    @classmethod
    def _default_mergeable(cls, value: Any) -> Any:
        return value or "UNKNOWN"
