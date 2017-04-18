FROM python:3

RUN mkdir -p /app
WORKDIR /app
ENV PYTHONUNBUFFERED 1
COPY setup.py /app/
COPY turbasen /app/turbasen/
RUN pip install -e .[dev]
