FROM python:3.5

RUN mkdir -p /app
WORKDIR /app
COPY setup.py /app/
COPY turbasen /app/turbasen/
RUN pip install -e .[dev]
