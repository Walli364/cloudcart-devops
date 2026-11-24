FROM python:3.12-slim

WORKDIR /app

# copy requirements.txt file first 
COPY app/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy application code
COPY app/backend/main.py .

# expose port and start uvicorn server
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]