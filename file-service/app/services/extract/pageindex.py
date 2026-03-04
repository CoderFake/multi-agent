"""
PageIndex tree construction helpers — PURE, clean implementation.
This replaces the massive and messy VectifyAI/PageIndex SDK folder.
Parses a markdown file to a hierarchical tree based on headers,
summarizes sections using LLMs (if configured), and extracts bboxes.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Tuple

from app.config.settings import settings

logger = logging.getLogger(__name__)


# ── Internal Markdown Parser ─────────────────────────────────────────────

def _parse_markdown_to_tree(content: str) -> List[Dict[str, Any]]:
    lines = content.split("\n")
    header_pattern = re.compile(r'^(#{1,6})\s+(.+)$')
    code_block_pattern = re.compile(r'^```')
    
    in_code_block = False
    nodes = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if code_block_pattern.match(stripped):
            in_code_block = not in_code_block
            continue
            
        if not in_code_block:
            match = header_pattern.match(stripped)
            if match:
                nodes.append({
                    "title": match.group(2).strip(),
                    "level": len(match.group(1)),
                    "start_index": i,
                    "nodes": []
                })
                
    if not nodes:
        nodes.append({
            "title": "Document",
            "level": 1,
            "start_index": 0,
            "nodes": []
        })

    for i, node in enumerate(nodes):
        if i + 1 < len(nodes):
            node["end_index"] = nodes[i+1]["start_index"] - 1
        else:
            node["end_index"] = len(lines) - 1
            
        text_lines = lines[node["start_index"] : node["end_index"]+1]
        node["text"] = "\n".join(text_lines).strip()

    root_nodes = []
    stack = []
    node_counter = 1
    
    for node in nodes:
        node["node_id"] = f"{node_counter:04d}"
        node_counter += 1
        
        while stack and stack[-1]["level"] >= node["level"]:
            stack.pop()
            
        if not stack:
            root_nodes.append(node)
        else:
            stack[-1]["nodes"].append(node)
            
        stack.append(node)
        
    return root_nodes


# ── LLM Summarization ──────────────────────────────────────────────────

from app.services.retrieval import get_llm

async def _add_summaries(nodes: List[Dict[str, Any]], llm):
    tasks = []
    
    async def process_node(node):
        text = node.get("text", "")
        # Use LLM context if text is notably long
        if len(text) > 400 and llm:
            try:
                from langchain_core.prompts import PromptTemplate
                prompt = PromptTemplate.from_template(
                    "Summarize the following content briefly and concisely (under 100 words) to support search:\n\n{text}"
                )
                chain = prompt | llm
                res = await chain.ainvoke({"text": text})
                node["summary"] = res.content.strip()
            except Exception as e:
                logger.debug("Summary failed for node %s: %s", node["node_id"], e)
                node["summary"] = text[:500]
        else:
            node["summary"] = text[:500]  # Fallback to direct truncation
            
        if node.get("nodes"):
            await _add_summaries(node["nodes"], llm)
            
    for node in nodes:
        tasks.append(process_node(node))
        
    if tasks:
        await asyncio.gather(*tasks)


# ── Public API ─────────────────────────────────────────────────────────

async def build_tree(md_path: str) -> Dict[str, Any]:
    """
    Parse a markdown file, build a hierarchical reasoning tree,
    and generate summaries for each section.
    """
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    tree_nodes = _parse_markdown_to_tree(content)
    
    try:
        llm = get_llm()
    except Exception as e:
        logger.warning("Could not initialize LLM for PageIndex summary: %s", e)
        llm = None
        
    await _add_summaries(tree_nodes, llm)

    logger.info("PageIndex hierarchical tree built: %s", md_path)
    
    # Wrap in root matching the DB schema expectation
    return {"node_id": "root", "title": "root", "nodes": tree_nodes}


def flatten_nodes(tree: Dict[str, Any], parent_id: str | None = None) -> List[Dict[str, Any]]:
    """Recursively flatten a PageIndex tree into a flat node list."""
    nodes: List[Dict[str, Any]] = []
    node = {
        "node_id": tree.get("node_id", ""),
        "title": tree.get("title", ""),
        "summary": tree.get("summary", ""),
        "start_index": tree.get("start_index", 0),
        "end_index": tree.get("end_index", 0),
        "parent_id": parent_id,
    }
    nodes.append(node)

    for child in tree.get("nodes", []):
        nodes.extend(flatten_nodes(child, parent_id=node["node_id"]))

    return nodes


def extract_bbox_from_content(content: str) -> Tuple[List[int], List[Dict]]:
    """
    Extract page numbers and bboxes from HTML comments embedded in node content.
    Comments are of the form: <!-- meta:{...} -->
    """
    pattern = r'<!-- meta:(.*?) -->'
    matches = re.findall(pattern, content)

    pages: set[int] = set()
    bboxes: List[Dict] = []
    for m in matches:
        try:
            meta = json.loads(m)
            pages.add(meta["page"])
            if meta.get("bbox"):
                bboxes.append({
                    "page": meta["page"],
                    "bbox": meta["bbox"],
                    "layout_type": meta.get("layout_type", "text"),
                    "minio_key": meta.get("minio_key", ""),
                })
        except (json.JSONDecodeError, KeyError):
            continue

    return sorted(pages), bboxes
