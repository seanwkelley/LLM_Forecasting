#!/bin/bash
# Cleanup script - run AFTER simulation completes
# Moves old "output" directory to archive

cd "D:\Northeastern\LLM_Forecasting"

if [ -d "output" ]; then
  echo "Archiving old 'output' directory..."
  mv output archive/output_OLD_interactions_deprecated
  echo "✓ Done! Old 'output' directory archived."
else
  echo "No 'output' directory found - already cleaned up."
fi

echo ""
echo "Current structure:"
ls -d outputs* 2>/dev/null
