# Real judgment import

Install dependencies in the AI service environment, then run from repository root:

```powershell
python -m pip install -r ai-service/requirements.txt
python scripts/fetch_comprehensive_dataset.py --per-category 400 --scan-limit-per-config 500000
```

By default, the importer writes to `D:/PramaLexData/raw/real_judgments.jsonl` on Windows and targets up to 400 records in each of five issue categories (up to 2,000 total). Create the D: folder automatically through the script; no need to move the project. Override with `--output` if needed. The script streams the configured public Hugging Face dataset, accepts only records with judgment text, a recognized court and an actual source URL, deduplicates by URL, and filters to five property/civil issue groups. The importer supports alternate/nested field names and prints rejection reasons and sample input rows to diagnose upstream schema changes. It does not invent missing source URLs. The upstream schema/configuration and license can change. Check the dataset card and its terms before use. If fewer records exist, the script reports the shortfall; it does not create fake records.
