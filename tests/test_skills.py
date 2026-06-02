from __future__ import annotations

from leadfinder.domain.models import UserProfile
from leadfinder.skills import render_lead_finder, render_outreach_system


def test_lead_finder_uses_profile() -> None:
    skill = render_lead_finder(
        UserProfile(company="云想科技", products_desc="玻尿酸面膜", markets="尼日利亚")
    )
    assert "云想科技" in skill
    assert "玻尿酸面膜" in skill
    assert "尼日利亚" in skill
    assert "<leads>" in skill
    assert "{company}" not in skill  # 占位符已全部填充


def test_lead_finder_falls_back_without_profile() -> None:
    skill = render_lead_finder(None)
    assert "护肤品" in skill
    assert "一家中国出口商" in skill  # 默认公司
    assert "{company}" not in skill and "{products}" not in skill  # 无遗留占位符


def test_outreach_uses_company_and_language() -> None:
    skill = render_outreach_system(UserProfile(company="云想", language="中文"))
    assert "云想" in skill
    assert "中文" in skill
    assert '{"subject"' in skill  # JSON 格式说明完好(转义正确)
