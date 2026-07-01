from datetime import datetime

from pydantic import BaseModel, Field


class BlogCategoryOut(BaseModel):
    id: int
    name: str
    description: str | None = None


class BlogCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    content: str = Field(min_length=1)
    category_id: int | None = None
    tags: str = ""
    featured_image: str | None = None
    action: str = "draft"


class BlogUpdateRequest(BlogCreateRequest):
    """Request payload for updating a blog."""


class BlogStatusRequest(BaseModel):
    status: str


class BlogOut(BaseModel):
    id: int
    title: str
    content: str
    featured_image: str | None
    author_id: int
    author_name: str
    status: str
    category_id: int | None
    category_name: str | None
    tags: str
    is_featured: bool
    created_at: datetime
    updated_at: datetime
    # Lifecycle tracking fields
    approved_by_name: str | None = None
    approved_at: datetime | None = None
    published_by_name: str | None = None
    published_at: datetime | None = None


class BlogAnalyticsOut(BaseModel):
    total_blogs: int
    published_blogs: int
    pending_blogs: int
    rejected_blogs: int
    draft_blogs: int
    most_active_authors: list[dict[str, object]]
    recent_blogs: list[BlogOut]
    blogs_by_category: list[dict[str, object]]
