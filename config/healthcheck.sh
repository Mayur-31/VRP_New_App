#!/bin/sh

# Streamlit health check
if ! curl -fs http://localhost:80/_stcore/health; then
  echo "Streamlit health check failed"
  exit 1
fi

# OSRM health check (simpler)
if ! curl -fs http://osrm:5000 > /dev/null; then
  echo "OSRM service unavailable"
  exit 1
fi

# Postcodes health check (simpler)
if ! curl -fs http://postcodes-app:8000 > /dev/null; then
  echo "Postcodes service unavailable"
  exit 1
fi

exit 0
