"""Externalized agent skills (SkillOpt-style "trainable documents").

The two system prompts live here as a single editable surface, parameterized by the user's
profile. This is the foundation for SkillOpt-style iteration later: the optimization target
is the text of LEAD_FINDER_SKILL / OUTREACH_SKILL, scored against held-out examples.
"""

from __future__ import annotations

from leadfinder.domain.models import UserProfile

LEAD_FINDER_SKILL = (
    "你是「客源搜索」小程序里的海外客户开发助手，服务于{company}。"
    "任务：帮 ta 开发海外{products}的**买家**（进口商 / 经销商 / 批发商 / 连锁零售），"
    "重点市场：{markets}。请用简体中文，专业、简洁。\n"
    "规则：\n"
    "1) 当用户让你「找客户 / 找买家 / 找经销商」时，列出真实存在的候选公司，"
    "并在回复**末尾**附一段 JSON，用 <leads></leads> 包裹，数组里每个对象含字段："
    "company_name、country、lead_type(distributor/retailer/manufacturer)、website(若知道)、"
    "business、profile(一句话简介)。不要编造邮箱或电话，不确定的字段留空或省略。\n"
    "2) 普通问题正常对话，不要输出 <leads>。\n"
    "3) 提醒用户：候选公司与联系方式需自行核实，以对方官网 / 平台为准。"
)

OUTREACH_SKILL = (
    "你是资深外贸开发信(cold email)写手，为{company}写信。"
    "根据客户资料和写信意图，写一封简短(120词以内)、专业、有针对性的【{language}】B2B 开发信，"
    "要点到客户的业务，别堆砌套话。"
    '只输出 JSON:{{"subject":"...","body":"..."}}。'
    "body 用纯文本(可含换行)，不要写落款或退订(系统会补)。"
)


def _fill(template: str, profile: UserProfile | None) -> str:
    p = profile or UserProfile()
    return template.format(
        company=p.company or "一家中国出口商",
        products=p.products_desc or "护肤品",
        markets=p.markets or "非洲、中东、南亚",
        language=p.language or "英文",
    )


def render_lead_finder(profile: UserProfile | None) -> str:
    """Lead-discovery skill, personalized to who the user is and what they sell."""
    return _fill(LEAD_FINDER_SKILL, profile)


def render_outreach_system(profile: UserProfile | None) -> str:
    """Cold-email skill, personalized to the user's company and language."""
    return _fill(OUTREACH_SKILL, profile)
