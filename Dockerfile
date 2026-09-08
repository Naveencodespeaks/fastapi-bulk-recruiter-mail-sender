#==============================
# stage 1: Build
#=============================



FROM python:3.12-slim AS build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt




#===========================================
# stage 2: Runtime
# ==========================================

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app


# copy installed python packages from build stage

COPY --from=build /install /usr/local


# copy application code


COPY app ./app


# Expose FastAPI port

EXPOSE 8000


# START FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
