#!/bin/sh
# Check if Streamlit health endpoint is responsive
curl -f http://localhost:8501/_stcore/health || exit 1
