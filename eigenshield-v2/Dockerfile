FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8080
CMD ["python", "-m", "bus.event_server", "--policy", "config/policy.yaml", "--topology", "config/company_topology.json", "--model", "qwen3.5:4b", "--host", "0.0.0.0", "--port", "8080"]
