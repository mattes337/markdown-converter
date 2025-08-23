FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including Chrome for headless browsing
RUN apt-get update && apt-get install -y \
    curl \
    pandoc \
    poppler-utils \
    libxml2-dev \
    libxslt1-dev \
    wget \
    gnupg \
    unzip \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install 'markitdown[all]'

# Copy application code
COPY server.py .
COPY browser_utils.py .

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "server.py"]
