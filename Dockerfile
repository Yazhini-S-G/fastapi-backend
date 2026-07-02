FROM python:3.12-slim

WORKDIR /app

# Create a non-root user and group
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app appuser

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY static ./static
COPY uploads ./uploads

COPY alembic.ini .
COPY pyproject.toml .
COPY requirements.txt .
COPY gunicorn_config.py .

# Set correct ownership of /app
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]