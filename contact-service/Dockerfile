FROM python:3.13-alpine
COPY app.py /app.py
ENV PYTHONUNBUFFERED=1
USER nobody
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:8080/ || exit 1
CMD ["python", "/app.py"]
