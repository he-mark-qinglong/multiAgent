FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code (tools.py needs tests/mock_tools)
COPY backend/ ./backend/
COPY tests/ ./tests/

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
