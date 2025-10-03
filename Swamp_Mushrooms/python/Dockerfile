FROM python:3.12-slim

# зависимости для сборки + линковки
RUN apt-get update && apt-get install -y \
    build-essential cmake g++ git pkg-config \
    libeigen3-dev \
    libgoogle-glog-dev libgflags-dev \
    libopenblas-dev liblapack-dev libsuitesparse-dev \
    pybind11-dev \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y \
    libabsl-dev \
    && rm -rf /var/lib/apt/lists/*


# Сборка ceres (нет deb-пакета во многих slim образах)
RUN apt-get update && apt-get install -y \
    libceres-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# requirements отдельно (чтобы кешировалось)
COPY python/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# теперь копируем всё нужное
COPY CMakeLists.txt .
COPY cpp ./cpp
COPY python ./python

# сборка C++ pybind11 модуля
RUN mkdir -p build && cd build && cmake .. && make -j$(nproc)

ENV PYTHONPATH=/app/build/cpp:$PYTHONPATH
ENV PYTHONPATH=/app:$PYTHONPATH

WORKDIR /app/python
CMD ["python", "main.py"]