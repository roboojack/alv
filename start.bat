@echo off
setlocal

echo === Starting Backend ===
cd backend

if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate
    echo Installing backend dependencies...
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate
)

:: Start uvicorn in a new window so it runs in parallel
start "ALV Backend" uvicorn app.main:app --reload

cd ..

echo === Starting Frontend ===
cd label-verifier-ui

if not exist node_modules (
    echo Installing frontend dependencies...
    call npm install
)

echo Starting Angular app...
npm start

endlocal
