# Use official Python 3.12.9 image
FROM python:3.12.9-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Set the default command to run the server
CMD ["python", "mcp_server/main.py"] 