FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x /app/docker/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["gunicorn", "cqcalling_site.wsgi:application", "--bind", "0.0.0.0:8000"]
