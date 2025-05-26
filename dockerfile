# Use a slim Python base
FROM python:3.11-slim-bullseye

# Set working directory
WORKDIR /usr/src/app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your app code (including main.py)
COPY . .

# Let Cloud Run know what port to listen on
ARG PORT=8080
ENV PORT=$PORT
EXPOSE $PORT

# Launch Uvicorn pointing at your root-level main:app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
