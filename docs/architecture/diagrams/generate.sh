#!/bin/bash

# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

cd "$(dirname "$0")"

echo "Generating PlantUML diagrams..."
plantuml -tpng -Sscale=2 -o output *.puml

echo ""
echo "Generated diagrams:"
ls -lh output/*.png

echo ""
echo "Total PNG files: $(ls -1 output/*.png 2>/dev/null | wc -l)"
