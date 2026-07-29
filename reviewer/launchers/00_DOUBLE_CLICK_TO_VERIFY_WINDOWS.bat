@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title BGVD-State v1.1.1 No-Install Reviewer Check

if not exist "runtime\python.exe" (
    echo REVIEWER KIT INCOMPLETE
    echo.
    echo The private runtime is missing from this folder.
    echo Re-extract the complete reviewer ZIP or download it again.
    echo You do not need to install Python or any other software.
    if not "%BGVD_REVIEWER_NO_PAUSE%"=="1" pause
    exit /b 1
)

"runtime\python.exe" -I -s "reviewer_offline_check.py"
set "BGVD_EXIT=%errorlevel%"

echo.
if "%BGVD_EXIT%"=="0" (
    echo Reviewer check completed successfully. Opening the result page...
) else (
    echo Reviewer check did not pass. Opening the explanation and logs...
)
if not "%BGVD_REVIEWER_NO_OPEN%"=="1" (
    if exist "reviewer_output\REVIEWER_CHECK_SUMMARY.html" (
        start "" "reviewer_output\REVIEWER_CHECK_SUMMARY.html"
    )
)
if not "%BGVD_REVIEWER_NO_PAUSE%"=="1" (
    echo.
    echo Press any key to close this window.
    pause
)
exit /b %BGVD_EXIT%
