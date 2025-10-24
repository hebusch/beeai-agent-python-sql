# Tools

Este directorio contiene las herramientas personalizadas (tools) para los agentes de BeeAI.

## Herramientas Disponibles

### 1. FixedPythonTool (`python_tool.py`)

Herramienta para ejecutar código Python en un entorno sandboxed.

**Características:**
- Ejecuta código Python arbitrario de forma segura
- Soporta generación de gráficos con matplotlib
- Guarda archivos generados automáticamente
- Hace requests HTTP directas al code interpreter
- Acepta `Language.PYTHON` para evitar problemas de validación

**Uso:**
```python
from tools.python_tool import FixedPythonTool

python_tool = FixedPythonTool(
    code_interpreter_url="http://localhost:50082",
    storage=storage  # LocalPythonStorage instance
)
```

**Input Schema:**
- `code` (str): Código Python a ejecutar
- `language` (str): Lenguaje de programación (default: "Language.PYTHON")
- `input_files` (list[str]): Lista de archivos de input (opcional)

**Output:**
- Stdout del código ejecutado
- Stderr (si hay errores)
- Lista de archivos generados con formato URN
- Exit code

---

### 2. PSQLTool (`psql_tool.py`)

Herramienta para ejecutar queries SQL en bases de datos PostgreSQL.

**Características:**
- Ejecuta queries SELECT, INSERT, UPDATE, DELETE
- Formatea resultados como tablas ASCII
- Soporta múltiples bases de datos
- Usa credenciales seguras vía BeeAI Secrets
- Manejo robusto de errores de PostgreSQL

**Uso:**
```python
from tools.psql_tool import PSQLTool

psql_tool = PSQLTool(
    host="localhost",
    port=5432,
    username="user",
    password="password"
)
```

**Input Schema:**
- `query` (str): Query SQL a ejecutar
- `database` (str): Nombre de la base de datos (default: "postgres")

**Output:**
- Para SELECT: Tabla formateada con resultados
- Para INSERT/UPDATE/DELETE: Número de filas afectadas
- Mensajes de error detallados si falla la query

**Configuración de Secrets:**

El PSQLTool requiere los siguientes secrets configurados en la plataforma BeeAI:

| Secret Key | Descripción | Ejemplo |
|-----------|-------------|---------|
| `PSQL_HOST` | Hostname o IP del servidor PostgreSQL | `localhost`, `db.example.com` |
| `PSQL_PORT` | Puerto del servidor PostgreSQL | `5432` |
| `PSQL_USERNAME` | Usuario de la base de datos | `postgres`, `myuser` |
| `PSQL_PASSWORD` | Contraseña del usuario | `********` |

Para configurar los secrets:
1. Ve a la interfaz de BeeAI
2. Navega a la configuración del agente
3. Agrega los secrets necesarios en la sección "Secrets"
4. Los valores se almacenan de forma segura y se inyectan automáticamente en el agente

---

## Estructura del Código

```
src/tools/
├── __init__.py          # Exporta todas las tools
├── README.md            # Esta documentación
├── python_tool.py       # FixedPythonTool
└── psql_tool.py         # PSQLTool
```

## Crear una Nueva Tool

Para crear una nueva tool personalizada:

1. **Crea un nuevo archivo** en `src/tools/` (ej: `my_tool.py`)

2. **Define el Input Schema** usando Pydantic:
```python
from pydantic import BaseModel, Field

class MyToolInput(BaseModel):
    param1: str = Field(description="Descripción del parámetro")
    param2: int = Field(default=10, description="Parámetro opcional")
```

3. **Implementa la Tool Class**:
```python
from beeai_framework.tools import Tool, StringToolOutput, ToolRunOptions
from beeai_framework.context import RunContext

class MyTool(Tool[MyToolInput, ToolRunOptions, StringToolOutput]):
    name = "MyTool"
    description = "Descripción clara de qué hace la tool"
    input_schema = MyToolInput
    
    async def _run(
        self,
        tool_input: MyToolInput,
        options: ToolRunOptions | None,
        context: RunContext,
    ) -> StringToolOutput:
        # Tu lógica aquí
        result = f"Procesando {tool_input.param1}"
        return StringToolOutput(result)
```

4. **Exporta en `__init__.py`**:
```python
from tools.my_tool import MyTool
__all__ = ["FixedPythonTool", "PSQLTool", "MyTool"]
```

5. **Agrega al agente** en `agent.py`:
```python
from tools.my_tool import MyTool

my_tool = MyTool()
agent = RequirementAgent(
    llm=llm,
    tools=[ThinkTool(), python_tool, psql_tool, my_tool],
    ...
)
```

## Best Practices

1. **Nombres descriptivos**: Usa nombres claros para tools, parámetros y outputs
2. **Documentación**: Incluye descripciones detalladas en el input schema
3. **Manejo de errores**: Usa `ToolError` para errores específicos de la tool
4. **Validación**: Valida inputs con Pydantic validators
5. **Seguridad**: Nunca hardcodees credenciales, usa Secrets
6. **Output claro**: Retorna resultados legibles para el usuario y el LLM

## Referencias

- [BeeAI Framework Tools Documentation](https://framework.beeai.dev/modules/tools)
- [BeeAI Secrets Documentation](https://docs.beeai.dev/build-agents/secrets)
- [Pydantic Documentation](https://docs.pydantic.dev/)

