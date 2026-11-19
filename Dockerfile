FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 SUPPLIERHUB_DB=/state/supplierhub.sqlite
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && mkdir /state \
    && chown 10001:10001 /state
COPY supplierhub ./supplierhub
USER 10001:10001
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "supplierhub.app:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
