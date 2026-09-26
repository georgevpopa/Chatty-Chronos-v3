@echo off
chcp 65001 >nul
title Chatty Chronos — Web UI Launcher

cd /d "%~dp0"

echo.
echo  ==========================================
echo   Chatty Chronos v3  —  Web Dashboard
echo  ==========================================
echo.

:: ---- Verifică Python ----
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [EROARE] Python nu e in PATH. Instaleaza Python 3.10+ si adauga-l la PATH.
    pause
    exit /b 1
)

:: ---- Verifică deps critice ----
python -c "import fastapi, uvicorn, chromadb, sentence_transformers" 2>nul
if %errorlevel% neq 0 (
    echo [AVERTISMENT] Lipsesc dependente. Ruleaza:  pip install -r requirements.txt
    echo.
)

:: ---- Citește config curent (provider/model) ----
set "CURRENT_PROVIDER=necunoscut"
set "CURRENT_MODEL=necunoscut"
set "CONFIG_PATH=%USERPROFILE%\.chatty-chronos\config.json"
if exist "%CONFIG_PATH%" (
    for /f "tokens=2 delims=:" %%a in ('findstr /r /c:"\"provider\"" "%CONFIG_PATH%" 2^>nul') do set "CURRENT_PROVIDER=%%a"
    for /f "tokens=2 delims=:" %%a in ('findstr /r /c:"\"model\"" "%CONFIG_PATH%" 2^>nul') do set "CURRENT_MODEL=%%a"
    for %%v in (%CURRENT_PROVIDER%) do set "CURRENT_PROVIDER=%%~v"
    for %%v in (%CURRENT_MODEL%) do set "CURRENT_MODEL=%%~v"
)

echo Config curent:
echo   Provider : %CURRENT_PROVIDER%
echo   Model    : %CURRENT_MODEL%
echo.

:: ---- Meniul rapid ----
echo Ce vrei sa faci?
echo.
echo   [1] Porneste Web UI cu configul actual
echo   [2] Schimba provider / model (Ollama local)
echo   [3] Schimba provider / model (llama.cpp local GPU)
echo   [4] Schimba provider / model (Groq cloud)
echo   [5] Schimba provider / model (NVIDIA / OpenRouter / Mistral / Gemini)
echo   [6] Editeaza config.json manual (Notepad)
echo   [0] Iesire
echo.

choice /c 1234560 /n /m "Alege optiunea: "
echo.

if errorlevel 7 goto :LAUNCH
if errorlevel 6 goto :EDIT_CONFIG
if errorlevel 5 goto :SET_CLOUD
if errorlevel 4 goto :SET_GROQ
if errorlevel 3 goto :SET_LLAMACPP
if errorlevel 2 goto :SET_OLLAMA
goto :EXIT

:SET_OLLAMA
echo.
echo Setez provider=ollama ...
python -c "
import json, os
p = os.path.expanduser(r'~\.chatty-chronos\config.json')
with open(p, 'r', encoding='utf-8') as f: cfg = json.load(f)
cfg['provider'] = 'ollama'
cfg['model'] = 'llama3.1:8b'
cfg['ollama_host'] = 'http://localhost:11434'
with open(p, 'w', encoding='utf-8') as f: json.dump(cfg, f, indent=2)
print('OK: ollama / llama3.1:8b')
"
echo Verifică că Ollama rulează (ollama serve) și modelul epullat (ollama pull llama3.1:8b).
timeout /t 2 >nul
goto :LAUNCH

:SET_LLAMACPP
echo.
echo Setez provider=llamacpp (GPU local) ...
python -c "
import json, os
p = os.path.expanduser(r'~\.chatty-chronos\config.json')
with open(p, 'r', encoding='utf-8') as f: cfg = json.load(f)
cfg['provider'] = 'llamacpp'
cfg['model'] = 'auto'
cfg['llamacpp_host'] = 'http://localhost:8080'
cfg['local_server_enabled'] = True
cfg['local_server_bin'] = r'E:\\AI_Sandbox\\llama-b9827-bin-win-vulkan-x64\\llama-server.exe'
cfg['local_server_model'] = r'E:\\AI_Sandbox\\models\\llama-3.1-8b-instruct-q4_k_m.gguf'
cfg['local_server_port'] = 8080
cfg['local_server_ngl'] = 35
cfg['local_server_ctx'] = 16384
cfg['local_server_env'] = {
    'HSA_OVERRIDE_GFX_VERSION': '11.0.2',
    'HIP_VISIBLE_DEVICES': '0'
}
with open(p, 'w', encoding='utf-8') as f: json.dump(cfg, f, indent=2)
print('OK: llamacpp / GPU AMD (ngl=35)')
print('Verifică că calea la llama-server.exe si modelul GGUF sunt corecte!')
"
timeout /t 3 >nul
goto :LAUNCH

:SET_GROQ
echo.
set /p GROQ_KEY="Introdu GROQ_API_KEY (sau Enter pentru a sări): "
if "%GROQ_KEY%"=="" goto :LAUNCH
python -c "
import json, os
p = os.path.expanduser(r'~\.chatty-chronos\config.json')
with open(p, 'r', encoding='utf-8') as f: cfg = json.load(f)
cfg['provider'] = 'groq'
cfg['model'] = 'llama-3.1-70b-versatile'
with open(p, 'w', encoding='utf-8') as f: json.dump(cfg, f, indent=2)
print('OK: groq / llama-3.1-70b-versatile')
"
setx GROQ_API_KEY "%GROQ_KEY%" >nul
echo Cheie salvată în Environment Variables (reauțește terminalul).
timeout /t 2 >nul
goto :LAUNCH

:SET_CLOUD
echo.
echo Provideri cloud disponibili: nvidia, openrouter, mistral, gemini
set /p CLOUD_PROV="Provider (nvidia/openrouter/mistral/gemini): "
set /p CLOUD_MODEL="Model ID (ex: nvidia/llama-3.1-nemotron-70b-instruct): "
set /p CLOUD_KEY="API Key: "
if "%CLOUD_PROV%"=="" goto :LAUNCH
python -c "
import json, os
p = os.path.expanduser(r'~\.chatty-chronos\config.json')
with open(p, 'r', encoding='utf-8') as f: cfg = json.load(f)
cfg['provider'] = r'%CLOUD_PROV%'
cfg['model'] = r'%CLOUD_MODEL%'
with open(p, 'w', encoding='utf-8') as f: json.dump(cfg, f, indent=2)
print('OK: %CLOUD_PROV% / %CLOUD_MODEL%')
"
setx "%CLOUD_PROV:_=%_API_KEY" "%CLOUD_KEY%" >nul 2>&1
echo Cheie salvată. Repornește terminalul ca să fie activă.
timeout /t 2 >nul
goto :LAUNCH

:EDIT_CONFIG
notepad "%CONFIG_PATH%"
goto :LAUNCH

:LAUNCH
echo.
echo ==========================================
echo  Pornesc Web UI pe http://localhost:8000
echo ==========================================
echo.
python main.py --web

:EXIT