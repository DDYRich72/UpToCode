FROM python:3.13-slim AS builder

WORKDIR /build
COPY pyproject.toml README.md LICENSE ./
COPY uptocode ./uptocode
RUN python -m pip install --no-cache-dir --upgrade "pip>=26.1.2" \
    && python -m pip wheel --no-cache-dir --wheel-dir /wheels .

FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TMPDIR=/tmp \
    PORT=8080

RUN groupadd --system uptocode \
    && useradd --system --gid uptocode --create-home uptocode \
    && chmod 1777 /tmp
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir --upgrade "pip>=26.1.2" \
    && python -m pip install --no-cache-dir /wheels/uptocode-*.whl \
    && rm -rf /wheels \
    && mkdir /app \
    && chmod 0555 /app

USER uptocode
WORKDIR /app
EXPOSE 8080
CMD ["uptocode", "serve", "--transport", "streamable-http", "--mode", "hosted"]
