# Stage 1: Get uv binary
FROM ghcr.io/astral-sh/uv:latest as uv

# Stage 2: Build image with Python and uv
FROM python:3.12.9-slim as build

# Copy uv binary from the uv image
COPY --from=uv /uv /bin/uv

# Set up virtual environment
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app

# Create venv and install dependencies
RUN uv venv $VIRTUAL_ENV

COPY requirements.txt .
RUN uv pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cu121 --index-strategy unsafe-best-match

# Copy the rest of the code
COPY . .

# Stage 3: Final image (optional, for smaller images)
# FROM python:3.12.9-slim
# COPY --from=build /opt/venv /opt/venv
# COPY --from=build /app /app
# ENV VIRTUAL_ENV=/opt/venv
# ENV PATH="$VIRTUAL_ENV/bin:$PATH"
# WORKDIR /app

# Default command
CMD ["python", "mcp_server/main.py"]