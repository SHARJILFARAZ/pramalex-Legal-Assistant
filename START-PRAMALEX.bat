@echo off
setlocal
echo PramaLex fresh build startup helper
echo Ensure MySQL is running and the database/user in backend environment are configured.
start "PramaLex API - Spring Boot" cmd /k "cd /d %~dp0backend && set JWT_SECRET=CHANGE_THIS_TO_A_RANDOM_SECRET_WITH_32_OR_MORE_CHARACTERS && mvn spring-boot:run"
start "PramaLex AI - FastAPI" cmd /k "cd /d %~dp0ai-service && python -m uvicorn app.main:app --reload --port 8000"
start "PramaLex Frontend" cmd /k "cd /d %~dp0frontend && npm install && npm run dev"
echo Three terminals opened. See README.md and docs/BOOTSTRAP_ADMIN.md before first use.
