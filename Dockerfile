FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Copy application code and dependencies
COPY . .

# Copy SSL certificates into the container
COPY ./fullchain.pem /etc/ssl/certs/fullchain.pem
COPY ./privkey.pem /etc/ssl/private/privkey.pem

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port
EXPOSE 443

# Set environment variables
ENV PORT=443

# Command to run the FastAPI application with SSL
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "443", "--ssl-certfile", "/etc/ssl/certs/fullchain.pem", "--ssl-keyfile", "/etc/ssl/private/privkey.pem"]
