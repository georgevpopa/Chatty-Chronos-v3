@echo off
title Chatty Chronos v3 Launcher
color 0A

:meniu_principal
cls
echo ========================================================
echo         CHATTY CHRONOS V3 - MASTER LAUNCHER
echo ========================================================
echo.
echo  1. LOCAL RUNTIME (Radeon 890M GPU - AMD ROCm/HIP)
echo  2. CLOUD RUNTIME (API Providers - Gemini, Groq, etc.)
echo.
echo  0. IESIRE
echo ========================================================
set /p rmode="Alege tipul de rulare (0-2) si apasa ENTER: "

if "%rmode%"=="1" goto meniu_local
if "%rmode%"=="2" goto meniu_api
if "%rmode%"=="0" exit
echo Selectie invalida! Incearca din nou.
pause
goto meniu_principal

:meniu_local
cls
echo ========================================================
echo         SELECTIE MODEL LOCAL (iGPU Radeon 890M)
echo ========================================================
echo.
echo  [ MODELE DE COD SI LOGICA ]
echo  1. Qwen 2.5.1 Coder Instruct (7B)
echo  2. Qwen 3.5 (9B)
echo  3. Qwen 3.6 (27B) - GREU
echo  4. Google Gemma 4 IT (12B)
echo  5. Google Gemma 4 A4B IT (26B) - GREU
echo.
echo  [ MODELE CREATIVE / ROLEPLAY / DIVERSE ]
echo  6. Tiger Gemma v3b (12B)
echo  7. Cream Phi-3 v1 (14B)
echo  8. rpDungeon Gemma 4 E4B Luchador
echo  9. Gemmasutra v1c (9B)
echo 10. TheDrummer Gemmasutra Small (4B)
echo.
echo  B. Inapoi la meniul principal
echo ========================================================
set /p optiune="Alege numarul modelului (1-10 / B) si apasa ENTER: "

if "%optiune%"=="1" set FISIER=Qwen2.5.1-Coder-7B-Instruct-Q4_K_M.gguf
if "%optiune%"=="2" set FISIER=Qwen_Qwen3.5-9B-Q4_K_M.gguf
if "%optiune%"=="3" set FISIER=Qwen_Qwen3.6-27B-Q4_K_M.gguf
if "%optiune%"=="4" set FISIER=gemma-4-12B-it-Q4_K_M.gguf
if "%optiune%"=="5" set FISIER=google_gemma-4-26B-A4B-it-Q4_K_M.gguf
if "%optiune%"=="6" set FISIER=Tiger-Gemma-12B-v3b-Q4_K_M.gguf
if "%optiune%"=="7" set FISIER=Cream-Phi-3-14B-v1-Q4_K_M.gguf
if "%optiune%"=="8" set FISIER=rpDungeon_Gemma-4-E4B-Luchador-Q4_K_M.gguf
if "%optiune%"=="9" set FISIER=Gemmasutra-9B-v1c-Q4_K_M.gguf
if "%optiune%"=="10" set FISIER=TheDrummer_Gemmasutra-Small-4B-v1-Q4_K_M.gguf
if /i "%optiune%"=="B" goto meniu_principal

if not defined FISIER (
    echo Selectie invalida! Incearca din nou.
    pause
    goto meniu_local
)

:: Salvare setari local server prin Python (include optimized server flags)
python -c "from core.config import Config; c = Config(); c.set('provider', 'llamacpp'); c.set('model', '%FISIER%'); c.set('local_server_enabled', True); c.set('local_server_model', 'E:\\AI_Sandbox\\llama-b9627-bin-win-vulkan-x64\\%FISIER%'); c.set('llamacpp_host', 'http://localhost:8069'); c.set('local_server_port', 8069); c.set('local_server_parallel', 1); c.set('local_server_reasoning_budget', 1024); c.set('local_server_cache_ram', 512)"

cls
echo ========================================================
echo INCARC MODEL LOCAL: %FISIER%
echo HARDWARE: Radeon 890M ROCm/HIP (Port 8069)
echo.
echo OPTIMIZARI ACTIVE:
echo   --parallel 1          (un singur slot, elibereaza VRAM)
echo   --reasoning-budget 1024 (cap la tokeni de gandire)
echo   --cache-ram 512       (limita cache prompt 512 MiB)
echo ========================================================
echo.
python main.py
echo.
echo Chatty Chronos s-a oprit.
pause
set FISIER=
goto meniu_principal


:meniu_api
cls
echo ========================================================
echo         SELECTIE MODEL CLOUD (API BASED)
echo ========================================================
echo.
echo  1. Google Gemini 2.0 Flash
echo  2. Groq Llama 3.3 70B Versatile
echo  3. OpenRouter Llama 3.3 70B Instruct
echo  4. Mistral Small Latest
echo.
echo  B. Inapoi la meniul principal
echo ========================================================
set /p api_opt="Alege API-ul (1-4 / B) si apasa ENTER: "

if "%api_opt%"=="1" (
    set PROVIDER=gemini
    set MODEL=gemini-2.0-flash
)
if "%api_opt%"=="2" (
    set PROVIDER=groq
    set MODEL=llama-3.3-70b-versatile
)
if "%api_opt%"=="3" (
    set PROVIDER=openrouter
    set MODEL=meta-llama/llama-3.3-70b-instruct
)
if "%api_opt%"=="4" (
    set PROVIDER=mistral
    set MODEL=mistral-small-latest
)
if /i "%api_opt%"=="B" goto meniu_principal

if not defined PROVIDER (
    echo Selectie invalida! Incearca din nou.
    pause
    goto meniu_api
)

:: Salvare setari API prin Python (dezactivam serverul local)
python -c "from core.config import Config; c = Config(); c.set('provider', '%PROVIDER%'); c.set('model', '%MODEL%'); c.set('local_server_enabled', False)"

cls
echo ========================================================
echo INCARC RUNTIME API: %PROVIDER% (%MODEL%)
echo ========================================================
echo.
python main.py
echo.
echo Chatty Chronos s-a oprit.
pause
set PROVIDER=
set MODEL=
goto meniu_principal
