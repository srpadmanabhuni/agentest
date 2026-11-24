# One-command try-it for agentest: build locally, no registry image is published.
#   docker build -t agentest .
#   docker run --rm agentest                                   # reproduces the README demo (a22, T1-018 fails)
#   docker run --rm -v "$PWD/traces:/traces" agentest std run --otlp /traces/my_trace.otlp.json --format md
# Offline at run time: no network, API key or model is used to judge.
FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir . && useradd --create-home agentest
USER agentest
ENTRYPOINT ["agentest"]
CMD ["std", "run", "--agent", "a22", "--ids", "T1-018", "--format", "md"]
