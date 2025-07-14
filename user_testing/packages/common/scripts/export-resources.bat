@echo off

REM HERITRACE Testing - Resources Export Script
REM This script exports the modified resources (Shuffle and Display Rules) from Docker volumes

echo 📦 HERITRACE Resources Export
echo ==============================================

set "ROOT_DIR=%~dp0"

set "EXPORT_DIR=%ROOT_DIR%export"
set "ZIP_FILE=%cd%\export.zip"

set "SOURCE_DIR=.\resources"

if not exist "%SOURCE_DIR%" (
    echo Error: 'resources' directory not found in the current location.
    pause
    exit /b 1
)

set "SHACL_FILE=%SOURCE_DIR%\shacl.ttl"
set "DISPLAY_RULES_FILE=%SOURCE_DIR%\display_rules.yaml"

if not exist "%SHACL_FILE%" if not exist "%DISPLAY_RULES_FILE%" (
    echo Error: Neither 'shacl.ttl' nor 'display_rules.yaml' found in the 'resources' directory.
    pause
    exit /b 1
)

if exist "%EXPORT_DIR%" rmdir /s /q "%EXPORT_DIR%"
mkdir "%EXPORT_DIR%"

echo Copying resources to export directory...

if exist "%SHACL_FILE%" (
    copy "%SHACL_FILE%" "%EXPORT_DIR%\" >nul
    echo    - Found shacl.ttl
)

if exist "%DISPLAY_RULES_FILE%" (
    copy "%DISPLAY_RULES_FILE%" "%EXPORT_DIR%\" >nul
    echo    - Found display_rules.yaml
)

echo Creating zip archive...
powershell -command "Compress-Archive -Path '%EXPORT_DIR%\*' -DestinationPath '%ZIP_FILE%' -Force" > nul

echo Cleaning up temporary directory...
if exist "%EXPORT_DIR%" rmdir /s /q "%EXPORT_DIR%"

echo Successfully exported resources to: %ZIP_FILE%