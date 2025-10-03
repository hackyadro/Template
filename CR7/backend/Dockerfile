FROM python:3.10-slim

# Рабочая директория внутри контейнера
WORKDIR /app

# Скопировать зависимости
COPY requirements.txt .

# Установить зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Скопировать код
COPY . .

# Запустить приложение
CMD ["python", "main.py"]
