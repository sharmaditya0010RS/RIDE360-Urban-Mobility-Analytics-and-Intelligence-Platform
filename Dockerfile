FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_HEADLESS=true

WORKDIR /app

COPY pyproject.toml requirements-dashboard.txt ./
COPY src/ ./src/
COPY dashboard/ ./dashboard/

RUN python -m pip install --no-cache-dir \
    -e . \
    -r requirements-dashboard.txt

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s \
    --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=3)"

CMD ["python", "-m", "streamlit", "run", "dashboard/app.py"]
