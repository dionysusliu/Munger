FROM python:3.12-slim

WORKDIR /app

# Ensure pip has a writable temp directory during build
RUN mkdir -p /tmp /var/tmp && chmod 1777 /tmp /var/tmp
ENV TMPDIR=/tmp

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Tesseract language data for LiteParse OCR (prepare via scripts/prepare-tessdata.sh)
COPY tessdata/ /app/tessdata/
ENV TESSDATA_PREFIX=/app/tessdata

# Copy application code
COPY . .

# Preserve built-in workflows outside the /app/data bind mount path.
RUN cp -r /app/data/workflows /app/builtin-workflows

# Create data directories
RUN mkdir -p /app/data/sources /app/data/wiki /app/data/schema

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# Run with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
