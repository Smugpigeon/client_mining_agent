from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from dataclasses import dataclass

import httpx

from leadfinder.domain.enums import LeadType, Priority
from leadfinder.domain.models import Lead

ChatFn = Callable[["LlmConfig", list[dict[str, str]]], str]

_LEADS_BLOCK = re.compile(r"<leads>\s*(.*?)\s*</leads>", re.DOTALL)
_THINK_BLOCK = re.compile(r"<think>.*?</think>\s*", re.DOTALL)
_LEAD_TYPES = {
    "distributor": LeadType.DISTRIBUTOR,
    "importer": LeadType.DISTRIBUTOR,
    "wholesaler": LeadType.DISTRIBUTOR,
    "retailer": LeadType.RETAILER,
    "manufacturer": LeadType.MANUFACTURER,
}


@dataclass
class LlmConfig:
    api_key: str = ""
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "openai/gpt-4o-mini"

    @property
    def configured(self) -> bool:
        return bool(self.api_key)


def llm_config_from_env() -> LlmConfig:
    return LlmConfig(
        api_key=os.environ.get("LLM_API_KEY", ""),
        base_url=os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1"),
        model=os.environ.get("LLM_MODEL", "openai/gpt-4o-mini"),
    )


def _chat_via_http(config: LlmConfig, messages: list[dict[str, str]]) -> str:
    body: dict[str, object] = {"model": config.model, "messages": messages, "temperature": 0.4}
    if "minimax" in config.model.lower():
        # MiniMax-M3 默认深度思考(~50s/条);关掉直接作答,快约 4 倍
        body["thinking"] = {"type": "disabled"}
    response = httpx.post(
        f"{config.base_url}/chat/completions",
        headers={"Authorization": f"Bearer {config.api_key}"},
        json=body,
        timeout=60.0,
    )
    response.raise_for_status()
    data = response.json()
    return str(data["choices"][0]["message"]["content"])


class LlmClient:
    """Chat completion via an OpenAI-compatible API. Inject `chat_fn` in tests."""

    def __init__(self, *, config: LlmConfig, chat_fn: ChatFn | None = None) -> None:
        self._config = config
        self._chat_fn = chat_fn or _chat_via_http

    @property
    def configured(self) -> bool:
        return self._config.configured

    def chat(self, messages: list[dict[str, str]]) -> str:
        return self._chat_fn(self._config, messages)


def _dict_to_lead(item: object) -> Lead | None:
    if not isinstance(item, dict):
        return None
    name = str(item.get("company_name") or "").strip()
    if not name:
        return None

    def field(key: str) -> str | None:
        value = item.get(key)
        return str(value).strip() if value else None

    lead_type = _LEAD_TYPES.get(str(item.get("lead_type") or "").lower(), LeadType.UNKNOWN)
    return Lead(
        company_name=name,
        country=field("country"),
        website=field("website"),
        business=field("business"),
        profile=field("profile"),
        lead_type=lead_type,
        source="chat",
        priority=Priority.MEDIUM,
    )


def parse_assistant_reply(raw: str) -> tuple[str, list[Lead]]:
    """Split an assistant reply into prose + any <leads>JSON</leads> block it carries."""
    raw = _THINK_BLOCK.sub("", raw)  # 去掉推理模型(如 MiniMax-M3)输出的 <think> 思考块
    match = _LEADS_BLOCK.search(raw)
    if not match:
        return raw.strip(), []
    reply = (raw[: match.start()] + raw[match.end() :]).strip()
    leads: list[Lead] = []
    try:
        items = json.loads(match.group(1))
    except json.JSONDecodeError:
        items = []
    if isinstance(items, list):
        for entry in items:
            lead = _dict_to_lead(entry)
            if lead is not None:
                leads.append(lead)
    return reply or "已为你整理出以下潜在客户：", leads
