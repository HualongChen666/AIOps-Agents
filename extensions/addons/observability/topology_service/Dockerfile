# Build context must be repository root
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app
ENV PYTHONPATH=/app

EXPOSE 9101

CMD ["uvicorn", "extensions.addons.observability.topology_service.orchestrator:app", "--host", "0.0.0.0", "--port", "9101"]
