# Optional disposable-test image. Not a production deployment declaration.
# No container runtime is available on the current audit host; build/run unverified.
FROM python:3.12.14-slim AS builder
WORKDIR /build
COPY pyproject.toml ./
COPY src ./src
RUN python -m pip wheel --no-cache-dir --no-deps --wheel-dir /wheels .

FROM python:3.12.14-slim
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir /wheels/*.whl "psycopg[binary]" "httpx" \
    && useradd --uid 10001 --create-home commerce
COPY adversarial/runtime.py ./runtime.py
ENV COMMERCE_TEST_CONFIG=/run/commerce/config.json
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=3)"
CMD ["python", "-m", "uvicorn", "runtime:application", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
