from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app import logger
from app.core.database import get_db

router = APIRouter(prefix="/api", tags=["base"])


@router.get("/health")
async def health_check(db: Annotated[AsyncSession, Depends(get_db)]) -> JSONResponse:
    try:
        await db.execute(text("SELECT 1"))
        return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "All Healthy"})
    except ProgrammingError:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"error": "Database connection failed"}
        )
    except asyncpg.InvalidCatalogNameError:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "Database not found"})
    except asyncpg.InvalidPasswordError:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"error": "Invalid password"})
    except OSError:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"error": "Database unreachable"}
        )
    except SQLAlchemyError as e:
        logger.exception(f"Unexpected health check failure: {e}")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"error": str(e)})


@router.get("/pulse")
def pulse() -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "I'm Alive"})
