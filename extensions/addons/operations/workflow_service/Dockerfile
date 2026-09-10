# Build context must be repository root
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app
ENV PYTHONPATH=/app

EXPOSE 9201

CMD ["uvicorn", "extensions.addons.operations.workflow_service.workflow_orchestrator_app:app", "--host", "0.0.0.0", "--port", "9201"]
