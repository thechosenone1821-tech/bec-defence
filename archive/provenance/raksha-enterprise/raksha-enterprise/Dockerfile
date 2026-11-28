FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY raksha ./raksha
RUN pip install --no-cache-dir ".[api]"

ENV RAKSHA_DATA_DIR=/var/lib/raksha
RUN mkdir -p /var/lib/raksha
VOLUME ["/var/lib/raksha"]

EXPOSE 8000
CMD ["uvicorn", "raksha.bus.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
