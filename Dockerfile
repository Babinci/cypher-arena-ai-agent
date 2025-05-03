# Stage 1: Get uv binary
FROM ghcr.io/astral-sh/uv:latest AS uv

# Stage 2: Build image with Python, CUDA, and uv
FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04 AS build

# Copy uv binary from the uv image
COPY --from=uv /uv /usr/local/bin/uv

# Install Python 3.12, pip, venv, and essential build tools using deadsnakes PPA
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        software-properties-common \
        git \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && \
    apt-get install -y --no-install-recommends \
        python3.12 \
        python3.12-venv \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install pip for Python 3.12
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12

# Make python3.12 the default python3
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

# Set up virtual environment using the installed python3.12
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app

# Install dependencies using uv
COPY requirements.txt .
RUN uv pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cu121 --index-strategy unsafe-best-match

# Copy the rest of the application code
COPY . .

# Default command
CMD ["python", "mcp_server/main.py"]