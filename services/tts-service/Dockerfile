FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    ffmpeg \
    libsndfile1 \
    espeak-ng \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create symbolic link for python
RUN ln -s /usr/bin/python3.11 /usr/bin/python

# Upgrade pip
RUN python -m pip install --upgrade pip

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download default TTS models (optional - can be done at runtime)
# RUN python -c "from TTS.api import TTS; TTS('tts_models/en/ljspeech/tacotron2-DDC')"

# Copy application code
COPY . .

# Create models directory
RUN mkdir -p /models/tts

# Expose port
EXPOSE 8007

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8007"]
