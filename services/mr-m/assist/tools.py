# services/mr-m/assist/tools.py

SEARCH_KNOWLEDGE_TOOL = {
  "type": "function",
  "function": {
    "name": "search_knowledge",
    "description": "Use FAISS knowledge chunks to answer general questions (bio/background, duties, summaries, talks, projects).",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {"type": "string"},
        "top_k": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20}
      },
      "required": ["query"],
      "additionalProperties": False
    }
  }
}

QUERY_PUBLICATIONS_TOOL = {
  "type": "function",
  "function": {
    "name": "query_publications",
    "description": "Answer publications metadata questions (latest/first N, co-authors, venues).",
    "parameters": {
      "type": "object",
      "properties": {
        "select": {"type": "string", "enum": ["rows", "coauthors", "venues"]},
        "author": {"type": "string"},
        "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 5},
        "first": {"type": "boolean", "description": "True=earliest N (first), False=latest N (last)", "default": False}
      },
      "required": ["select", "author"],
      "additionalProperties": False
    }
  }
}

TOOLS = [QUERY_PUBLICATIONS_TOOL, SEARCH_KNOWLEDGE_TOOL]
