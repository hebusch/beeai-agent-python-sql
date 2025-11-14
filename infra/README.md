# Despliegue del Agente AIOps Analytics en Kubernetes

Este documento describe cómo desplegar el agente de análisis AIOps en un cluster de Kubernetes (k3s).

## Pre-requisitos

- Cluster de Kubernetes (k3s) funcionando
- BeeAI Platform desplegada en el cluster
- Code Interpreter desplegado en el cluster
- Docker instalado para construir la imagen del agente
- Credenciales de DB2 de AIOps

## Orden de Despliegue

### 1. Code Interpreter

Primero despliega el Code Interpreter que el agente usará para ejecutar código Python:

```bash
kubectl apply -f 02-code-interpreter.yaml
```

Verifica que esté funcionando:

```bash
kubectl get pods | grep code-interpreter
kubectl logs -f code-interpreter
```

### 2. Credenciales de DB2

Edita `04-db2-secret.yaml` y actualiza las credenciales de DB2 según tu configuración:

```bash
# Codificar valores en base64
echo -n "tu-hostname" | base64
echo -n "50000" | base64
echo -n "AIOPS" | base64
echo -n "db2inst1" | base64
echo -n "db2inst1" | base64
```

Luego aplica el secret:

```bash
kubectl apply -f 04-db2-secret.yaml
```

### 3. Construir y Cargar la Imagen del Agente

Desde el directorio raíz del proyecto:

```bash
# Construir la imagen
docker build -t beeai-agent:latest .

# Cargar la imagen en k3s (sin usar registry)
docker save beeai-agent:latest | sudo k3s ctr images import -

# Verificar que la imagen esté cargada
sudo k3s ctr images ls | grep beeai-agent
```

### 4. Desplegar el Agente

```bash
kubectl apply -f 03-agent-deployment.yaml
```

Verifica el despliegue:

```bash
# Ver los pods
kubectl get pods | grep beeai-agent

# Ver logs del agente
kubectl logs -f $(kubectl get pod -l app=beeai-agent -o name)

# Ver el servicio
kubectl get svc beeai-agent-service
```

## Configuración de Credenciales

El agente soporta **dos formas** de proveer credenciales de DB2:

### Opción 1: Kubernetes Secrets (Pre-configurado)

Las credenciales se definen en `04-db2-secret.yaml` y se inyectan como variables de entorno en el pod. Esto es útil para entornos donde las credenciales son fijas.

**Ventajas:**
- Las credenciales están disponibles inmediatamente al iniciar el agente
- No requiere interacción del usuario
- Ideal para entornos de desarrollo/staging

**Desventajas:**
- Las credenciales están fijas en el deployment
- Requiere redeployar el agente para cambiar credenciales

### Opción 2: Secrets Extension (Usuario provee en runtime)

El agente puede solicitar al usuario que provea las credenciales a través de la UI de BeeAI Platform. Las credenciales se almacenan de forma segura en la plataforma y se reutilizan en ejecuciones posteriores.

**Ventajas:**
- El usuario puede proveer sus propias credenciales
- Las credenciales se pueden actualizar/revocar desde la UI
- No requiere acceso al cluster de Kubernetes
- Ideal para entornos multi-tenant

**Desventajas:**
- Requiere que el usuario provea las credenciales en el primer uso

**Para usar solo Secrets Extension (sin Kubernetes Secrets):**

Comenta las variables de entorno `DB2_*` en `03-agent-deployment.yaml`:

```yaml
# - name: DB2_HOST
#   valueFrom:
#     secretKeyRef:
#       name: db2-credentials
#       key: host
# ... etc
```

El agente automáticamente solicitará las credenciales al usuario cuando intente conectarse a DB2.

## Verificación

### 1. Verificar que el agente se registró en BeeAI Platform

```bash
# Ver logs del agente
kubectl logs $(kubectl get pod -l app=beeai-agent -o name) | grep -i "register"
```

Deberías ver algo como:
```
Agent registered successfully: http://beeai-agent-service:8000
```

### 2. Verificar en la UI de BeeAI Platform

1. Abre https://beeai.hebusch.com
2. Ve a la sección de "Agents"
3. Deberías ver "AIOps Analytics Agent" listado

### 3. Probar el agente

1. Crea un nuevo chat con el agente
2. Prueba una consulta simple: "Muéstrame las tablas disponibles en la base de datos"
3. El agente debería:
   - Conectarse a DB2
   - Ejecutar una query (e.g., `SELECT TABNAME FROM SYSCAT.TABLES FETCH FIRST 10 ROWS ONLY`)
   - Mostrar los resultados

## Actualización del Agente

Para actualizar el agente después de cambios en el código:

```bash
# 1. Reconstruir la imagen
docker build -t beeai-agent:latest .

# 2. Recargar en k3s
docker save beeai-agent:latest | sudo k3s ctr images import -

# 3. Forzar recreación del pod (eliminar el pod existente)
kubectl delete pod -l app=beeai-agent

# 4. Verificar que el nuevo pod esté corriendo
kubectl get pods -l app=beeai-agent
kubectl logs -f $(kubectl get pod -l app=beeai-agent -o name)
```

## Troubleshooting

### El agente no se conecta a DB2

**Síntoma:** Error "DB2 credentials not configured" o "Failed to connect to DB2"

**Soluciones:**

1. Verificar que el secret de DB2 existe:
   ```bash
   kubectl get secret db2-credentials
   kubectl describe secret db2-credentials
   ```

2. Verificar que las variables de entorno están correctas en el pod:
   ```bash
   kubectl exec $(kubectl get pod -l app=beeai-agent -o name) -- env | grep DB2
   ```

3. Verificar conectividad de red al servidor DB2:
   ```bash
   kubectl exec $(kubectl get pod -l app=beeai-agent -o name) -- ping -c 3 <DB2_HOST>
   kubectl exec $(kubectl get pod -l app=beeai-agent -o name) -- nc -zv <DB2_HOST> 50000
   ```

### Error "ModuleNotFoundError: No module named 'ibm_db'"

**Síntoma:** El agente falla al importar `ibm_db`

**Solución:** El paquete `ibm_db` requiere los drivers de DB2. Necesitas instalarlos en el Dockerfile:

```dockerfile
# Agregar al Dockerfile antes de `uv sync`
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Descargar e instalar IBM DB2 CLI drivers
RUN wget https://public.dhe.ibm.com/ibmdl/export/pub/software/data/db2/drivers/odbc_cli/linuxx64_odbc_cli.tar.gz \
    && tar -xzf linuxx64_odbc_cli.tar.gz -C /opt \
    && rm linuxx64_odbc_cli.tar.gz

ENV IBM_DB_HOME=/opt/clidriver
ENV LD_LIBRARY_PATH=/opt/clidriver/lib:$LD_LIBRARY_PATH
```

### El agente no se auto-registra en BeeAI Platform

**Síntoma:** El agente no aparece en la UI de BeeAI Platform

**Soluciones:**

1. Verificar que `PRODUCTION_MODE=false`:
   ```bash
   kubectl exec $(kubectl get pod -l app=beeai-agent -o name) -- env | grep PRODUCTION_MODE
   ```

2. Verificar logs del agente:
   ```bash
   kubectl logs $(kubectl get pod -l app=beeai-agent -o name) | grep -i register
   ```

3. Verificar conectividad a BeeAI Platform:
   ```bash
   kubectl exec $(kubectl get pod -l app=beeai-agent -o name) -- curl -v http://beeai-platform-svc:8333/healthcheck
   ```

### El code interpreter no encuentra archivos

**Síntoma:** Python genera archivos pero no se muestran en el chat

**Soluciones:**

1. Verificar que el volumen compartido está montado correctamente:
   ```bash
   # En el agente
   kubectl exec $(kubectl get pod -l app=beeai-agent -o name) -- ls -la /app/tmp
   
   # En el code interpreter
   kubectl exec code-interpreter -- ls -la /storage
   
   # En el host
   sudo ls -la /var/lib/beeai/storage
   ```

2. Verificar que los 3 directorios tienen el mismo contenido

3. Verificar permisos:
   ```bash
   sudo chmod 777 /var/lib/beeai/storage
   ```

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                      BeeAI Platform UI                       │
│                   (https://beeai.hebusch.com)                │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      BeeAI Platform API                      │
│                  (beeai-platform-svc:8333)                   │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    AIOps Analytics Agent                     │
│                   (beeai-agent-service:8000)                 │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │   DB2Tool    │  │  PythonTool  │  │  Secrets Mgmt   │   │
│  └──────┬───────┘  └──────┬───────┘  └─────────────────┘   │
└─────────┼──────────────────┼──────────────────────────────┘
          │                  │
          ↓                  ↓
┌──────────────────┐  ┌────────────────────────────────────┐
│   DB2 Database   │  │      Code Interpreter              │
│     (AIOps)      │  │ (code-interpreter-service:50081)   │
└──────────────────┘  └────────────────────────────────────┘
                               │
                               ↓
                      ┌─────────────────────┐
                      │  Shared Storage     │
                      │ /var/lib/beeai/     │
                      │      storage        │
                      └─────────────────────┘
```

## Referencias

- [BeeAI SDK - Secrets Extension](https://ibm.github.io/bee-agent-stack-sdk/beeai-sdk/docs/extensions/secrets/)
- [BeeAI Platform Documentation](https://ibm.github.io/bee-agent-stack-sdk/)
- [IBM DB2 Python Driver](https://github.com/ibmdb/python-ibmdb)

