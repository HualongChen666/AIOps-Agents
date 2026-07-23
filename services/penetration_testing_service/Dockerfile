# Build context must be repository root
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

EXPOSE 9564

CMD ["uvicorn", "services.penetration_testing_service.main_app:app", "--host", "0.0.0.0", "--port", "9564"]
