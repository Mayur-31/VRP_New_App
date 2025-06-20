#!/bin/sh
# Check if Streamlit health endpoint is responsive on port 80
curl -f http://localhost:80/_stcore/health || exit 1
