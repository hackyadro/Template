FROM python:3.11-slim

# Никаких системных dev-пакетов не ставим
# (wheels scipy/numpy/matplotlib ставятся через pip)
WORKDIR /app

ENV MPLBACKEND=Agg 

# requirements лежит в app/
COPY ./app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# код
COPY ./app/ /app/

CMD ["bash", "-c", "sleep infinity"]
