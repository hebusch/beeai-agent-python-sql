FROM python:3.13-slim-trixie
COPY --from=ghcr.io/astral-sh/uv:0.7.15 /uv /bin/

ENV UV_LINK_MODE=copy \
    PRODUCTION_MODE=true

# Copiar todo el código
ADD . /app
WORKDIR /app

# Instalar todas las dependencias
# Nota: Usa 'docker build --no-cache' si quieres un build completamente limpio
RUN uv sync --locked --link-mode copy

ENV PRODUCTION_MODE=True \
    PATH="/app/.venv/bin:$PATH" \
    HOME=/tmp

CMD ["uv", "run", "--no-sync", "server"]
