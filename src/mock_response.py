MOCK_RESPONSE_TEXT = "模拟响应：该项参数已识别，当前阶段仅验证 Word 写回，需后续商品数据匹配后复核。"


def build_mock_responses(requirements: list[dict[str, str]]) -> list[dict[str, str]]:
    responses: list[dict[str, str]] = []

    for item in requirements:
        response_item = dict(item)
        response_item["response_value"] = MOCK_RESPONSE_TEXT
        responses.append(response_item)

    return responses
