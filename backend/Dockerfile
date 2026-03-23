FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (including chromium dependencies for Playwright)
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    gnupg2 \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libxrender1 \
    libxt6 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libuuid1 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers and dependencies
RUN python -m playwright install --with-deps

# Prepare cache directory for Playwright
RUN mkdir -p /root/.cache/ms-playwright

# Copy app
COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
