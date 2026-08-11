@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Atualizar deputados federais (Camara)
echo ============================================================
echo    Atualizador de deputados federais - API da Camara
echo ============================================================
echo.

rem 1) Garante um Python isolado (.venv) com a biblioteca 'requests'.
if not exist ".venv\Scripts\python.exe" (
  echo [1 de 2] Primeira vez: preparando o ambiente ^(demora ~1 min^)...
  py -3 -m venv .venv 2>nul || python -m venv .venv
  if not exist ".venv\Scripts\python.exe" (
    echo.
    echo ERRO: nao encontrei o Python neste computador.
    echo Instale em https://www.python.org/downloads/ , marque "Add Python to PATH",
    echo e rode este arquivo de novo.
    echo.
    pause
    exit /b 1
  )
  ".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
  ".venv\Scripts\python.exe" -m pip install --quiet requests
)

rem 2) Busca os deputados de SP na Camara e grava no CSV.
echo [2 de 2] Buscando os deputados federais de SP na Camara...
echo.
".venv\Scripts\python.exe" -m src.camara_federais
echo.
echo ------------------------------------------------------------
echo A planilha ficou em:  data\deputados_federais_camara.csv
echo Se apareceu algum ERRO acima, tire um print e me mande.
echo ------------------------------------------------------------
echo.
pause
