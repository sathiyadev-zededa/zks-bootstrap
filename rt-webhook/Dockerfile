# ─────────────────────────────────────────────────────────────
#  RT Mutating Admission Webhook — aarch64 (Moxa SPMCPL02S013)
#  ZEDEDA / Saudi Aramco Edge Demo
# ─────────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY main.py .

# Certs are mounted at runtime via k8s Secret — never baked into image
# Mount point: /certs/tls.crt and /certs/tls.key

EXPOSE 8443

CMD ["python", "main.py"]
