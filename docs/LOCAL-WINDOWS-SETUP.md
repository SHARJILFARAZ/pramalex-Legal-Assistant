# Windows setup

## 1. MySQL
Start MySQL and run:
```sql
CREATE DATABASE pramalex CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```
Set `MYSQL_USER`, `MYSQL_PASSWORD`, `JWT_SECRET` in your terminal or environment. Do not commit real secrets.

## 2. API
```powershell
cd backend
$env:MYSQL_DATABASE="pramalex"
$env:MYSQL_USER="root"
$env:MYSQL_PASSWORD="your-mysql-password"
$env:JWT_SECRET="use-a-random-secret-that-is-at-least-32-characters"
mvn spring-boot:run
```
API is on `http://localhost:8080`. Hibernate creates/updates tables during development.

## 3. AI service
```powershell
cd ai-service
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```
If using Command Prompt, activate with `.venv\Scripts\activate.bat` instead of the PowerShell script.
The AI service will show an empty corpus until `data/real_judgments.jsonl` exists at the repository root. Importer command is in `scripts/README.md`. After data download, call `POST http://localhost:8000/reload` or restart FastAPI.

## 4. Frontend
```powershell
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173`.

## 5. First admin
Follow `BOOTSTRAP_ADMIN.md`. The first account registered from the UI is Public. Admins can promote a reviewed account to Lawyer. Do not expose a bootstrap admin account publicly.

## Separate Madras land corpus

The existing bundled 1,000-record collection remains at `data/demo/pramalex_corpus_1000.jsonl`. The extracted Madras land corpus is a separate collection. Copy the complete `madras_land_candidates.jsonl` file to `data/candidates/madras_land_candidates.jsonl`, or configure `PRAMALEX_CANDIDATE_JUDGMENTS_PATH` to the absolute path of that file before starting the AI service. Do not replace the bundled file.

In Legal Research, select **Existing collection (1,000 records)** or **Madras land corpus** to search one collection at a time. The source JSONL is read-only; the service creates its TF-IDF index in memory. Records without a source URL are still searchable, but the app does not invent a source link.
