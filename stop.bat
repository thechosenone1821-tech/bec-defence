@echo off
rem Stop exactly the RAKSHA processes that start.bat started — and nothing else.
rem
rem   stop.bat                        stop the recorded stack
rem   stop.bat --state-dir DIR        stack recorded in another run directory
rem
rem Each recorded pid is verified to still run the expected app module on the
rem expected port before it is signalled, so a recycled pid belonging to another
rem program is reported and left alone. A stack that is not running at all exits
rem successfully: stop is idempotent.
setlocal EnableExtensions
cd /d "%~dp0"

set "PY="
set "PYARGS="
if defined RAKSHA_PYTHON (
  set "PY=%RAKSHA_PYTHON%"
  goto pyfound
)
if exist ".venv\Scripts\python.exe" (
  set "PY=.venv\Scripts\python.exe"
  goto pyfound
)
where py >nul 2>nul
if not errorlevel 1 (
  set "PY=py"
  set "PYARGS=-3"
  goto pyfound
)
where python >nul 2>nul
if not errorlevel 1 (
  set "PY=python"
  goto pyfound
)
echo FAIL: no Python interpreter to read .raksha\launcher.json. If the apps were
echo       started another way, find and stop them yourself:
echo       wmic process where "name like '%%python%%'" get processid,commandline
set "RC=1"
goto report

:pyfound
if defined PYARGS (
  "%PY%" %PYARGS% tools\launch_apps.py --stop %*
) else (
  "%PY%" tools\launch_apps.py --stop %*
)
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo stop.bat exited with %RC%: a process was left running on purpose. Read the
  echo PROBLEM line above before signalling anything by hand.
)

:report
set "EXITCODE=%RC%"
endlocal & exit /b %EXITCODE%
