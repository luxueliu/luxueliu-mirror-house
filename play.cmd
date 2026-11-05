@echo off
rem Mirror House launcher. ASCII only: cmd.exe decodes .cmd with the system code page.
setlocal
set "HERE=%~dp0"

where py >nul 2>nul
if not errorlevel 1 goto :usepy
where python >nul 2>nul
if not errorlevel 1 goto :usepython

echo Python 3 not found. Install Python 3.8+ first.
set "RC=1"
goto :done

:usepy
py -3 "%HERE%mirror_house.py" %*
set "RC=%ERRORLEVEL%"
goto :done

:usepython
python "%HERE%mirror_house.py" %*
set "RC=%ERRORLEVEL%"
goto :done

:done
if "%~1"=="" pause
exit /b %RC%
