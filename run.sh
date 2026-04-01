#!/bin/bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "starting postgresql..."
docker compose -f "$ROOT/docker-compose.yml" up -d

echo "waiting for postgresql to be ready..."
until docker compose -f "$ROOT/docker-compose.yml" exec -T postgres pg_isready -U supersight_user -d supersight > /dev/null 2>&1; do
    sleep 1
done
echo "postgresql is ready"

echo "setting up pipeline..."
cd "$ROOT/pipeline"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -q

echo "running pipeline..."
python -m src.main
deactivate

echo "setting up web application..."
cd "$ROOT/web-application"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -q

echo "starting dashboard at http://localhost:8000/"
python manage.py runserver
