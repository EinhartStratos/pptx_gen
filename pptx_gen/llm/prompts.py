from __future__ import annotations

import json


def build_system_prompt() -> str:
    return (
        "你是一个严格输出 JSON 的 PPT 内容生成助手。"
        "你必须根据需求全文和单页规则判断该页是否应该生成。"
        "如果没有足够信息，必须返回 should_generate=false 和明确 skip_reason。"
        "首版只允许输出 text、table、image 三类元素；其中 image 只能来自 Mermaid。"
        "模板中的说明文字、填写说明、示例文案只可作为理解页面用途的参考，不能直接照抄到最终结果。"
        "正文内容应尽量压缩为可展示的要点，而不是把需求全文整段搬运进页面。"
        "如果某个元素只是模板说明占位，且当前需求不足以生成真实内容，可以省略该元素。"
        "禁止输出 Markdown 解释、禁止输出代码围栏、禁止输出额外说明。"
    )


def _build_model_rule_view(page_rule: dict) -> dict:
    return {
        "page_no": page_rule["page_no"],
        "page_name": page_rule.get("page_name", ""),
        "page_purpose": page_rule.get("page_purpose", ""),
        "supports_mermaid": page_rule.get("supports_mermaid", False),
        "title": page_rule.get("title", {}),
        "elements": [
            {
                "id": element.get("id"),
                "type": element.get("type"),
                "role": element.get("role"),
                "bbox": element.get("bbox"),
                "content_requirement": element.get("content_requirement"),
                "fill_strategy": element.get("fill_strategy"),
                "table_schema": element.get("table_schema"),
                "diagram_kind": element.get("diagram_kind"),
                "is_instructional": element.get("is_instructional", False),
            }
            for element in page_rule.get("elements", [])
        ],
    }


def build_user_prompt(requirement_text: str, page_rule: dict) -> str:
    model_page_rule = _build_model_rule_view(page_rule)
    output_schema = {
        "page_no": page_rule["page_no"],
        "should_generate": True,
        "skip_reason": "",
        "elements": [
            {
                "id": "title_1",
                "type": "text",
                "content": "页面标题",
            },
            {
                "id": "table_2",
                "type": "table",
                "headers": ["列1", "列2"],
                "rows": [["值1", "值2"]],
            },
            {
                "id": "image_3",
                "type": "image",
                "image_source_type": "mermaid",
                "diagram_kind": "architecture",
                "mermaid_syntax": "architecture-beta",
                "mermaid_source": "architecture-beta\n...",
            },
        ],
    }
    return (
        "请根据下面的需求全文和单页模板规则生成该页内容。\n\n"
        "要求：\n"
        "1. 先判断该页是否适合当前需求。\n"
        "2. 如果不适合，输出 should_generate=false，并写清 skip_reason。\n"
        "3. 文本框内容要简洁，优先提炼要点、分层列点，表格不要超过模板容量。\n"
        "4. 对 is_instructional=true 的元素，不要直接复述模板说明话术，应改写成真实业务内容；如果无法生成真实内容，可以省略该元素。\n"
        "5. 如果某个正文框的说明里提到“可分多页”或“分多页”，请优先按一级章节组织内容，避免单页堆满大段文字。\n"
        "6. 如果页面包含图片区，且适合图形表达，输出 Mermaid。\n"
        "7. 所有元素 id 必须严格复用模板规则里的 id。\n"
        "8. 不需要返回没有生成内容的元素。\n"
        "9. 只输出 JSON。\n\n"
        f"需求全文：\n{requirement_text}\n\n"
        f"单页模板规则：\n{json.dumps(model_page_rule, ensure_ascii=False, indent=2)}\n\n"
        f"输出 JSON 结构示例：\n{json.dumps(output_schema, ensure_ascii=False, indent=2)}"
    )
