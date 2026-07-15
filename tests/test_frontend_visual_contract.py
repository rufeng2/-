from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_global_design_tokens_and_accessibility_contract():
    css = (ROOT / "frontend/src/styles/global.css").read_text(encoding="utf-8")
    for token in ("--ink", "--surface", "--primary", "--success", "--border", "--sidebar"):
        assert token in css
    assert ":focus-visible" in css
    assert "@media(max-width:760px)" in css.replace(" ", "")
    assert "letter-spacing:0" in css.replace(" ", "")


def test_chat_uses_workspace_semantics_without_emoji_identity():
    source = (ROOT / "frontend/src/views/Chat.vue").read_text(encoding="utf-8")
    assert "conversation-rail" in source
    assert "suggested-questions" in source
    assert "sidebar-footer" not in source
    assert "📚" not in source
    assert "👤" not in source
    assert "🤖" not in source
