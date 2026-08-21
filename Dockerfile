FROM python:3.12-slim-bookworm

ARG STUDENT_UID=1000
ARG STUDENT_GID=1000

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/workspace

RUN groupadd --gid "${STUDENT_GID}" student \
    && useradd --uid "${STUDENT_UID}" --gid "${STUDENT_GID}" --create-home --shell /bin/bash student

WORKDIR /workspace

COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install --requirement /tmp/requirements.txt \
    && rm /tmp/requirements.txt

RUN mkdir -p /workspace/data/input \
             /workspace/data/working \
             /workspace/notebooks \
             /workspace/results \
             /workspace/src \
             /workspace/scripts \
    && chown -R student:student /workspace

USER student

EXPOSE 8888
