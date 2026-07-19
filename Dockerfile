FROM python:3.13-slim AS builder

WORKDIR /build
COPY pyproject.toml README.md LICENSE ./
COPY archagent_audit ./archagent_audit
RUN python -m pip install --no-cache-dir --upgrade "pip>=26.1.2" \
    && python -m pip wheel --no-cache-dir --wheel-dir /wheels .

FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TMPDIR=/tmp \
    PORT=8080

RUN groupadd --system archagent \
    && useradd --system --gid archagent --create-home archagent \
    && chmod 1777 /tmp
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir --upgrade "pip>=26.1.2" \
    && python -m pip install --no-cache-dir /wheels/archagent_audit-*.whl \
    && rm -rf /wheels \
    && mkdir /app \
    && chmod 0555 /app

USER archagent
WORKDIR /app
EXPOSE 8080
CMD ["archagent-audit", "serve", "--transport", "streamable-http", "--mode", "hosted"]
