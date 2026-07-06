import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient

from app import logger
from app.constants import DEFAULT_FRONTEND_URL
from app.core.config import setup_logger
from app.core.manager import lifespan
from app.core.redis import RedisHelper
from app.core.settings import Settings
from app.router.activity_logs import router as activity_logs_router
from app.router.auth import router as auth_router
from app.router.base import router as base_router
from app.router.blogs import router as blogs_router
from app.router.dashboard import router as dashboard_router
from app.router.rbac import router as rbac_router
from app.router.reports import router as reports_router

_settings = Settings()

app = FastAPI(lifespan=lifespan, debug=_settings.debug, docs_url="/api/docs")

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")
uploads_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(os.path.join(uploads_dir, "blogs"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

setup_logger(_settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        DEFAULT_FRONTEND_URL,
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(base_router)
app.include_router(auth_router)
app.include_router(rbac_router)
app.include_router(blogs_router)
app.include_router(activity_logs_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")


# Static page routes


@app.get("/", response_class=FileResponse)
@app.get("/index.html", response_class=FileResponse)
async def root() -> FileResponse:
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.get("/dashboard", response_class=FileResponse)
@app.get("/dashboard.html", response_class=FileResponse)
async def dashboard() -> FileResponse:
    return FileResponse(os.path.join(static_dir, "dashboard.html"))


@app.get("/profile", response_class=FileResponse)
@app.get("/profile.html", response_class=FileResponse)
async def profile_page() -> FileResponse:
    return FileResponse(os.path.join(static_dir, "profile.html"))


@app.get("/users", response_class=FileResponse)
@app.get("/users.html", response_class=FileResponse)
async def users_page() -> FileResponse:
    return FileResponse(os.path.join(static_dir, "users.html"))


@app.get("/roles", response_class=FileResponse)
@app.get("/roles.html", response_class=FileResponse)
async def roles_page() -> FileResponse:
    return FileResponse(os.path.join(static_dir, "roles.html"))


@app.get("/superadmin", response_class=FileResponse)
@app.get("/superadmin.html", response_class=FileResponse)
async def superadmin_page() -> FileResponse:
    return FileResponse(os.path.join(static_dir, "superadmin.html"))


@app.get("/admin", response_class=FileResponse)
@app.get("/admin.html", response_class=FileResponse)
async def admin_page() -> FileResponse:
    return FileResponse(os.path.join(static_dir, "admin.html"))


@app.get("/admins", response_class=FileResponse)
@app.get("/admins.html", response_class=FileResponse)
async def admins_page() -> FileResponse:
    return FileResponse(os.path.join(static_dir, "admins.html"))


@app.get("/reports", response_class=FileResponse)
@app.get("/reports.html", response_class=FileResponse)
async def reports_page() -> FileResponse:
    return FileResponse(os.path.join(static_dir, "reports.html"))


@app.get("/blogs", response_class=FileResponse)
@app.get("/blogs.html", response_class=FileResponse)
async def blogs_page() -> FileResponse:
    return FileResponse(os.path.join(static_dir, "blogs.html"))


@app.get("/blog-review", response_class=FileResponse)
@app.get("/blog-review.html", response_class=FileResponse)
async def blog_review_page() -> FileResponse:
    return FileResponse(os.path.join(static_dir, "blog-review.html"))


client = TestClient(app)


def add_cache_layer(app: FastAPI) -> None:
    try:
        app.state.cache = RedisHelper()
    except (OSError, ValueError) as e:
        logger.error(e)
