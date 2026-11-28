@echo off
rem Start the whole RAKSHA stack with one action: preflight, both app processes,
rem both Phosphor console origins, and a readiness wait before this window ends.
rem
rem   start.bat                 start (or report the stack that is already up)
rem   start.bat --status        show what is running and where
rem   start.bat --check         preflight only, start nothing
rem   start.bat --timeout 180   more patience for a cold venv or a slow disk
rem   start.bat --restart       stop, then start again
rem
rem All real logic lives in tools\launch_apps.py so this file and start.sh can
rem never drift apart. Nothing here starts a database or a broker (the audit
rem ledger is in-process), and no model run, eval or Commander call is executed.
rem
rem The two servers keep running after this window closes. Stop them with
rem stop.bat; logs land in .raksha\logs\ and the pid record in
rem .raksha\launcher.json (both git-ignored). The window waits for a keypress
rem only when you double-clicked this file; set RAKSHA_BAT_NOPAUSE to skip it.
setlocal EnableExtensions
cd /d "%~dp0"

set "PY="
set "PYARGS="
set "HADARGS="
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
echo FAIL: no Python interpreter found. Install Python 3.11+ and create the venv:
echo       py -3 -m venv .venv ^&^& .venv\Scripts\python -m pip install -r requirements.txt
set "RC=1"
goto report

:pyfound
if not exist "tools\launch_apps.py" (
  echo FAIL: tools\launch_apps.py is missing. Run start.bat from the repository root.
  set "RC=1"
  goto report
)

set "MODE=--detach"
set "EXTRA="
:args
if "%~1"=="" goto argsdone
set "HADARGS=1"
if /i "%~1"=="--status"   ( set "MODE=--status"   & shift & goto args )
if /i "%~1"=="--check"    ( set "MODE=--check"    & shift & goto args )
if /i "%~1"=="--stop"     ( set "MODE=--stop"     & shift & goto args )
if /i "%~1"=="--restart"  ( set "MODE=--restart"  & shift & goto args )
set EXTRA=%EXTRA% "%~1"
shift
goto args

:argsdone
echo using %PY%%PYARGS% to run tools\launch_apps.py %MODE%%EXTRA%
echo.
if defined PYARGS (
  "%PY%" %PYARGS% tools\launch_apps.py %MODE%%EXTRA%
) else (
  "%PY%" tools\launch_apps.py %MODE%%EXTRA%
)
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo start.bat exited with %RC%. Read .raksha\logs\infra.log and
  echo .raksha\logs\citizen.log, then run "start.bat --check" for preflight detail.
)

:report
if not defined HADARGS if not defined RAKSHA_BAT_NOPAUSE if not defined RAKSHA_CI pause
set "EXITCODE=%RC%"
endlocal & exit /b %EXITCODE%
