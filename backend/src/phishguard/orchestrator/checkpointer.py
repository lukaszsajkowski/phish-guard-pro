"""PostgreSQL checkpointer for LangGraph workflow persistence.

This module provides session persistence via Supabase PostgreSQL,
allowing workflows to be interrupted and resumed across requests.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from phishguard.core import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def get_checkpointer() -> AsyncGenerator:
    """Get a checkpointer instance for workflow persistence.
    
    This context manager creates an AsyncPostgresSaver connected to Supabase.
    
    Yields:
        AsyncPostgresSaver instance connected to Supabase.
        
    Example:
        async with get_checkpointer() as checkpointer:
            graph = create_phishguard_graph()
            result = await graph.ainvoke(
                state,
                config={"configurable": {"thread_id": session_id}},
            )
    """
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    
    settings = get_settings()
    connection_string = settings.supabase_db_url
    
    if not connection_string:
        logger.warning("SUPABASE_DB_URL not set, using memory checkpointer")
        from langgraph.checkpoint.memory import MemorySaver
        yield MemorySaver()
        return
    
    try:
        async with AsyncPostgresSaver.from_conn_string(connection_string) as checkpointer:
            await checkpointer.setup()
            logger.info("Created PostgreSQL checkpointer for session persistence")
            yield checkpointer
    except Exception as e:
        logger.error("Failed to create PostgreSQL checkpointer: %s", e)
        raise


def get_memory_checkpointer():
    """Get an in-memory checkpointer for testing/development.
    
    Returns:
        MemorySaver instance for non-persistent checkpointing.
    """
    from langgraph.checkpoint.memory import MemorySaver
    return MemorySaver()
