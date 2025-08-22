FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    pandoc \
    poppler-utils \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install 'markitdown[all]'

# Copy application code
COPY server.py .

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "server.py"]
