FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package.json vite.config.js ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Run development server (for local testing)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]