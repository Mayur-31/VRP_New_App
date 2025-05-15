FROM idealpostcodes/postcodes.io:latest

# Switch to root user for package installation
USER root

# Install curl and postgresql-client
RUN apk add --no-cache curl postgresql-client

# Switch back to the default non-root user
USER node