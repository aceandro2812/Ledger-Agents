FROM node:20-alpine

WORKDIR /app

# Copy package descriptors and install packages
COPY package*.json ./
RUN npm install

# Copy frontend source code
COPY . .

# Set dev server environment variables
ENV VITE_API_URL=http://localhost:8000

# Expose Vite dev port
EXPOSE 5173

# Run Vite dev server on port 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
