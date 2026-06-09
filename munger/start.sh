#!/bin/bash
# Munger startup script

echo "================================"
echo "  Munger Knowledge Base"
echo "  Starting services..."
echo "================================"
echo ""

BACKEND_PORT="${BACKEND_PORT:-18000}"
FRONTEND_PORT="${FRONTEND_PORT:-13000}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

# Create data directories
mkdir -p data/sources data/wiki data/schema

# Frontend image builds directly from ../app via Docker Compose
echo "Preparing frontend build context..."

# Start services
echo ""
echo "Starting Munger services..."
docker-compose up --build -d

echo ""
echo "================================"
echo "  Munger is running!"
echo ""
echo "  Frontend: http://localhost:${FRONTEND_PORT}"
echo "  Backend API: http://localhost:${BACKEND_PORT}"
echo "  API Docs: http://localhost:${BACKEND_PORT}/docs"
echo ""
echo "  Data directory: ./data/"
echo ""
echo "  To view logs: docker-compose logs -f"
echo "  To stop: docker-compose down"
echo "================================"
