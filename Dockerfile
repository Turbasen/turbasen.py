FROM python:3-alpine

RUN mkdir -p /app
WORKDIR /app
ENV PYTHONUNBUFFERED 1
RUN apk --update add make && rm -rf /var/cache/apk/*
COPY setup.py /app/
COPY turbasen /app/turbasen/
RUN pip install -e .[dev]
