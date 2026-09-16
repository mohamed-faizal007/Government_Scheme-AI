 .\venv\Scripts\Activate.ps1
 Terminal 1 (backend):

uvicorn chatbot.backend.api.main:app --reload --port 8000

Terminal 2 (frontend):

cd chatbot/frontend
npm run dev

