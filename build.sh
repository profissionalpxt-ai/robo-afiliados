#!/usr/bin/env bash
set -o errexit

echo "📦 [BUILD] Instalando dependencias Python..."
pip install -r requirements.txt

if [ -d "whatsapp_baileys" ]; then
    echo "📦 [BUILD] Instalando dependencias Node do Baileys..."
    cd whatsapp_baileys
    npm install --production
    cd ..
fi

echo "✅ [BUILD] Build concluido com sucesso!"
