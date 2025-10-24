import os
import re
from typing import Annotated

from a2a.types import Message, Role, TextPart, Part
from a2a.utils.message import get_message_text
from beeai_framework.agents.react import ReActAgent
from beeai_framework.agents.experimental import RequirementAgent
from beeai_framework.agents.experimental.requirements.conditional import ConditionalRequirement
from beeai_framework.backend import AssistantMessage, UserMessage, ChatModel
from beeai_framework.backend.types import ChatModelParameters
from beeai_framework.tools.think import ThinkTool
from beeai_framework.tools.code import LocalPythonStorage, PythonTool
from beeai_framework.tools import Tool

from beeai_agents.fixed_python_tool import FixedPythonTool
from beeai_framework.memory import UnconstrainedMemory, TokenMemory

from beeai_sdk.a2a.extensions import (
    AgentDetail,
    AgentDetailTool,
    LLMServiceExtensionServer,
    LLMServiceExtensionSpec,
    TrajectoryExtensionServer,
    TrajectoryExtensionSpec,
)
from beeai_sdk.a2a.extensions.services.platform import (
    PlatformApiExtensionServer,
    PlatformApiExtensionSpec,
)
from beeai_sdk.a2a.types import AgentMessage
from beeai_sdk.platform import File
from beeai_sdk.server import Server
from beeai_sdk.server.context import RunContext
from beeai_sdk.server.store.platform_context_store import PlatformContextStore


from dotenv import load_dotenv
load_dotenv()

server = Server()

FrameworkMessage = UserMessage | AssistantMessage

def to_framework_message(message: Message) -> FrameworkMessage:
    """Convert A2A Message to BeeAI Framework Message format"""
    message_text = "".join(part.root.text for part in message.parts if part.root.kind == "text")

    if message.role == Role.agent:
        return AssistantMessage(message_text)
    elif message.role == Role.user:
        return UserMessage(message_text)
    else:
        raise ValueError(f"Invalid message role: {message.role}")

@server.agent(
    name="Agente de Prueba con Python",
    default_input_modes=["text", "text/plain", "application/pdf", "text/csv", "application/json"],
    default_output_modes=["text", "text/plain", "image/png", "image/jpeg", "text/csv", "application/json"],
    detail=AgentDetail(
        ui_type="chat",
        user_greeting="Hola! Agente de Prueba con Python",
        input_placeholder="Ask anything...",
        license="Apache 2.0",
        programming_language="python",
        framework="BeeAI",
        tools=[
            AgentDetailTool(
                name="Python Tool",
                description="Ejecuta código Python",
            ),
        ],
    )
)
async def example_agent(
    input: Message,
    context: RunContext,
    llm: Annotated[LLMServiceExtensionServer, LLMServiceExtensionSpec.single_demand()],
    trajectory: Annotated[TrajectoryExtensionServer, TrajectoryExtensionSpec()],
    platform_api: Annotated[PlatformApiExtensionServer, PlatformApiExtensionSpec()]
):
    """Example agent with Python code execution capabilities"""

    #########################################################
    # Chat and messages context capabilities
    #########################################################

    # Store the current message in the context store
    await context.store(input)

    # Get the current user message
    current_message = get_message_text(input)
    print(f"Current message: {current_message}")

    # Load all messages from conversation history (including current message)
    history = [message async for message in context.load_history() if isinstance(message, Message) and message.parts]

    # Process the conversation history
    print(f"Found {len(history)} messages in conversation (including current)")

    #########################################################
    # LLM capabilities
    #########################################################

    # Obtener el nombre del modelo desde env var o usar el configurado en la plataforma
    model_name = os.getenv("LLM_CHAT_MODEL_NAME", "watsonx:ibm/granite-4-h-small")

    print(f"Inicializando LLM: {model_name}")
    llm = ChatModel.from_name(
        model_name,
        ChatModelParameters(
            temperature=0.1,
            max_tokens=512  # Limitar tokens para evitar respuestas descontroladas
        )
    )

    #########################################################
    # Python Tools Configuration
    #########################################################

    # Code interpreter en puerto 50082 (propio de este agente)
    code_interpreter_url = os.getenv("CODE_INTERPRETER_URL", "http://127.0.0.1:50082")
    
    # Configuración de directorios:
    # - local_working_dir: donde este agente guarda archivos antes de subirlos
    # - interpreter_working_dir: donde el code interpreter espera encontrar archivos
    #   (en docker-compose.yml: ./tmp/code_interpreter se monta a /storage en k8s)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    local_working_dir = os.path.join(project_root, "tmp", "code_interpreter_source")
    interpreter_working_dir = os.path.join(project_root, "tmp", "code_interpreter")
    
    os.makedirs(local_working_dir, exist_ok=True)
    os.makedirs(interpreter_working_dir, exist_ok=True)
    
    storage = LocalPythonStorage(
        local_working_dir=local_working_dir,
        interpreter_working_dir=interpreter_working_dir,
    )
    
    print(f"Inicializando Python Tool: {code_interpreter_url}")
    print(f"  - Local working dir: {local_working_dir}")
    print(f"  - Interpreter working dir: {interpreter_working_dir}")

    # Usar FixedPythonTool que hace requests HTTP directas al code interpreter
    # Esto evita la validación estricta del PythonTool del framework
    python_tool = FixedPythonTool(code_interpreter_url=code_interpreter_url, storage=storage)

    #########################################################
    # Agent Logic Here
    #########################################################

    print(f"Inicializando agente")

    # Create a RequirementAgent with conversation memory
    agent = RequirementAgent(
        llm=llm,
        role="AI Assistant",
        instructions=[
            "You are a helpful assistant that can answer questions and execute Python code.",
            "When the user asks for data, graphs or analysis, you should use the Python tool.",
            "ALWAYS execute the necessary Python code before giving a final answer.",
            "Python code must be written in English. No special characters. No accents.",
            "ALWAYS USE THE TOOLS IN ENGLISH.",
            "IMPORTAT: ALWAYS ANSWER THE USER IN SPANISH."
        ],
        tools=[ThinkTool(), python_tool],
        requirements=[
            ConditionalRequirement(
                ThinkTool, 
                force_at_step=1,
                force_after=[python_tool],
                consecutive_allowed=False
            )
        ],
    )

    # Create a ReActAgent with conversation memory
    # agent = ReActAgent(llm=llm, tools=[python_tool], memory=UnconstrainedMemory())

    # Load conversation history into agent memory
    await agent.memory.add_many(to_framework_message(item) for item in history)

    print("Agente inicializado")

    # Trackear steps ya procesados para evitar duplicados
    processed_step_ids = set()
    
    # Lista para almacenar archivos generados por PythonTool
    all_generated_files = []

    async for event, meta in agent.run(
        get_message_text(input),
        max_iterations=8,
        max_retries_per_step=3,
        total_max_retries=10
    ):
        # ===================================================================
        # LOGICA PARA REACTAGENT (COMENTADA PARA CAMBIO FACIL)
        # ===================================================================
        
        # Solo procesar eventos completos (update), no partial_update
        # if meta.name == 'update' and hasattr(event, 'update') and event.update:
        #     update_key = event.update.key
        #     update_value = event.update.parsed_value
            
        #     # Mostrar el pensamiento del agente
        #     if update_key == 'thought':
        #         yield trajectory.trajectory_metadata(
        #             title="Thinking",
        #             content=update_value
        #         )
            
        #     # Mostrar el nombre de la herramienta que va a usar
        #     elif update_key == 'tool_name':
        #         if update_value:
        #             yield trajectory.trajectory_metadata(
        #                 title=f"{update_value} Tool",
        #                 content=f"The agent decided to use the {update_value} tool."
        #             )
            
        #     # Mostrar el input de la herramienta
        #     elif update_key == 'tool_input':
        #         if update_value:
        #             # Si es PythonTool, extraer el código
        #             if isinstance(update_value, dict) and 'code' in update_value:
        #                 code = update_value.get('code', '')
        #                 content = f"{code}"
        #             else:
        #                 content = f"{update_value}"
                    
        #             yield trajectory.trajectory_metadata(
        #                 title="Tool Input",
        #                 content=content
        #             )
            
        #     # Mostrar el output de la herramienta
        #     elif update_key == 'tool_output':
        #         if update_value:
        #             output_preview = str(update_value)
        #             yield trajectory.trajectory_metadata(
        #                 title="Tool Output",
        #                 content=f"{output_preview}"
        #             )
        
        # # Si es el último evento "success" con iterations, extraer final_answer y archivos
        # elif meta.name == 'success' and hasattr(event, 'iterations') and event.iterations:
        #     last_iteration = event.iterations[-1]
        #     if hasattr(last_iteration, 'state') and hasattr(last_iteration.state, 'final_answer'):
        #         final_answer = last_iteration.state.final_answer
                
        #         if final_answer:
        #             # Extraer URNs de archivos del texto (patrón: urn:bee:file:{hash})
        #             urn_pattern = r'urn:bee:file:([a-f0-9]+)'
        #             file_urns = re.findall(urn_pattern, final_answer)
                    
        #             # Lista para almacenar todos los Parts (texto + imágenes)
        #             all_parts = []
                    
        #             # Diccionario para mapear URNs a URLs reales
        #             urn_to_url = {}
                    
        #             # Base URL de la plataforma (configurable via env var)
        #             platform_url = os.getenv("PLATFORM_URL", "http://127.0.0.1:8334")
                    
        #             # Procesar cada archivo encontrado
        #             for file_hash in file_urns:
        #                 # El archivo está en tmp/code_interpreter/{hash}
        #                 file_path = os.path.join(interpreter_working_dir, file_hash)
                        
        #                 if os.path.exists(file_path):
        #                     # Leer el contenido del archivo
        #                     with open(file_path, 'rb') as f:
        #                         file_content = f.read()
                            
        #                     # Intentar detectar el tipo de archivo por su contenido
        #                     import mimetypes
        #                     # Para archivos generados por matplotlib, suelen ser PNG
        #                     mime_type = 'image/png'
        #                     filename = f'plot_{file_hash[:8]}.png'
                            
        #                     # Intentar detectar por magic bytes
        #                     if file_content.startswith(b'\x89PNG'):
        #                         mime_type = 'image/png'
        #                         filename = f'plot_{file_hash[:8]}.png'
        #                     elif file_content.startswith(b'\xff\xd8\xff'):
        #                         mime_type = 'image/jpeg'
        #                         filename = f'plot_{file_hash[:8]}.jpg'
        #                     elif file_content.startswith(b'%PDF'):
        #                         mime_type = 'application/pdf'
        #                         filename = f'document_{file_hash[:8]}.pdf'
                            
        #                     # Crear el archivo en la plataforma BeeAI
        #                     platform_file = await File.create(
        #                         filename=filename,
        #                         content_type=mime_type,
        #                         content=file_content,
        #                     )

        #                     # Construir URL completa del archivo
        #                     # Formato: http://127.0.0.1:8334/api/v1/files/{file_id}/content
        #                     file_url = f"{platform_url}/api/v1/files/{platform_file.id}/content"
                            
        #                     # Guardar mapeo de URN a URL real del archivo
        #                     urn_to_url[f'urn:bee:file:{file_hash}'] = file_url
                    
        #             # Reemplazar URNs por URLs reales en el texto
        #             modified_text = final_answer
        #             for urn, url in urn_to_url.items():
        #                 modified_text = modified_text.replace(urn, url)
                    
        #             # Agregar el texto modificado como TextPart
        #             all_parts.insert(0, Part(root=TextPart(text=modified_text)))
                    
        #             # Enviar mensaje con todas las parts (texto con URLs + imágenes)
        #             response = AgentMessage(parts=all_parts)
        #             yield response
        #             await context.store(response)
        
        # ===================================================================
        # LOGICA PARA REQUIREMENTAGENT
        # ===================================================================
        
        # Procesar todos los steps nuevos cuando hay un evento

        print(f"Event: {event}")
        print(f"Meta: {meta}")

        if event.state.steps:
            for step in event.state.steps:
                # Solo procesar steps nuevos
                if step.id in processed_step_ids:
                    continue
                    
                processed_step_ids.add(step.id)
                
                if not step.tool:
                    continue

                tool_name = step.tool.name
                
                # Analizar cada tipo de herramienta
                if tool_name == "think":
                    # Extraer el pensamiento del agente
                    thoughts = step.input.get('thoughts', 'Pensando...')
                    
                    yield trajectory.trajectory_metadata(
                        title="Thinking",
                        content=thoughts
                    )
                
                elif tool_name == "Python":
                    # Extraer el código Python que se ejecutará
                    code = step.input.get('code', '')
                    
                    if code:
                        content = code
                    else:
                        content = "Ejecutando código Python..."
                    
                    yield trajectory.trajectory_metadata(
                        title="PythonTool",
                        content=content
                    )
                    
                    # Verificar si hubo error
                    if step.error:
                        error_msg = str(step.error)
                        
                        # Construir un mensaje de error detallado
                        error_details = f"**Error:** {error_msg}\n\n"
                        error_details += "**Input recibido por el tool:**\n"
                        
                        for key, value in step.input.items():
                            if key == 'code':
                                # Mostrar solo primeras líneas del código
                                code_preview = str(value)[:200]
                                if len(str(value)) > 200:
                                    code_preview += "..."
                                error_details += f"- {key}: {code_preview}\n"
                            else:
                                error_details += f"- {key}: {str(value)}\n"
                        
                        yield trajectory.trajectory_metadata(
                            title="PythonTool Error",
                            content=error_details
                        )
                    # Mostrar output si está disponible
                    elif step.output:
                        # StringToolOutput tiene el texto en .result
                        output_text = str(step.output.result) if hasattr(step.output, 'result') else str(step.output)
                        if output_text and output_text.strip():
                            yield trajectory.trajectory_metadata(
                                title="PythonTool Output",
                                content=output_text
                            )
                        
                        # Capturar archivos generados si existen
                        if hasattr(step.output, 'generated_files'):
                            all_generated_files.extend(step.output.generated_files)
                
                elif tool_name == "final_answer":
                    final_answer_text = step.input["response"]

                    print(f"Final answer text: {final_answer_text}")
                    
                    print(f"All generated files: {all_generated_files}")
                    
                    # Si hay archivos generados, procesarlos y reemplazar URNs por URLs
                    if all_generated_files:
                        # Extraer URNs del texto de respuesta
                        urn_pattern = r'urn:bee:file:([a-f0-9]+)'
                        urns_in_text = re.findall(urn_pattern, final_answer_text)
                        
                        # Base URL de la plataforma
                        platform_url = os.getenv("PLATFORM_URL", "http://127.0.0.1:8334")
                        
                        # Mapeo de URN a URL
                        urn_to_url = {}
                        
                        # Procesar cada archivo generado
                        for file_hash in all_generated_files:
                            # Buscar el archivo en el interpreter_working_dir
                            file_path = os.path.join(interpreter_working_dir, file_hash)
                            
                            if os.path.exists(file_path):
                                # Leer contenido del archivo
                                with open(file_path, 'rb') as f:
                                    file_content = f.read()
                                
                                # Detectar tipo de archivo
                                mime_type = 'application/octet-stream'
                                filename = f'file_{file_hash[:8]}.bin'
                                
                                if file_content.startswith(b'\x89PNG'):
                                    mime_type = 'image/png'
                                    filename = f'plot_{file_hash[:8]}.png'
                                elif file_content.startswith(b'\xff\xd8\xff'):
                                    mime_type = 'image/jpeg'
                                    filename = f'plot_{file_hash[:8]}.jpg'
                                elif file_content.startswith(b'%PDF'):
                                    mime_type = 'application/pdf'
                                    filename = f'document_{file_hash[:8]}.pdf'
                                
                                # Subir archivo a la plataforma BeeAI
                                platform_file = await File.create(
                                    filename=filename,
                                    content_type=mime_type,
                                    content=file_content,
                                )
                                
                                # Construir URL completa
                                file_url = f"{platform_url}/api/v1/files/{platform_file.id}/content"
                                
                                # Guardar mapeo
                                urn_to_url[f'urn:bee:file:{file_hash}'] = file_url
                        
                        # Reemplazar URNs en el texto por URLs reales
                        modified_text = final_answer_text
                        for urn, url in urn_to_url.items():
                            modified_text = modified_text.replace(urn, f"{url}")

                        print(f"Modified text: {modified_text}")
                        
                        # Enviar respuesta con texto modificado
                        response = AgentMessage(text=modified_text)
                    else:
                        # Sin archivos, responder con el texto original
                        response = AgentMessage(text=final_answer_text)
                    
                    yield response
                    await context.store(response)

def run():
    server.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", 8000)),
        context_store=PlatformContextStore(),
    )


if __name__ == "__main__":
    run()