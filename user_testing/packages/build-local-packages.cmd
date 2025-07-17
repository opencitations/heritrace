@echo off
setlocal enabledelayedexpansion

REM HERITRACE User Testing Package Builder
REM This script creates two standalone ZIP packages for user testing

echo [BUILD] Building HERITRACE User Testing Packages
echo ============================================

if not exist "..\..\app.py" (
    echo [ERROR] Error: This script must be run from user_testing\packages\
    echo    Current directory: %CD%
    pause
    exit /b 1
)

set BUILD_DIR=build
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
mkdir "%BUILD_DIR%"

echo [FILES] Preparing build environment...

call :prepare_package "enduser"
call :prepare_package "technician"

echo [ZIP] Creating ZIP packages...

cd "%BUILD_DIR%"

echo    Creating heritrace-enduser-local.zip...
powershell -command "Compress-Archive -Path 'heritrace-enduser-local' -DestinationPath '..\heritrace-enduser-local.zip' -Force"

echo    Creating heritrace-technician-local.zip...
powershell -command "Compress-Archive -Path 'heritrace-technician-local' -DestinationPath '..\heritrace-technician-local.zip' -Force"

cd ..

for %%A in (heritrace-enduser-local.zip) do set ENDUSER_SIZE=%%~zA
for %%A in (heritrace-technician-local.zip) do set TECHNICIAN_SIZE=%%~zA

set /a ENDUSER_SIZE_KB=%ENDUSER_SIZE%/1024
set /a TECHNICIAN_SIZE_KB=%TECHNICIAN_SIZE%/1024

echo.
echo [SUCCESS] Package build completed!
echo ==========================
echo [PKG] Created packages:
echo    [USER] heritrace-enduser-local.zip (%ENDUSER_SIZE_KB% KB)
echo    [TECH] heritrace-technician-local.zip (%TECHNICIAN_SIZE_KB% KB)
echo.
echo [INFO] Each package contains:
echo    - start.cmd - One-click startup (double-click to run)
echo    - stop.cmd - Clean shutdown (double-click to run)
echo    - README.md - Complete user instructions
echo    - sus_questionnaire.md - SUS usability questionnaire
echo    - written_responses_template.md - Written reflection questions template
echo    - A standalone Docker setup with all dependencies

echo.
echo [CLEAN] Cleaning up build directory...
rmdir /s /q "%BUILD_DIR%"

echo [DONE] Build complete!
pause
goto :eof

:prepare_package
set package_type=%~1
set build_package_dir=%BUILD_DIR%\heritrace-%package_type%-local

if "%package_type%"=="enduser" (
    set package_type_title=End User
) else (
    set package_type_title=Configurator
)

echo [PKG] Building %package_type% package...

mkdir "%build_package_dir%"

echo    Copying %package_type%-specific files...
xcopy "%package_type%\*" "%build_package_dir%\" /E /I /Q
copy "..\sus_questionnaire.md" "%build_package_dir%\sus_questionnaire.md"
copy "..\written_responses_template.md" "%build_package_dir%\written_responses_template.md"

echo    Generating scripts from templates...
call :generate_script_from_template "common\templates\scripts\start.cmd.template" "%build_package_dir%\start.cmd" "%package_type%" "%package_type_title%"
call :generate_script_from_template "common\templates\scripts\stop.cmd.template" "%build_package_dir%\stop.cmd" "%package_type%" "%package_type_title%"

echo    Copying common Docker files and data...
copy "common\dockerfiles\Dockerfile.virtuoso" "%build_package_dir%\"
copy "common\dockerfiles\Dockerfile.provenance" "%build_package_dir%\"
copy "common\dockerfiles\Dockerfile.heritrace" "%build_package_dir%\"

if "%package_type%"=="enduser" (
    copy "common\templates\docker-compose-enduser.yml" "%build_package_dir%\docker-compose.yml"
) else (
    copy "common\templates\docker-compose-technician.yml" "%build_package_dir%\docker-compose.yml"
)

echo    Copying common data directory...
mkdir "%build_package_dir%\data"
xcopy "common\data\*" "%build_package_dir%\data\" /E /I /Q

echo    Generating config.py from template...
call :generate_script_from_template "common\templates\config.py.template" "%build_package_dir%\config.py" "%package_type%" "%package_type_title%"

echo    Copying HERITRACE application files...
copy "..\..\app.py" "%build_package_dir%\"
copy "..\..\pyproject.toml" "%build_package_dir%\"
copy "..\..\poetry.lock" "%build_package_dir%\"
copy "..\..\package*.json" "%build_package_dir%\" 2>nul
copy "..\..\webpack.config.js" "%build_package_dir%\"

xcopy "..\..\heritrace" "%build_package_dir%\heritrace\" /E /I /Q
xcopy "..\..\babel" "%build_package_dir%\babel\" /E /I /Q

mkdir "%build_package_dir%\resources"
copy "..\..\resources\context.json" "%build_package_dir%\resources\"
copy "..\..\resources\datatypes.py" "%build_package_dir%\resources\"
copy "..\..\resources\datatypes_validation.py" "%build_package_dir%\resources\"
echo. > "%build_package_dir%\resources\__init__.py"

echo    Setting up Virtuoso database directories...
mkdir "%build_package_dir%\dataset_database"
mkdir "%build_package_dir%\prov_database"

echo    Creating Virtuoso configuration files...
copy "common\templates\virtuoso_dataset.ini" "%build_package_dir%\dataset_database\virtuoso.ini"
copy "common\templates\virtuoso_provenance.ini" "%build_package_dir%\prov_database\virtuoso.ini"

echo    Setting up scripts directory...
mkdir "%build_package_dir%\scripts"
copy "common\scripts\virtuoso_utils.py" "%build_package_dir%\scripts\"
copy "common\scripts\load_data.py" "%build_package_dir%\scripts\"
copy "common\scripts\setup_provenance.py" "%build_package_dir%\scripts\"
copy "common\scripts\virtuoso_entrypoint.sh" "%build_package_dir%\scripts\"
copy "common\scripts\provenance_entrypoint.sh" "%build_package_dir%\scripts\"

if "%package_type%"=="enduser" (
    copy "common\scripts\export-data.cmd" "%build_package_dir%\"
) else (
    copy "common\scripts\export-resources.cmd" "%build_package_dir%\"
)

echo    Adding Docker Hub scripts and compose files...
copy "common\scripts\push-to-dockerhub.sh" "%build_package_dir%\"

if "%package_type%"=="enduser" (
    copy "common\templates\docker-compose-dockerhub-enduser.yml" "%build_package_dir%\docker-compose-dockerhub.yml"
) else (
    copy "common\templates\docker-compose-dockerhub-technician.yml" "%build_package_dir%\docker-compose-dockerhub.yml"
)

REM Clean up Python cache files
for /d /r "%build_package_dir%" %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
del /s /q "%build_package_dir%\*.pyc" 2>nul

echo    [DONE] %package_type% package prepared
goto :eof

:generate_script_from_template
set template_file=%~1
set output_file=%~2
set package_type=%~3
set package_type_title=%~4

if "%package_type%"=="enduser" (
    set export_message=echo    - Export all modified data: double-click export-data.cmd
    set export_command=   - Export all modified data: double-click export-data.cmd
) else (
    set export_message=echo    - Export the modified resources ^(Shacl and Display Rules^): double-click export-resources.cmd
    set export_command=   - Export the modified resources ^(Shacl and Display Rules^): double-click export-resources.cmd
)

powershell -command "(Get-Content '%template_file%') -replace '{{PACKAGE_TYPE}}', '%package_type%' -replace '{{PACKAGE_TYPE_TITLE}}', '%package_type_title%' -replace '{{EXPORT_MESSAGE}}', '%export_message%' -replace '{{EXPORT_COMMAND}}', '%export_command%' | Set-Content '%output_file%'"
goto :eof