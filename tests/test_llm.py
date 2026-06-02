from __future__ import annotations

from leadfinder.domain.models import Recipient
from leadfinder.infra.llm import (
    LlmClient,
    LlmConfig,
    generate_outreach_email,
    parse_assistant_reply,
)


def test_strips_think_block_and_parses_leads() -> None:
    raw = (
        "<think>\n用户想找尼日利亚买家,先想想\n</think>\n"
        "为你找到一家:\n"
        '<leads>[{"company_name":"Acme","country":"Nigeria","lead_type":"distributor"}]</leads>'
    )
    reply, leads = parse_assistant_reply(raw)
    assert "<think>" not in reply
    assert "先想想" not in reply
    assert reply.startswith("为你找到一家")
    assert len(leads) == 1
    assert leads[0].company_name == "Acme"
    assert leads[0].source == "chat"


def test_plain_reply_has_no_leads() -> None:
    reply, leads = parse_assistant_reply("普通回答，没有客户。")
    assert reply == "普通回答，没有客户。"
    assert leads == []


def test_importer_and_wholesaler_map_to_distributor() -> None:
    raw = (
        "<leads>["
        '{"company_name":"A","lead_type":"importer"},'
        '{"company_name":"B","lead_type":"wholesaler"}'
        "]</leads>"
    )
    _, leads = parse_assistant_reply(raw)
    assert [lead.lead_type.value for lead in leads] == ["distributor", "distributor"]


def test_generate_outreach_email_parses_subject_body() -> None:
    def fake_chat(config: LlmConfig, messages: list[dict[str, str]]) -> str:
        return '<think>想想客户</think>{"subject":"Hi Acme","body":"We export skincare."}'

    client = LlmClient(config=LlmConfig(api_key="x"), chat_fn=fake_chat)
    subject, body = generate_outreach_email(
        client,
        system_prompt="write a cold email",
        recipient=Recipient(email="a@b.com", company_name="Acme"),
        brief="合作",
    )
    assert subject == "Hi Acme"
    assert body == "We export skincare."
