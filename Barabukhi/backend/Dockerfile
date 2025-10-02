FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements и установка Python зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование приложения
COPY app/ ./app/
COPY migrations/ ./migrations/

# Создание скрипта для ожидания PostgreSQL и миграций
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "Waiting for PostgreSQL..."\n\
while ! pg_isready -h postgres -p 5432 -U indoor_user; do\n\
  sleep 1\n\
done\n\
echo "PostgreSQL is ready!"\n\
\n\
echo "Running migrations..."\n\
export PGPASSWORD=indoor_pass\n\
psql -h postgres -U indoor_user -d indoor_navigation -f /app/migrations/001_initial_schema.sql || true\n\
echo "Migrations complete!"\n\
\n\
echo "Starting application..."\n\
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload\n\
' > /app/start.sh && chmod +x /app/start.sh

EXPOSE 8000

CMD ["/app/start.sh"]
