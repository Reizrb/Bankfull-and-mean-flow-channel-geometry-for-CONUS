# Container for the Channel Geometry Data API.
# The data files are NOT copied in: the API reads them from Hugging Face
# (or from the address in the CG_DATA_URL setting).
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && python -c "import duckdb; duckdb.sql('INSTALL httpfs')"

COPY app.py .

ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT}"]
