FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/knowledge_graph_service /app/services/knowledge_graph_service

EXPOSE 9409

CMD ["uvicorn", "services.knowledge_graph_service.main_app:app", "--host", "0.0.0.0", "--port", "9409"]
