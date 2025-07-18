#!/bin/sh
# Check only Streamlit health
curl -fs http://localhost:8501/_stcore/health || exit 1
