from semantic_tester.api.prompts import (
    SEMANTIC_CHECK_PROMPT,
    get_semantic_check_prompt,
)


class DummyEnvManager:
    def __init__(self, value: str):
        self._value = value

    def get_semantic_check_prompt(self) -> str:  # pragma: no cover - simple passthrough
        return self._value


def test_semantic_check_prompt_default_and_placeholders():
    # 默认提示词应包含三个占位符
    assert "{question}" in SEMANTIC_CHECK_PROMPT
    assert "{ai_answer}" in SEMANTIC_CHECK_PROMPT
    assert "{source_document}" in SEMANTIC_CHECK_PROMPT

    # env_manager 为空或不符合接口时，走默认提示词
    assert get_semantic_check_prompt(None) == SEMANTIC_CHECK_PROMPT
    assert get_semantic_check_prompt(object()) == SEMANTIC_CHECK_PROMPT


def test_semantic_check_prompt_from_env_manager():
    dummy = DummyEnvManager("CUSTOM_PROMPT")
    assert get_semantic_check_prompt(dummy) == "CUSTOM_PROMPT"
