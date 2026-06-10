FROM python:3.11-slim

# Set timezone
ENV TZ=UTC

# Install system dependencies for OpenCV and other packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install CPU-only PyTorch and Torchvision directly from PyTorch CPU index
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Copy requirements and install the rest of the dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all repository contents
COPY . .

# Expose the default port for Hugging Face Spaces
EXPOSE 7860

# Run Flask server using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "app:app"]
