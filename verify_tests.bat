@echo off
setlocal enabledelayedexpansion

echo Jupiter Test Suite Verification
echo ============================
echo.

set ERROR_COUNT=0
set MISSING_FILES=

REM Check for main directories
echo Checking test directories...
for %%D in (mocks test_utils unit_tests integration_tests functional_tests ui_tests) do (
    if not exist "jupiter_tests\%%D" (
        echo [ERROR] Missing directory: jupiter_tests\%%D
        set /a ERROR_COUNT+=1
    ) else (
        echo [OK] Found directory: jupiter_tests\%%D
    )
)

REM Check for main script files
echo.
echo Checking main script files...
for %%F in (run_tests.bat run_tests.py) do (
    if not exist "jupiter_tests\%%F" (
        echo [ERROR] Missing file: jupiter_tests\%%F
        set /a ERROR_COUNT+=1
        set MISSING_FILES=!MISSING_FILES! jupiter_tests\%%F
    ) else (
        echo [OK] Found file: jupiter_tests\%%F
    )
)

REM Check mock files
echo.
echo Checking mock files...
for %%F in (
    __init__.py
    mock_llm.py
    mock_voice.py
    mock_discord.py
) do (
    if not exist "jupiter_tests\mocks\%%F" (
        echo [ERROR] Missing file: jupiter_tests\mocks\%%F
        set /a ERROR_COUNT+=1
        set MISSING_FILES=!MISSING_FILES! jupiter_tests\mocks\%%F
    ) else (
        echo [OK] Found file: jupiter_tests\mocks\%%F
    )
)

REM Check test utils
echo.
echo Checking test utility files...
for %%F in (
    __init__.py
    test_environment.py
    test_helpers.py
) do (
    if not exist "jupiter_tests\test_utils\%%F" (
        echo [ERROR] Missing file: jupiter_tests\test_utils\%%F
        set /a ERROR_COUNT+=1
        set MISSING_FILES=!MISSING_FILES! jupiter_tests\test_utils\%%F
    ) else (
        echo [OK] Found file: jupiter_tests\test_utils\%%F
    )
)

REM Check unit tests
echo.
echo Checking unit test files...
for %%F in (
    __init__.py
    test_llm_client.py
    test_user_model.py
    test_info_extractor.py
    test_calendar.py
) do (
    if not exist "jupiter_tests\unit_tests\%%F" (
        echo [ERROR] Missing file: jupiter_tests\unit_tests\%%F
        set /a ERROR_COUNT+=1
        set MISSING_FILES=!MISSING_FILES! jupiter_tests\unit_tests\%%F
    ) else (
        echo [OK] Found file: jupiter_tests\unit_tests\%%F
    )
)

REM Check integration tests
echo.
echo Checking integration test files...
for %%F in (
    __init__.py
    test_chat_user_integration.py
    test_calendar_integration.py
) do (
    if not exist "jupiter_tests\integration_tests\%%F" (
        echo [ERROR] Missing file: jupiter_tests\integration_tests\%%F
        set /a ERROR_COUNT+=1
        set MISSING_FILES=!MISSING_FILES! jupiter_tests\integration_tests\%%F
    ) else (
        echo [OK] Found file: jupiter_tests\integration_tests\%%F
    )
)

REM Check functional tests
echo.
echo Checking functional test files...
for %%F in (
    __init__.py
    test_first_time_user.py
    test_returning_user.py
    test_calendar_workflow.py
) do (
    if not exist "jupiter_tests\functional_tests\%%F" (
        echo [ERROR] Missing file: jupiter_tests\functional_tests\%%F
        set /a ERROR_COUNT+=1
        set MISSING_FILES=!MISSING_FILES! jupiter_tests\functional_tests\%%F
    ) else (
        echo [OK] Found file: jupiter_tests\functional_tests\%%F
    )
)

REM Check UI tests
echo.
echo Checking UI test files...
for %%F in (
    __init__.py
    test_terminal_ui.py
    test_gui.py
) do (
    if not exist "jupiter_tests\ui_tests\%%F" (
        echo [ERROR] Missing file: jupiter_tests\ui_tests\%%F
        set /a ERROR_COUNT+=1
        set MISSING_FILES=!MISSING_FILES! jupiter_tests\ui_tests\%%F
    ) else (
        echo [OK] Found file: jupiter_tests\ui_tests\%%F
    )
)

REM Check for README
echo.
echo Checking documentation...
if not exist "jupiter_tests\README.md" (
    echo [ERROR] Missing file: jupiter_tests\README.md
    set /a ERROR_COUNT+=1
    set MISSING_FILES=!MISSING_FILES! jupiter_tests\README.md
) else (
    echo [OK] Found file: jupiter_tests\README.md
)

REM Output summary
echo.
echo ============================
if %ERROR_COUNT% EQU 0 (
    echo [SUCCESS] All test files are in the correct locations.
) else (
    echo [FAILURE] Found %ERROR_COUNT% missing files or directories.
    echo Missing items: %MISSING_FILES%
)

echo.
echo Verification complete.
pause
