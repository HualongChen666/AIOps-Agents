FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/scenario_memory_service /app/services/scenario_memory_service

EXPOSE 9408

CMD ["uvicorn", "services.scenario_memory_service.main_app:app", "--host", "0.0.0.0", "--port", "9408"]
