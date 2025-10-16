# ✅ Base Image
FROM python:3.10.8-slim

# ✅ Install Dependencies
RUN apt-get update -y && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
       gcc libffi-dev musl-dev ffmpeg aria2 python3-pip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ✅ Copy Project Files
COPY . /app/
WORKDIR /app/

# ✅ Install Python Dependencies
RUN pip3 install --no-cache-dir --upgrade -r requirements.txt

# ✅ Run Gunicorn and Python app
CMD gunicorn app:app & python3 main.py
