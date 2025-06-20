#!/bin/sh

# Check Streamlit health
if ! curl -fs http://localhost:80/_stcore/health; then
  echo "Streamlit health check failed"
  exit 1
fi

# Check OSRM service
if ! curl -fs http://osrm:5000/route/v1/driving/-0.085,51.516;-0.09,51.51?overview=false > /dev/null; then
  echo "OSRM service unavailable"
  exit 1
fi

# Check Postcodes service
if ! curl -fs http://postcodes-app:8000/postcodes/EC2A4JE > /dev/null; then
  echo "Postcodes service unavailable"
  exit 1
fi

exit 0
