FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

FROM base AS builder
WORKDIR /w
COPY app/requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
ENV PATH="/usr/local/bin:$PATH"

COPY --from=builder /install /usr/local
COPY app/ /app/

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
