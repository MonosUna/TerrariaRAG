#!/bin/sh
set -e

cd /app

echo "Checking Chroma databases..."

if [ ! -d "terraria_db/general" ] || [ -z "$(ls -A terraria_db/general 2>/dev/null || true)" ]; then
    echo "Creating general DB..."
    python src/manage_db.py create \
        --persist_directory terraria_db/general \
        --json_path data/data/wiki_dump_cleaned.json \
        --min_length 200
else
    echo "General DB already exists, skipping."
fi

if [ ! -d "terraria_db/recipes" ] || [ -z "$(ls -A terraria_db/recipes 2>/dev/null || true)" ]; then
    echo "Creating recipes DB..."
    python src/manage_db.py create \
        --persist_directory terraria_db/recipes \
        --json_path data/data/recipes.json \
        --min_length 0
else
    echo "Recipes DB already exists, skipping."
fi

echo "Starting API..."
exec uvicorn src.api:app --host 0.0.0.0 --port 8000

