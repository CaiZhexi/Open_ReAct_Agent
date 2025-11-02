#!/bin/bash
cd /Users/caizhexi/Desktop/个人项目/Agentic-RAG
source venv/bin/activate
python -u app.py 2>&1 | tee logs/app_debug.log

