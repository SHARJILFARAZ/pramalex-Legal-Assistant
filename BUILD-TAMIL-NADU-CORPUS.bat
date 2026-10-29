@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo PramaLex - Tamil Nadu Civil and Property Corpus
echo Source: vaquill/open-india-law
echo Output: D:\PramaLexData\raw\real_judgments.jsonl
echo Target: 2,500 distinct cases (maximum 3,000)
echo ============================================================
echo This requires internet access and may take a while.
echo It will NOT overwrite an existing corpus unless a validated output is built.
echo.
choice /M "Build the corpus now"
if errorlevel 2 exit /b 0
if not exist "D:\PramaLexData\raw" mkdir "D:\PramaLexData\raw"
py -m pip install "datasets>=3.0,<5.0" "huggingface_hub>=0.25"
if errorlevel 1 goto failed
py scripts\build_tamil_nadu_property_corpus.py --target 2500
if errorlevel 1 goto failed
echo.
echo Build finished. Check D:\PramaLexData\raw\corpus_manifest.json
echo Do not treat keyword selection as legal verification.
pause
exit /b 0
:failed
echo.
echo Build failed. Read the error above. Existing corpus should remain intact.
pause
exit /b 1
