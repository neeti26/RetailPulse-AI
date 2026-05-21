"""
RetailPulse AI — Observability & Monitoring Layer
Tracks every agent tool call, sub-agent delegation, latency, and outcome.
Writes structured logs to MongoDB `agent_traces` collection.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/retailpulse")
DB_NAME = os.getenv("MONGODB_DB_NAME", "retailpulse")

# ── Structured JSON logger ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","msg":%(message)s}',
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger("retailpulse")

_db = None


def _get_db():
    global _db
    if _db is not None:
        return _db
    try:
        from pymongo import MongoClient
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=2000)
        client.admin.command("ping")
        _db = client[DB_NAME]
        return _db
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Trace dataclass
# ─────────────────────────────────────────────────────────────────────────────
class AgentTrace:
    """Records a single agent execution trace."""

    def __init__(self, session_id: str, user_query: str):
        self.session_id = session_id
        self.user_query = user_query
        self.trace_id = f"TRACE-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S%f')[:20]}"
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.tool_calls: list[dict] = []
        self.sub_agent_calls: list[dict] = []
        self.errors: list[dict] = []
        self.total_tokens = 0
        self._start_time = time.time()

    def log_tool_call(
        self,
        tool_name: str,
        collection: str,
        operation_desc: str,
        result_count: int = 0,
        success: bool = True,
        error: str = "",
    ):
        """Record a MongoDB MCP tool call."""
        latency_ms = int((time.time() - self._start_time) * 1000)
        entry = {
            "tool": tool_name,
            "collection": collection,
            "operation": operation_desc,
            "result_count": result_count,
            "latency_ms": latency_ms,
            "success": success,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.tool_calls.append(entry)
        logger.info(json.dumps({
            "event": "tool_call",
            "trace_id": self.trace_id,
            **entry,
        }))
        if not success:
            self.errors.append({"type": "tool_error", "tool": tool_name, "error": error})

    def log_sub_agent(
        self,
        agent_name: str,
        task: str,
        success: bool = True,
        result_summary: str = "",
    ):
        """Record a sub-agent delegation."""
        latency_ms = int((time.time() - self._start_time) * 1000)
        entry = {
            "agent": agent_name,
            "task": task,
            "success": success,
            "result_summary": result_summary[:200],
            "latency_ms": latency_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.sub_agent_calls.append(entry)
        logger.info(json.dumps({
            "event": "sub_agent_delegation",
            "trace_id": self.trace_id,
            **entry,
        }))

    def complete(self, final_response: str, token_estimate: int = 0) -> dict:
        """Finalize the trace and persist to MongoDB."""
        elapsed_ms = int((time.time() - self._start_time) * 1000)
        self.total_tokens = token_estimate

        trace_doc = {
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "user_query": self.user_query[:500],
            "started_at": self.started_at,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "total_latency_ms": elapsed_ms,
            "tool_calls": self.tool_calls,
            "tool_call_count": len(self.tool_calls),
            "sub_agent_calls": self.sub_agent_calls,
            "sub_agent_count": len(self.sub_agent_calls),
            "errors": self.errors,
            "error_count": len(self.errors),
            "success_rate": (
                round((len(self.tool_calls) - len(self.errors)) /
                      max(len(self.tool_calls), 1) * 100, 1)
            ),
            "token_estimate": token_estimate,
            "response_length": len(final_response),
            "collections_accessed": list({tc["collection"] for tc in self.tool_calls}),
        }

        # Persist to MongoDB
        db = _get_db()
        if db is not None:
            try:
                db["agent_traces"].insert_one({**trace_doc, "_id": self.trace_id})
            except Exception:
                pass  # Don't fail the agent if observability fails

        logger.info(json.dumps({
            "event": "trace_complete",
            "trace_id": self.trace_id,
            "total_latency_ms": elapsed_ms,
            "tool_calls": len(self.tool_calls),
            "sub_agents": len(self.sub_agent_calls),
            "errors": len(self.errors),
        }))

        return trace_doc


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard metrics
# ─────────────────────────────────────────────────────────────────────────────
def get_observability_metrics() -> dict:
    """Returns agent performance metrics for the observability dashboard."""
    db = _get_db()
    if db is None:
        return {
            "total_queries": 0, "avg_latency_ms": 0, "avg_tool_calls": 0,
            "success_rate": 100.0, "top_collections": [], "recent_traces": [],
        }
    try:
        from datetime import timedelta
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        since_str = since.isoformat()

        traces = list(db["agent_traces"].find(
            {"started_at": {"$gte": since_str}},
            {"_id": 0, "trace_id": 1, "user_query": 1, "total_latency_ms": 1,
             "tool_call_count": 1, "error_count": 1, "success_rate": 1,
             "started_at": 1, "collections_accessed": 1}
        ).sort("started_at", -1).limit(50))

        if not traces:
            return {
                "total_queries": 0, "avg_latency_ms": 0, "avg_tool_calls": 0,
                "success_rate": 100.0, "top_collections": [], "recent_traces": [],
            }

        avg_latency = sum(t.get("total_latency_ms", 0) for t in traces) / len(traces)
        avg_tools = sum(t.get("tool_call_count", 0) for t in traces) / len(traces)
        avg_success = sum(t.get("success_rate", 100) for t in traces) / len(traces)

        # Top collections
        all_collections: list = []
        for t in traces:
            all_collections.extend(t.get("collections_accessed", []))
        from collections import Counter
        top_cols = Counter(all_collections).most_common(5)

        return {
            "total_queries": len(traces),
            "avg_latency_ms": round(avg_latency),
            "avg_tool_calls": round(avg_tools, 1),
            "success_rate": round(avg_success, 1),
            "top_collections": [{"collection": c, "count": n} for c, n in top_cols],
            "recent_traces": [
                {
                    "trace_id": t["trace_id"][-12:],
                    "query": t["user_query"][:50] + "…",
                    "latency": f"{t.get('total_latency_ms', 0):,}ms",
                    "tools": t.get("tool_call_count", 0),
                    "status": "✅" if t.get("error_count", 0) == 0 else "⚠️",
                }
                for t in traces[:10]
            ],
        }
    except Exception:
        return {
            "total_queries": 0, "avg_latency_ms": 0, "avg_tool_calls": 0,
            "success_rate": 100.0, "top_collections": [], "recent_traces": [],
        }
