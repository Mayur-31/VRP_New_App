# Use ARM64 compatible base image
FROM node:18-alpine

# Install dependencies with build tools
RUN apk add --no-cache curl postgresql-client python3 make g++ git

# Clone Postcodes.io
RUN git clone --depth 1 https://github.com/ideal-postcodes/postcodes.io.git /app

WORKDIR /app

# Install specific CommonJS-compatible version of escape-string-regexp
RUN npm install escape-string-regexp@4.0.0

# Find and patch the configuration file BEFORE build
RUN find . -name index.js -exec grep -l "stub: process.env.STUB === 'true'" {} + | \
    while read file; do \
        sed -i "s|stub: process.env.STUB === 'true'|stub: true|g" "$file"; \
        echo "Patched stub mode in: $file"; \
    done

# Install dependencies and build the project
RUN npm install --legacy-peer-deps
RUN npm run build

# Expose port
EXPOSE 8000

# Startup command
CMD ["npm", "start"]
