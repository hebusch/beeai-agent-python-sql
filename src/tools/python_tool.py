"""
FixedPythonTool: Tool que hace requests HTTP directas al code interpreter.

Este tool evita la validación estricta del PythonTool del framework,
haciendo requests directas al endpoint que SÍ acepta 'Language.PYTHON'.
"""

import httpx
import shutil
import os
from typing import Any

from beeai_framework.context import RunContext
from beeai_framework.emitter import Emitter
from beeai_framework.tools import StringToolOutput, Tool, ToolRunOptions, ToolError
from beeai_framework.tools.code import LocalPythonStorage
from pydantic import BaseModel, Field


class FixedPythonToolInput(BaseModel):
    """Input schema para el code interpreter."""
    
    code: str = Field(
        description="Python code to execute. Must be written in English. No special characters. No accents."
    )
    language: str = Field(
        default="Language.PYTHON",
        description="Programming language (use 'Language.PYTHON' for Python code)."
    )
    input_files: list[str] = Field(
        default_factory=list,
        description="List of input files to make accessible to the code."
    )


class FixedPythonTool(Tool[FixedPythonToolInput, ToolRunOptions, StringToolOutput]):
    """
    Tool que ejecuta código Python haciendo requests HTTP directas al code interpreter.
    
    Este approach evita la validación estricta del PythonTool del framework
    y permite que el agente pase 'Language.PYTHON' directamente.
    """
    
    name = "Python"
    description = """A tool for writing and executing Python code.
Suitable for data analysis, file operations, computations, plotting, and more.
The code will be executed in a sandboxed environment."""
    input_schema = FixedPythonToolInput
    
    def __init__(self, code_interpreter_url: str, storage: LocalPythonStorage | None = None, **kwargs: Any) -> None:
        """
        Inicializa el tool con la URL del code interpreter.
        
        Args:
            code_interpreter_url: URL del code interpreter (ej: http://localhost:50082)
            storage: LocalPythonStorage para copiar archivos generados
            **kwargs: Argumentos adicionales para Tool
        """
        super().__init__(**kwargs)
        self.code_interpreter_url = code_interpreter_url.rstrip('/')
        self.execute_endpoint = f"{self.code_interpreter_url}/v1/execute"
        self.storage = storage
    
    def _create_emitter(self) -> Emitter:
        """Crea un emitter para el tool."""
        return Emitter.root().child(
            namespace=["tool", "direct", "python"],
            creator=self,
        )
    
    async def _run(
        self,
        tool_input: FixedPythonToolInput,
        options: ToolRunOptions | None,
        context: RunContext,
    ) -> StringToolOutput:
        """
        Ejecuta el código Python haciendo una request HTTP al code interpreter.
        
        Args:
            tool_input: Input con código y configuración
            options: Opciones de ejecución (no usadas)
            context: Contexto de ejecución
            
        Returns:
            StringToolOutput con el resultado de la ejecución
        """
        try:
            # Preparar el payload para el code interpreter
            payload = {
                "language": tool_input.language,
                "source_code": tool_input.code,
            }
            
            # Si hay archivos de input, agregarlos
            if tool_input.input_files:
                payload["input_files"] = tool_input.input_files
            
            # Hacer la request al code interpreter
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.execute_endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                
                result = response.json()
                
                # Obtener archivos generados (dict con filename: hash)
                files_dict = result.get("files", {})
                
                # Copiar archivos generados del interpreter al source (si hay storage configurado)
                if self.storage and files_dict:
                    for filename, file_hash in files_dict.items():
                        # Archivo en interpreter_working_dir
                        src_path = os.path.join(self.storage.interpreter_working_dir, file_hash)
                        # Copiar a local_working_dir
                        if os.path.exists(src_path):
                            # Extraer el nombre base del archivo (ej: /workspace/plot.png -> plot.png)
                            base_filename = os.path.basename(filename)
                            dst_path = os.path.join(self.storage.local_working_dir, base_filename)
                            shutil.copy2(src_path, dst_path)
                
                # Construir el output en formato texto
                output_parts = []
                
                # Agregar stdout si hay
                if result.get("stdout"):
                    output_parts.append(f"{result['stdout']}")
                
                # Agregar stderr si hay
                if result.get("stderr"):
                    output_parts.append(f"Errors:\n{result['stderr']}")
                
                # Agregar exit code si hay error
                exit_code = result.get("exit_code", 0)
                if exit_code != 0:
                    output_parts.append(f"Exit code: {exit_code}")
                
                # Agregar información sobre archivos generados en el formato específico
                if files_dict:
                    file_lines = []
                    for filename, file_hash in files_dict.items():
                        # Extraer nombre base del archivo
                        base_filename = os.path.basename(filename)
                        # Formato: ![filename](urn:bee:file:hash)
                        file_lines.append(f"![{base_filename}](urn:bee:file:{file_hash})")
                    
                    files_output = (
                        "SUCCESS: Files were created. "
                        "IMPORTANT: To show these files to the user, you MUST copy the EXACT markdown below into your final answer. "
                        "DO NOT modify it, DO NOT create your own URLs, DO NOT add extra text. "
                        "Just copy this EXACTLY as-is:\n\n" + 
                        "\n".join(file_lines) +
                        "\n\nRemember: Use the markdown EXACTLY as shown above. The system will convert it to the correct URL automatically."
                    )
                    output_parts.append(files_output)
                
                # Si no hay output en absoluto, indicarlo
                if not output_parts:
                    output_parts.append("Code executed successfully (no output)")
                
                output_text = "\n\n".join(output_parts)
                
                # Crear el output con metadata de archivos
                tool_output = StringToolOutput(output_text)
                # Agregar metadata de archivos generados para acceso posterior (solo los hashes)
                tool_output.generated_files = list(files_dict.values())  # type: ignore
                
                return tool_output
                
        except httpx.HTTPStatusError as e:
            raise ToolError(
                f"Code interpreter returned error {e.response.status_code}: {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise ToolError(
                f"Failed to connect to code interpreter at {self.execute_endpoint}: {str(e)}"
            ) from e
        except Exception as e:
            raise ToolError(f"Unexpected error executing Python code: {str(e)}") from e

