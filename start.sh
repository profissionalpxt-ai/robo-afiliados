#!/bin/bash
echo "📦 [INICIALIZACAO] Instalando pacotes do Baileys..."
cd whatsapp_baileys
npm install --production
cd ..

echo "🚀 [INICIALIZACAO] Subindo Baileys WhatsApp em segundo plano..."
node whatsapp_baileys/index.js &

echo "🌐 [INICIALIZACAO] Subindo servidor web Flask Gunicorn..."
exec gunicorn app:app --workers 1 --threads 4 --bind 0.0.0.0:$PORT
