FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /workspace

RUN useradd --create-home --shell /usr/sbin/nologin sandbox
USER sandbox

CMD ["python", "-c", "print('runner image ready')"]
