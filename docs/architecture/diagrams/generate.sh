#!/bin/bash

cd "$(dirname "$0")"

echo "Generating PlantUML diagrams..."
plantuml -tpng -Sscale=2 -o output *.puml

echo ""
echo "Generated diagrams:"
ls -lh output/*.png

echo ""
echo "Total PNG files: $(ls -1 output/*.png 2>/dev/null | wc -l)"
