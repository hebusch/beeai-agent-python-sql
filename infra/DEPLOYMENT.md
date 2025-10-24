# Deployment en Kubernetes con BeeAI Platform

Esta guía documenta cómo desplegar el agente custom usando BeeAI Platform Helm chart.

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                       │
│                                                             │
│  ┌──────────────────┐      ┌──────────────────────────┐   │
│  │  BeeAI Platform  │◄─────┤  Agent (via Docker)      │   │
│  │  (Helm Chart)    │      │  - Gestión: Helm         │   │
│  └──────────────────┘      │  - Runtime: Docker       │   │
│                            └───────────┬──────────────┘   │
│                                        │                   │
│                            ┌───────────▼──────────────┐   │
│                            │  Code Interpreter (Pod)  │   │
│                            └───────────┬──────────────┘   │
│                                        │                   │
│                            ┌───────────▼──────────────┐   │
│                            │  /var/lib/beeai/storage  │   │
│                            │  (hostPath - compartido) │   │
│                            └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 📋 Pre-requisitos

1. ✅ BeeAI Platform ya instalado via Helm
2. ✅ Imagen Docker del agente: `beeai-agent:latest` 
3. ✅ Code interpreter corriendo en el cluster
4. ✅ Secret de WatsonX creado

## 🚀 Deployment

### Paso 1: Eliminar PVC anterior (si existe)

```bash
kubectl delete pvc code-interpreter-storage --ignore-not-found
```

### Paso 2: Re-desplegar code-interpreter con hostPath

```bash
# Eliminar el anterior
kubectl delete -f infra/02-code-interpreter.yaml --ignore-not-found

# Aplicar la versión actualizada
kubectl apply -f infra/02-code-interpreter.yaml

# Verificar que está corriendo
kubectl get pods | grep code-interpreter
```

### Paso 3: Verificar que el secret de WatsonX existe

```bash
kubectl get secret watsonx-credentials
```

Si no existe, créalo:

```bash
kubectl create secret generic watsonx-credentials \
  --from-literal=project-id='TU_PROJECT_ID' \
  --from-literal=api-key='TU_API_KEY'
```

### Paso 4: Actualizar BeeAI Platform con tu agente

```bash
# Desde el directorio del proyecto
helm upgrade beeai -f infra/06-beeai-platform-config.yaml \
  oci://ghcr.io/i-am-bee/beeai-platform/beeai-platform-chart/beeai-platform:0.3.7
```

### Paso 5: Verificar el deployment

```bash
# Ver todos los pods
kubectl get pods

# Ver logs de BeeAI Platform
kubectl logs deployment/beeai-platform | tail -50

# Verificar que tu agente está registrado
kubectl get pods | grep beeai-provider
```

## 🔍 Verificación

### 1. Ver el storage compartido

```bash
# Desde el code-interpreter
kubectl exec -it code-interpreter -- ls -la /storage

# Desde el nodo (VM)
sudo ls -la /var/lib/beeai/storage
```

### 2. Probar conectividad

```bash
# Desde el agente al code-interpreter
kubectl exec -it deployment/beeai-provider-XXXXX -- curl -s http://code-interpreter-service:50081/
```

### 3. Verificar en la UI

Accede a https://beeai.hebusch.com y verifica que tu agente custom aparece en la lista.

## 🐛 Troubleshooting

### El agente no aparece en la plataforma

```bash
# Ver logs de BeeAI Platform
kubectl logs deployment/beeai-platform | grep -i provider

# Ver si el pod del agente se creó
kubectl get pods -A | grep provider
```

### Problemas con el storage

```bash
# Verificar permisos en el nodo
sudo ls -la /var/lib/beeai/storage

# Dar permisos si es necesario
sudo chmod 777 /var/lib/beeai/storage
```

### El agente no puede acceder al code-interpreter

```bash
# Verificar que el servicio existe
kubectl get svc code-interpreter-service

# Verificar DNS interno
kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup code-interpreter-service
```

## 📝 Notas Importantes

- **Storage compartido**: Usa `hostPath` en `/var/lib/beeai/storage` para compartir archivos entre el code-interpreter (pod de K8s) y el agente (contenedor Docker gestionado por Helm).

- **Credenciales**: Las credenciales de WatsonX están en el Secret `watsonx-credentials` y se montan como variables de entorno en el agente.

- **Code interpreter**: Debe estar corriendo antes de desplegar el agente, ya que el agente lo referencia.

- **Imagen local**: La imagen `beeai-agent:latest` se usa localmente con `imagePullPolicy: IfNotPresent` para evitar pulls innecesarios.

## 🔄 Actualizar el agente

Cuando hagas cambios en el código:

```bash
# Re-buildear la imagen
docker build -t beeai-agent:latest .

# Re-importar a k3s
docker save beeai-agent:latest | sudo k3s ctr images import -

# Reiniciar el pod del agente (Helm lo recreará)
kubectl delete pod -l app=beeai-provider-XXXXX
```

O simplemente:

```bash
helm upgrade beeai -f infra/06-beeai-platform-config.yaml \
  oci://ghcr.io/i-am-bee/beeai-platform/beeai-platform-chart/beeai-platform:0.3.7 \
  --force
```

## ✅ Checklist de verificación

- [ ] Code interpreter corriendo
- [ ] Secret de WatsonX creado
- [ ] Imagen del agente en k3s
- [ ] BeeAI Platform actualizado con Helm
- [ ] Storage compartido accesible
- [ ] Agente visible en la UI de BeeAI
- [ ] Prueba exitosa ejecutando el agente

