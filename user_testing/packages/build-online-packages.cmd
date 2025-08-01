@echo off
setlocal enabledelayedexpansion

REM HERITRACE User Testing Online Package Builder
REM This script creates two standalone ZIP packages for user testing with pre-built online images

echo [BUILD] Building HERITRACE Online Testing Packages
echo ===============================================

set BUILD_DIR=online-build
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
mkdir "%BUILD_DIR%"

echo [FILES] Preparing build environment...

echo [PKG] Building enduser online package...
set ENDUSER_DIR=%BUILD_DIR%\heritrace-enduser-testing
mkdir "%ENDUSER_DIR%"

copy "common\templates\docker-compose-dockerhub-enduser.yml" "%ENDUSER_DIR%\docker-compose.yml"

call :generate_script_from_template "common\templates\scripts\start.cmd.template" "%ENDUSER_DIR%\start.cmd" "enduser" "End User"
call :generate_script_from_template "common\templates\scripts\stop.cmd.template" "%ENDUSER_DIR%\stop.cmd" "enduser" "End User"
call :generate_script_from_template "common\templates\scripts\start.sh.template" "%ENDUSER_DIR%\start.sh" "enduser" "End User"
call :generate_script_from_template "common\templates\scripts\stop.sh.template" "%ENDUSER_DIR%\stop.sh" "enduser" "End User"

copy "enduser\README.md" "%ENDUSER_DIR%\README.md"
copy "..\sus_questionnaire.md" "%ENDUSER_DIR%\sus_questionnaire.md"
copy "..\written_responses_end_users.md" "%ENDUSER_DIR%\written_responses.md"
copy "..\user_testing_privacy_consent_form.pdf" "%ENDUSER_DIR%\user_testing_privacy_consent_form.pdf"

mkdir "%ENDUSER_DIR%\config"
copy "enduser\config\display_rules.yaml" "%ENDUSER_DIR%\config\"
copy "enduser\config\shacl.ttl" "%ENDUSER_DIR%\config\"

mkdir "%ENDUSER_DIR%\dataset_database"
mkdir "%ENDUSER_DIR%\prov_database"
copy "common\templates\virtuoso_dataset.ini" "%ENDUSER_DIR%\dataset_database\virtuoso.ini"
copy "common\templates\virtuoso_provenance.ini" "%ENDUSER_DIR%\prov_database\virtuoso.ini"

copy "common\scripts\export-data.sh" "%ENDUSER_DIR%\"
copy "common\scripts\export-data.cmd" "%ENDUSER_DIR%\"

echo [PKG] Building technician online package...
set TECHNICIAN_DIR=%BUILD_DIR%\heritrace-technician-testing
mkdir "%TECHNICIAN_DIR%"
mkdir "%TECHNICIAN_DIR%\config"

copy "common\templates\docker-compose-dockerhub-technician.yml" "%TECHNICIAN_DIR%\docker-compose.yml"

call :generate_script_from_template "common\templates\scripts\start.cmd.template" "%TECHNICIAN_DIR%\start.cmd" "technician" "Configurator"
call :generate_script_from_template "common\templates\scripts\stop.cmd.template" "%TECHNICIAN_DIR%\stop.cmd" "technician" "Configurator"
call :generate_script_from_template "common\templates\scripts\start.sh.template" "%TECHNICIAN_DIR%\start.sh" "technician" "Configurator"
call :generate_script_from_template "common\templates\scripts\stop.sh.template" "%TECHNICIAN_DIR%\stop.sh" "technician" "Configurator"

copy "technician\README.md" "%TECHNICIAN_DIR%\README.md"
copy "..\sus_questionnaire.md" "%TECHNICIAN_DIR%\sus_questionnaire.md"
copy "..\written_responses_technicians.md" "%TECHNICIAN_DIR%\written_responses.md"
copy "..\user_testing_privacy_consent_form.pdf" "%TECHNICIAN_DIR%\user_testing_privacy_consent_form.pdf"

mkdir "%TECHNICIAN_DIR%\dataset_database"
mkdir "%TECHNICIAN_DIR%\prov_database"
copy "common\templates\virtuoso_dataset.ini" "%TECHNICIAN_DIR%\dataset_database\virtuoso.ini"
copy "common\templates\virtuoso_provenance.ini" "%TECHNICIAN_DIR%\prov_database\virtuoso.ini"

copy "technician\config\display_rules.yaml" "%TECHNICIAN_DIR%\config\"
copy "technician\config\shacl.ttl" "%TECHNICIAN_DIR%\config\"

copy "common\scripts\export-resources.sh" "%TECHNICIAN_DIR%\"
copy "common\scripts\export-resources.cmd" "%TECHNICIAN_DIR%\"

echo [ZIP] Creating ZIP packages...
cd "%BUILD_DIR%"

echo    Creating heritrace-enduser-testing.zip...
powershell -command "Compress-Archive -Path 'heritrace-enduser-testing' -DestinationPath '..\heritrace-enduser-testing.zip' -Force"

echo    Creating heritrace-technician-testing.zip...
powershell -command "Compress-Archive -Path 'heritrace-technician-testing' -DestinationPath '..\heritrace-technician-testing.zip' -Force"

cd ..

call :print_summary

echo [CLEAN] Cleaning up build directory...
rmdir /s /q "%BUILD_DIR%"

echo [DONE] Build complete!
pause
exit /b 0

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

if exist "%template_file%" (
    powershell -command "(Get-Content '%template_file%') -replace '{{PACKAGE_TYPE}}', '%package_type%' -replace '{{PACKAGE_TYPE_TITLE}}', '%package_type_title%' -replace '{{EXPORT_MESSAGE}}', '%export_message%' -replace '{{EXPORT_COMMAND}}', '%export_command%' | Set-Content '%output_file%'"
) else (
    echo    Template file not found: %template_file%
)
exit /b 0

:print_summary
for %%A in (heritrace-enduser-testing.zip) do set ENDUSER_SIZE=%%~zA
for %%A in (heritrace-technician-testing.zip) do set TECHNICIAN_SIZE=%%~zA

set /a ENDUSER_SIZE_KB=%ENDUSER_SIZE%/1024
set /a TECHNICIAN_SIZE_KB=%TECHNICIAN_SIZE%/1024

echo.
echo [SUCCESS] Online Package build completed!
echo ==================================
echo [PKG] Created packages:
echo    [USER] heritrace-enduser-testing.zip (%ENDUSER_SIZE_KB% KB)
echo    [TECH] heritrace-technician-testing.zip (%TECHNICIAN_SIZE_KB% KB)
echo.
echo [INFO] Each package contains:
echo    - docker-compose.yml - Pre-configured Docker setup
echo    - start.cmd - One-click startup script (double-click to run)
echo    - stop.cmd - Clean shutdown script (double-click to run)
echo    - README.md - Complete user instructions
echo    - sus_questionnaire.md - SUS usability questionnaire
echo    - written_responses.md - Written reflection questions
echo    - user_testing_privacy_consent_form.pdf - Privacy consent form

if exist "heritrace-enduser-testing.zip" (
    echo    - export-data.cmd - Script to export all data (double-click to run)
)
if exist "heritrace-technician-testing.zip" (
    echo    - export-resources.cmd - Script to export SHACL and display rules (double-click to run)
)
exit /b 0