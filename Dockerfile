FROM python:3.11-slim

# Instalar git para sincronización de bóveda Obsidian
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar dependencias e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Comando por defecto
CMD ["python", "sync_obsidian.py", "python", "scheduler.py"]
