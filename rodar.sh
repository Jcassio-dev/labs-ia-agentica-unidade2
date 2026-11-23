#!/usr/bin/env bash
# Executa um notebook no lugar e grava o log em logs/. Uso: ./rodar.sh <pasta> <notebook>
cd "$(dirname "$0")/$1" || exit 1
nome=$(basename "$1")
echo "início $(date +%H:%M:%S)" > "../logs/$nome.log"
../.venv/bin/jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=1800 "$2" >> "../logs/$nome.log" 2>&1
echo "fim $(date +%H:%M:%S) código $?" >> "../logs/$nome.log"
