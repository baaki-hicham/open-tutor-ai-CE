#!/bin/bash

# 🚀 Script de développement pour Open TutorAI
# Lance le frontend (npm) + backend (Python) + vérifie Ollama

echo "🔍 Vérification des prérequis..."

# Vérifier que Ollama répond
if ! curl -s --max-time 5 http://127.0.0.1:11434/api/version > /dev/null; then
    echo "⚠️  Ollama ne répond pas sur http://127.0.0.1:11434"
    echo "   Lancez 'ollama serve' ou vérifiez le service"
    read -p "Continuer quand même ? (o/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Oo]$ ]]; then
        exit 1
    fi
fi

echo "🚀 Lancement du frontend (npm run dev)..."
cd frontend  # Adaptez si le dossier s'appelle autrement
npm install --silent 2>/dev/null
npm run dev &
FRONTEND_PID=$!

echo "🚀 Lancement du backend (Python)..."
cd ../backend  # Adaptez si le dossier s'appelle autrement
python3 -m venv venv 2>/dev/null || true
source venv/bin/activate 2>/dev/null || true
pip install -r requirements.txt --quiet 2>/dev/null
export OLLAMA_BASE_URL=http://127.0.0.1:11434
uvicorn main:app --reload --host 0.0.0.0 --port 3000 &
BACKEND_PID=$!

echo ""
echo "✅ Open TutorAI en développement !"
echo "   🌐 Frontend : http://localhost:5173 (ou port indiqué par Vite)"
echo "   🔌 Backend  : http://localhost:3000"
echo "   🤖 Ollama   : http://127.0.0.1:11434"
echo ""
echo "💡 Pour arrêter : Ctrl+C ou './stop-tutorai.sh'"
echo "💡 Logs backend : tail -f backend/logs/app.log (si existant)"

# Attendre que l'utilisateur appuie sur Ctrl+C
wait $FRONTEND_PID $BACKEND_PID
