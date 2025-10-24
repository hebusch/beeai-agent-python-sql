FROM python:3.13-slim-trixie
COPY --from=ghcr.io/astral-sh/uv:0.7.15 /uv /bin/

ENV UV_LINK_MODE=copy \
    PRODUCTION_MODE=true

WORKDIR /app

# Copiar solo archivos de dependencias primero (para cachear la instalación)
COPY pyproject.toml uv.lock ./

# Instalar dependencias (esta capa se cachea si no cambian pyproject.toml o uv.lock)
RUN uv sync --no-cache --locked --link-mode copy

# Ahora copiar el resto del código (cambios aquí no invalidan el caché de dependencias)
COPY . .

ENV PRODUCTION_MODE=True \
    PATH="/app/.venv/bin:$PATH" \
    HOME=/tmp

CMD ["uv", "run", "--no-sync", "server"]
