#!/bin/bash
# Wrapper que executa setup_config.py (Python)
# Garante que está no diretório correto
cd "$(dirname "$0")"
python3 setup_config.py