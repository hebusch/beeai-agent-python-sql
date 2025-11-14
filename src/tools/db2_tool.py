"""
DB2Tool: Tool for executing DB2 queries.

This tool allows agents to connect to IBM DB2 databases and execute SQL queries.
Credentials are provided via environment variables.
"""

import asyncio
import csv
import ibm_db
import os
from typing import Any

from beeai_framework.context import RunContext
from beeai_framework.emitter import Emitter
from beeai_framework.tools import StringToolOutput, Tool, ToolRunOptions, ToolError
from pydantic import BaseModel, Field


class DB2ToolInput(BaseModel):
    """Input schema for DB2 queries."""
    
    query: str = Field(
        description="SQL query to execute. Can be SELECT, INSERT, UPDATE, DELETE, etc."
    )
    database: str = Field(
        default="",
        description="Database name to connect to (optional, can be specified in connection string)"
    )


class DB2Tool(Tool[DB2ToolInput, ToolRunOptions, StringToolOutput]):
    """
    Tool for executing DB2 queries.
    
    This tool connects to an IBM DB2 database using credentials provided
    via environment variables and executes SQL queries.
    """
    
    name = "DB2"
    description = """A tool for executing IBM DB2 queries on the AIOps REPORTER database.
    
This tool connects to the Cloud Pak for AIOps database (REPORTER) with schema DB2INST1.

Main tables available:
- DB2INST1.ALERTS_REPORTER_STATUS: Current state of all alerts (severity, state, owner, team, etc.)
- DB2INST1.INCIDENTS_REPORTER_STATUS: Current state of all incidents (priority, state, owner, team, etc.)
- DB2INST1.ALERTS_AUDIT_SEVERITY: Historical severity changes for alerts
- DB2INST1.ALERTS_SEVERITY_TYPES: Lookup table for severity codes (0-6)

Use this tool to:
- Query alert data (active alerts, critical alerts, unacknowledged alerts, etc.)
- Query incident data (open incidents, incidents by priority, etc.)
- Analyze historical severity changes
- Get counts and distributions by severity, team, owner, etc.

IMPORTANT: 
- Always prefix table names with DB2INST1 schema (e.g., DB2INST1.ALERTS_REPORTER_STATUS)
- Use FETCH FIRST N ROWS ONLY to limit results
- Severity codes: 0=Clear, 1=Indeterminate, 2=Information, 3=Warning, 4=Minor, 5=Major, 6=Critical
- State codes: 0=active/open, 1=closed/resolved"""
    input_schema = DB2ToolInput
    
    def __init__(
        self,
        host: str | None = None,
        port: int = 50000,
        database: str | None = None,
        username: str | None = None,
        password: str | None = None,
        output_dir: str | None = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize the DB2 tool.
        
        Args:
            host: DB2 host (required)
            port: DB2 port (default: 50000)
            database: Database name (required)
            username: Database username (required)
            password: Database password (required)
            output_dir: Directory to save CSV files (optional, for use with PythonTool)
            **kwargs: Additional arguments for Tool
        """
        super().__init__(**kwargs)
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.output_dir = output_dir
    
    def _create_emitter(self) -> Emitter:
        """Create an emitter for the tool."""
        return Emitter.root().child(
            namespace=["tool", "database", "db2"],
            creator=self,
        )
    
    def _build_connection_string(
        self,
        host: str,
        port: int,
        database: str,
        username: str,
        password: str
    ) -> str:
        """
        Build DB2 connection string.
        
        Format: DATABASE=<database>;HOSTNAME=<host>;PORT=<port>;PROTOCOL=TCPIP;UID=<username>;PWD=<password>;
        """
        return (
            f"DATABASE={database};"
            f"HOSTNAME={host};"
            f"PORT={port};"
            f"PROTOCOL=TCPIP;"
            f"UID={username};"
            f"PWD={password};"
        )
    
    async def _run(
        self,
        tool_input: DB2ToolInput,
        options: ToolRunOptions | None,
        context: RunContext,
    ) -> StringToolOutput:
        """
        Execute a DB2 query.
        
        Args:
            tool_input: Input containing the SQL query and optional database name
            options: Tool execution options (not used)
            context: Execution context
            
        Returns:
            StringToolOutput with query results or error message
        """
        # Use database from input if provided, otherwise use default from init
        database = tool_input.database or self.database
        
        # Validate credentials
        if not self.host or not database or not self.username or not self.password:
            raise ToolError(
                "DB2 credentials not configured. "
                "Please provide DB2_HOST, DB2_DATABASE, DB2_USERNAME, and DB2_PASSWORD environment variables."
            )
        
        # Build connection string
        conn_str = self._build_connection_string(
            host=self.host,
            port=self.port,
            database=database,
            username=self.username,
            password=self.password
        )
        
        # Execute DB2 operations in a thread pool (ibm_db is synchronous)
        return await asyncio.to_thread(self._execute_query, conn_str, tool_input.query.strip())
    
    def _execute_query(self, conn_str: str, query: str) -> StringToolOutput:
        """
        Execute a DB2 query synchronously (runs in thread pool).
        
        Args:
            conn_str: DB2 connection string
            query: SQL query to execute
            
        Returns:
            StringToolOutput with query results or error message
        """
        connection = None
        try:
            # Connect to DB2
            connection = ibm_db.connect(conn_str, "", "")
            
            if not connection:
                error_msg = ibm_db.conn_errormsg()
                raise ToolError(f"Failed to connect to DB2: {error_msg}")
            
            # Determine if it's a SELECT query
            is_select = query.upper().strip().startswith(('SELECT', 'WITH', 'VALUES'))
            
            if is_select:
                # Execute SELECT query
                stmt = ibm_db.exec_immediate(connection, query)
                
                if not stmt:
                    error_msg = ibm_db.stmt_errormsg()
                    raise ToolError(f"DB2 query execution error: {error_msg}")
                
                # Fetch results
                rows = []
                try:
                    row = ibm_db.fetch_assoc(stmt)
                    
                    while row:
                        rows.append(row)
                        row = ibm_db.fetch_assoc(stmt)
                except Exception as fetch_error:
                    # Handle fetch errors (like DECFLOAT conversion issues)
                    ibm_db.free_stmt(stmt)
                    error_detail = str(fetch_error)
                    
                    # Provide helpful error message with remediation suggestions
                    error_is_decfloat = "SQL0420N" in error_detail or "DECFLOAT" in error_detail
                    
                    if error_is_decfloat:
                        remediation_msg = (
                            f"Fetch Failure: {error_detail}\n\n"
                            "⚠️  ERROR: SQL0420N (DECFLOAT conversion error)\n\n"
                            "COMMON CAUSES:\n"
                            "1. Using wrong data type in WHERE clause (e.g., state=0 when state is TEXT)\n"
                            "2. Selecting columns with invalid DECFLOAT values\n"
                            "3. Using SELECT * which includes problematic columns\n\n"
                            "SOLUTIONS TO TRY:\n"
                            "1. Check data types: Use state='open' not state=0 (state is TEXT, not numeric)\n"
                            "2. Avoid SELECT * - specify only the columns you need\n"
                            "3. Try removing 'summary' or other text columns if the query still fails\n"
                            "4. Simplify the query: Remove JOIN, subqueries, or complex expressions\n\n"
                            "EXAMPLE - For 'Count alerts by team':\n"
                            "   ✅ SELECT team, COUNT(*) FROM ALERTS_REPORTER_STATUS WHERE state='open' GROUP BY team\n"
                            "   ❌ SELECT team, COUNT(*) FROM ALERTS_REPORTER_STATUS WHERE state=0 GROUP BY team\n\n"
                            "SAFE COLUMNS:\n"
                            "   uuid, id, severity, state, owner, team, firstOccurrenceTime, lastOccurrenceTime\n\n"
                            "⚠️  NO CSV FILE WAS CREATED! Do not try to use PythonTool until DB2Tool succeeds.\n"
                        )
                    else:
                        remediation_msg = (
                            f"Fetch Failure: {error_detail}\n\n"
                            "COMMON CAUSES AND SOLUTIONS:\n"
                            "1. Try selecting specific columns instead of SELECT *\n"
                            "2. Try casting problematic columns:\n"
                            "   - Use CAST(column AS VARCHAR(100)) for numeric columns\n"
                            "   - Example: SELECT CAST(businessCriticality AS VARCHAR(20))\n"
                            "3. Query a different table or use a view (_VW tables may have cleaner data)\n"
                        )
                    raise ToolError(remediation_msg)
                
                # Free statement
                ibm_db.free_stmt(stmt)
                
                if not rows:
                    return StringToolOutput("Query executed successfully. No rows returned.")
                
                # Get column names from first row
                columns = list(rows[0].keys())
                total_rows = len(rows)
                
                # Save results to CSV file if output_dir is configured
                csv_file_info = None
                if self.output_dir and os.path.isdir(self.output_dir):
                    csv_file_info = self._save_to_csv(rows, columns, self.output_dir)
                
                # Format results as a tab-separated table (for easy Python parsing)
                output_lines = []
                
                # Create header (tab-separated)
                header = "\t".join(str(col) for col in columns)
                output_lines.append(header)
                
                # Add rows (limit to first 20 rows for readability in text output)
                max_display_rows = 20
                for row in rows[:max_display_rows]:
                    row_str = "\t".join(
                        str(row[col]) if row[col] is not None else "NULL"
                        for col in columns
                    )
                    output_lines.append(row_str)
                
                # Add summary
                if total_rows > max_display_rows:
                    output_lines.append(f"\n... showing {max_display_rows} of {total_rows} rows")
                else:
                    output_lines.append(f"\nTotal: {total_rows} row{'s' if total_rows != 1 else ''}")
                
                # Add CSV file information if available
                if csv_file_info:
                    output_lines.append(
                        f"\nCSV file saved: {csv_file_info['filename']} ({csv_file_info['row_count']} rows)"
                    )
                    output_lines.append(
                        f"To analyze this data with Python, use: input_files=['{csv_file_info['path']}']"
                    )
                
                text_output = "\n".join(output_lines)
                tool_output = StringToolOutput(text_output)
                
                # Add CSV file metadata for agent to use
                if csv_file_info:
                    tool_output.csv_file = csv_file_info  # type: ignore
                
                return tool_output
            else:
                # Execute non-SELECT queries (INSERT, UPDATE, DELETE, etc.)
                stmt = ibm_db.exec_immediate(connection, query)
                
                if not stmt:
                    error_msg = ibm_db.stmt_errormsg()
                    raise ToolError(f"DB2 query execution error: {error_msg}")
                
                # Get number of affected rows
                affected_rows = ibm_db.num_rows(stmt)
                
                # Free statement
                ibm_db.free_stmt(stmt)
                
                return StringToolOutput(
                    f"Query executed successfully. {affected_rows} row{'s' if affected_rows != 1 else ''} affected."
                )
                
        except ToolError:
            raise
        except Exception as e:
            error_msg = str(e)
            # Try to get DB2-specific error message if connection exists
            if connection:
                try:
                    db2_error = ibm_db.conn_errormsg(connection)
                    if db2_error:
                        error_msg = f"{error_msg} (DB2: {db2_error})"
                except:
                    pass
            raise ToolError(f"Unexpected error executing query: {error_msg}") from e
        finally:
            # Always close the connection
            if connection:
                try:
                    ibm_db.close(connection)
                except:
                    pass
    
    def _save_to_csv(self, rows: list[dict], columns: list[str], output_dir: str) -> dict:
        """
        Save query results to a CSV file with a unique timestamp-based name.
        
        Args:
            rows: List of row dictionaries
            columns: List of column names
            output_dir: Directory to save the CSV file
            
        Returns:
            Dictionary with file information (filename, path)
        """
        from datetime import datetime
        
        # Create db2 subdirectory if it doesn't exist
        db2_dir = os.path.join(output_dir, 'db2')
        os.makedirs(db2_dir, exist_ok=True)
        
        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:17]  # YYYYmmdd_HHMMSS_ms
        csv_filename = f'db2_results_{timestamp}.csv'
        csv_path = os.path.join(db2_dir, csv_filename)
        
        # Write CSV file
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
        
        # For Python code, use /workspace/ path (as expected by code interpreter)
        workspace_path = f"/workspace/{csv_filename}"
        
        return {
            'filename': csv_filename,
            'path': workspace_path,
            'local_path': csv_path,
            'row_count': len(rows)
        }

