#!/bin/bash

# HERITRACE User Testing Online Package Builder
# This script creates two standalone ZIP packages for user testing with pre-built online images

set -e

echo "🔨 Building HERITRACE Online Testing Packages"
echo "==============================================="

BUILD_DIR="online-build"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

echo "📁 Preparing build environment..."

create_scripts() {
    local package_dir=$1
    
    cat > "$package_dir/start.sh" << 'EOF'
#!/bin/bash

echo "🚀 Starting HERITRACE testing environment..."
docker compose up -d

echo "⏳ Waiting for services to be ready..."
echo "This may take a minute or two for the first run."

attempt=1
max_attempts=30
until docker ps | grep "heritrace-app" | grep -q "(healthy)" || [ $attempt -gt $max_attempts ]
do
    echo "Waiting for HERITRACE to be ready... ($attempt/$max_attempts)"
    sleep 10
    ((attempt++))
done

if [ $attempt -gt $max_attempts ]; then
    echo "❌ HERITRACE did not become healthy in the expected time."
    echo "Please check docker logs with: docker logs heritrace-app"
    exit 1
fi

echo "✅ HERITRACE is ready!"
echo "🌐 Open https://localhost:5000 in your browser"
echo "   (You may need to accept the self-signed certificate warning)"
EOF
    chmod +x "$package_dir/start.sh"
    
    cat > "$package_dir/stop.sh" << 'EOF'
#!/bin/bash

echo "🛑 Stopping HERITRACE testing environment..."
docker compose down

echo "✅ All services stopped"
EOF
    chmod +x "$package_dir/stop.sh"
    
    cat > "$package_dir/start.bat" << 'EOF'
@echo off
echo 🚀 Starting HERITRACE testing environment...
docker compose up -d

echo ⏳ Waiting for services to be ready...
echo This may take a minute or two for the first run.

set attempt=1
set max_attempts=30
:wait_loop
docker ps | findstr "heritrace-app" | findstr "(healthy)" > nul
if %errorlevel% equ 0 goto :healthy
if %attempt% gtr %max_attempts% goto :not_healthy
echo Waiting for HERITRACE to be ready... (%attempt%/%max_attempts%)
timeout /t 10 /nobreak > nul
set /a attempt+=1
goto :wait_loop

:not_healthy
echo ❌ HERITRACE did not become healthy in the expected time.
echo Please check docker logs with: docker logs heritrace-app
exit /b 1

:healthy
echo ✅ HERITRACE is ready!
echo 🌐 Open https://localhost:5000 in your browser
echo    (You may need to accept the self-signed certificate warning)
EOF
    
    cat > "$package_dir/stop.bat" << 'EOF'
@echo off
echo 🛑 Stopping HERITRACE testing environment...
docker compose down

echo ✅ All services stopped
EOF
}

echo "🎁 Building enduser online package..."
ENDUSER_DIR="$BUILD_DIR/heritrace-enduser-testing"
mkdir -p "$ENDUSER_DIR"

cp "common/templates/docker-compose-dockerhub-enduser.yml" "$ENDUSER_DIR/docker-compose.yml"

create_scripts "$ENDUSER_DIR"

cp "enduser/README.md" "$ENDUSER_DIR/README.md"

mkdir -p "$ENDUSER_DIR/dataset_database"
mkdir -p "$ENDUSER_DIR/prov_database"
cp "common/templates/virtuoso_dataset.ini" "$ENDUSER_DIR/dataset_database/virtuoso.ini"
cp "common/templates/virtuoso_provenance.ini" "$ENDUSER_DIR/prov_database/virtuoso.ini"

mkdir -p "$ENDUSER_DIR/resources"
cp "enduser/resources/display_rules.yaml" "$ENDUSER_DIR/resources/"
cp "enduser/resources/shacl.ttl" "$ENDUSER_DIR/resources/"

echo "🎁 Building technician online package..."
TECHNICIAN_DIR="$BUILD_DIR/heritrace-technician-testing"
mkdir -p "$TECHNICIAN_DIR"
mkdir -p "$TECHNICIAN_DIR/resources"

cp "common/templates/docker-compose-dockerhub-technician.yml" "$TECHNICIAN_DIR/docker-compose.yml"

create_scripts "$TECHNICIAN_DIR"

cp "technician/README.md" "$TECHNICIAN_DIR/README.md"

mkdir -p "$TECHNICIAN_DIR/dataset_database"
mkdir -p "$TECHNICIAN_DIR/prov_database"
cp "common/templates/virtuoso_dataset.ini" "$TECHNICIAN_DIR/dataset_database/virtuoso.ini"
cp "common/templates/virtuoso_provenance.ini" "$TECHNICIAN_DIR/prov_database/virtuoso.ini"

cp "technician/resources/display_rules.yaml" "$TECHNICIAN_DIR/resources/"
cp "technician/resources/shacl.ttl" "$TECHNICIAN_DIR/resources/"

echo "📦 Creating ZIP packages..."
cd "$BUILD_DIR"

echo "   Creating heritrace-enduser-testing.zip..."
zip -r heritrace-enduser-testing.zip heritrace-enduser-testing/ > /dev/null
mv heritrace-enduser-testing.zip ../

echo "   Creating heritrace-technician-testing.zip..."
zip -r heritrace-technician-testing.zip heritrace-technician-testing/ > /dev/null
mv heritrace-technician-testing.zip ../

cd ..

ENDUSER_SIZE=$(du -h heritrace-enduser-testing.zip | cut -f1)
TECHNICIAN_SIZE=$(du -h heritrace-technician-testing.zip | cut -f1)

echo ""
echo "🎉 Online Package build completed!"
echo "=================================="
echo "📦 Created packages:"
echo "   📚 heritrace-enduser-testing.zip ($ENDUSER_SIZE)"
echo "   🔧 heritrace-technician-testing.zip ($TECHNICIAN_SIZE)"
echo ""
echo "💡 Each package contains:"
echo "   - docker-compose.yml - Pre-configured Docker setup"
echo "   - start.sh / start.bat - One-click startup scripts"
echo "   - stop.sh / stop.bat - Clean shutdown scripts"
echo "   - README.md - Complete user instructions"

echo ""
echo "🧹 Cleaning up build directory..."
rm -rf "$BUILD_DIR"

echo "✅ Build complete!"
