#!/bin/bash
# Inicia conector Baileys se existir
if [ -d "whatsapp_baileys" ]; then
    echo "🚀 [START] Iniciando Baileys WhatsApp..."
    NODE_OPTIONS="--max-old-space-size=128" node whatsapp_baileys/index.js &
fi

# Inicia Gunicorn imediatamente na porta informada pelo Render
echo "🌐 [START] Iniciando Gunicorn na porta $PORT..."
exec gunicorn app:app --workers 1 --threads 4 --bind 0.0.0.0:$PORT
