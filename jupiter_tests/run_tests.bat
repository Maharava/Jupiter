@echo off
echo Jupiter Test Suite Runner
echo =======================

REM Check for Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH. Please install Python 3.7 or higher.
    exit /b 1
)

REM Create directories if they don't exist
if not exist test_results mkdir test_results

REM Run tests
echo Running tests... This may take a few minutes.
python run_tests.py %*

REM Check test result
if %errorlevel% neq 0 (
    echo.
    echo Tests failed! See test_results directory for detailed reports.
) else (
    echo.
    echo All tests passed!
)

echo.
echo Test run complete. Check test_results directory for detailed reports.
pause
