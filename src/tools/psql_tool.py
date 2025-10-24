"""
PSQLTool: Tool for executing PostgreSQL queries.

This tool allows agents to connect to PostgreSQL databases and execute SQL queries.
Credentials are provided via BeeAI Secrets extension.
"""

import asyncpg
from typing import Any

from beeai_framework.context import RunContext
from beeai_framework.emitter import Emitter
from beeai_framework.tools import StringToolOutput, Tool, ToolRunOptions, ToolError
from pydantic import BaseModel, Field


class PSQLToolInput(BaseModel):
    """Input schema for PostgreSQL queries."""
    
    query: str = Field(
        description="SQL query to execute. Can be SELECT, INSERT, UPDATE, DELETE, etc."
    )
    database: str = Field(
        default="postgres",
        description="Database name to connect to (default: postgres)"
    )


class PSQLTool(Tool[PSQLToolInput, ToolRunOptions, StringToolOutput]):
    """
    Tool for executing PostgreSQL queries.
    
    This tool connects to a PostgreSQL database using credentials provided
    via the BeeAI Secrets extension and executes SQL queries.
    """
    
    name = "PSQL"
    description = """A tool for executing PostgreSQL queries.
Use this tool to query databases, retrieve data, insert records, update data, or delete records.
IMPORTANT: Always use parameterized queries to prevent SQL injection."""
    input_schema = PSQLToolInput
    
    def __init__(
        self,
        host: str | None = None,
        port: int = 5432,
        username: str | None = None,
        password: str | None = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize the PSQL tool.
        
        Args:
            host: PostgreSQL host (can be overridden by secrets)
            port: PostgreSQL port (default: 5432)
            username: Database username (can be overridden by secrets)
            password: Database password (can be overridden by secrets)
            **kwargs: Additional arguments for Tool
        """
        super().__init__(**kwargs)
        self.host = host
        self.port = port
        self.username = username
        self.password = password
    
    def _create_emitter(self) -> Emitter:
        """Create an emitter for the tool."""
        return Emitter.root().child(
            namespace=["tool", "database", "psql"],
            creator=self,
        )
    
    async def _run(
        self,
        tool_input: PSQLToolInput,
        options: ToolRunOptions | None,
        context: RunContext,
    ) -> StringToolOutput:
        """
        Execute a PostgreSQL query.
        
        Args:
            tool_input: Input containing the SQL query and database name
            options: Tool execution options (not used)
            context: Execution context
            
        Returns:
            StringToolOutput with query results or error message
        """
        # Validate credentials
        if not self.host or not self.username or not self.password:
            raise ToolError(
                "PostgreSQL credentials not configured. "
                "Please provide PSQL_HOST, PSQL_USERNAME, and PSQL_PASSWORD secrets."
            )
        
        try:
            # Connect to PostgreSQL
            connection = await asyncpg.connect(
                host=self.host,
                port=self.port,
                user=self.username,
                password=self.password,
                database=tool_input.database,
                timeout=30.0
            )
            
            try:
                # Execute the query
                query = tool_input.query.strip()
                
                # Determine if it's a SELECT query
                is_select = query.upper().startswith(('SELECT', 'SHOW', 'DESCRIBE', 'EXPLAIN'))
                
                if is_select:
                    # Fetch results for SELECT queries
                    rows = await connection.fetch(query)
                    
                    if not rows:
                        return StringToolOutput("Query executed successfully. No rows returned.")
                    
                    # Format results as a table
                    output_lines = []
                    
                    # Get column names
                    columns = list(rows[0].keys())
                    
                    # Calculate column widths
                    col_widths = {col: len(col) for col in columns}
                    for row in rows:
                        for col in columns:
                            value_str = str(row[col]) if row[col] is not None else "NULL"
                            col_widths[col] = max(col_widths[col], len(value_str))
                    
                    # Create header
                    header = " | ".join(col.ljust(col_widths[col]) for col in columns)
                    separator = "-+-".join("-" * col_widths[col] for col in columns)
                    output_lines.append(header)
                    output_lines.append(separator)
                    
                    # Add rows (limit to first 100 rows for readability)
                    max_rows = 100
                    for i, row in enumerate(rows[:max_rows]):
                        row_str = " | ".join(
                            str(row[col]).ljust(col_widths[col]) if row[col] is not None 
                            else "NULL".ljust(col_widths[col])
                            for col in columns
                        )
                        output_lines.append(row_str)
                    
                    # Add summary
                    total_rows = len(rows)
                    if total_rows > max_rows:
                        output_lines.append(f"\n... showing {max_rows} of {total_rows} rows")
                    else:
                        output_lines.append(f"\nTotal: {total_rows} row{'s' if total_rows != 1 else ''}")
                    
                    return StringToolOutput("\n".join(output_lines))
                else:
                    # Execute non-SELECT queries
                    result = await connection.execute(query)
                    
                    # Extract row count from result (e.g., "INSERT 0 5" -> "5 rows affected")
                    parts = result.split()
                    if len(parts) >= 2 and parts[-1].isdigit():
                        row_count = parts[-1]
                        return StringToolOutput(
                            f"Query executed successfully. {row_count} row{'s' if row_count != '1' else ''} affected."
                        )
                    else:
                        return StringToolOutput(f"Query executed successfully. {result}")
                        
            finally:
                # Always close the connection
                await connection.close()
                
        except asyncpg.PostgresError as e:
            raise ToolError(f"PostgreSQL error: {str(e)}") from e
        except asyncpg.exceptions.InvalidPasswordError as e:
            raise ToolError("Invalid PostgreSQL credentials") from e
        except asyncpg.exceptions.InvalidCatalogNameError as e:
            raise ToolError(f"Database '{tool_input.database}' does not exist") from e
        except Exception as e:
            raise ToolError(f"Unexpected error executing query: {str(e)}") from e

