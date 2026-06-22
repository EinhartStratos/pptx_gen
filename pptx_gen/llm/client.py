from __future__ import annotations

from abc import ABC, abstractmethod
import json
import urllib.error
import urllib.request

from pptx_gen.config import LLMConfig
from pptx_gen.mermaid_utils import normalize_mermaid_source
from pptx_gen.schemas import GeneratedElement, PageGenerationResult


class BaseLLMClient(ABC):
    @abstractmethod
    def generate_page(self, requirement_text: str, page_rule: dict, system_prompt: str, user_prompt: str) -> PageGenerationResult:
        raise NotImplementedError


class MockLLMClient(BaseLLMClient):
    def generate_page(self, requirement_text: str, page_rule: dict, system_prompt: str, user_prompt: str) -> PageGenerationResult:
        lowered_requirement = requirement_text.lower()
        page_no = int(page_rule["page_no"])
        elements: list[GeneratedElement] = []
        for element in page_rule.get("elements", []):
            element_type = element.get("type", "text")
            role = element.get("role", "")
            content_requirement = element.get("content_requirement", "")
            default_text = element.get("default_text", "")
            is_instructional = bool(element.get("is_instructional", False))
            if element_type in {"title", "text"}:
                if role == "title":
                    content = page_rule.get("title", {}).get("text") or page_rule.get("page_name", f"第{page_no}页")
                else:
                    if is_instructional:
                        content = self._mock_text_from_requirement(page_rule, content_requirement)
                    else:
                        content = self._mock_text_from_requirement(page_rule, content_requirement or default_text)
                    if not content:
                        continue
                elements.append(GeneratedElement(id=element["id"], type="text", content=content))
            elif element_type == "table":
                schema = element.get("table_schema", {})
                cols = max(int(schema.get("cols", 2)), 1)
                rows = max(min(int(schema.get("rows", 2)), 4), 2)
                headers = [f"列{i + 1}" for i in range(cols)]
                body = [[f"示例{r + 1}-{c + 1}" for c in range(cols)] for r in range(max(rows - 1, 1))]
                elements.append(GeneratedElement(id=element["id"], type="table", headers=headers, rows=body))
            elif element_type == "image":
                if any(keyword in lowered_requirement for keyword in ["架构", "流程", "时序", "architecture", "flow", "sequence"]):
                    diagram_kind = element.get("diagram_kind") or "architecture"
                    mermaid_source = self._mock_mermaid(diagram_kind)
                    mermaid_syntax, mermaid_source = normalize_mermaid_source(diagram_kind, mermaid_source)
                    elements.append(
                        GeneratedElement(
                            id=element["id"],
                            type="image",
                            image_source_type="mermaid",
                            diagram_kind=diagram_kind,
                            mermaid_syntax=mermaid_syntax,
                            mermaid_source=mermaid_source,
                        )
                    )
        should_generate = bool(elements)
        skip_reason = "" if should_generate else "需求文档中没有足够信息支撑该页内容。"
        return PageGenerationResult(page_no=page_no, should_generate=should_generate, skip_reason=skip_reason, elements=elements)

    def _mock_text_from_requirement(self, page_rule: dict, hint: str) -> str:
        page_name = page_rule.get("page_name", "该页")
        if not hint:
            return f"请结合需求补充 {page_name} 的关键信息。"
        shortened = hint.strip()
        if len(shortened) > 90:
            shortened = shortened[:90].rstrip() + "..."
        return f"结合需求补充：{shortened}"

    def _mermaid_syntax(self, diagram_kind: str) -> str:
        if diagram_kind == "sequence":
            return "sequenceDiagram"
        if diagram_kind == "flowchart":
            return "flowchart TD"
        return "classDiagram"

    def _mock_mermaid(self, diagram_kind: str) -> str:
        if diagram_kind == "sequence":
            return "sequenceDiagram\nparticipant User\nparticipant System\nUser->>System: 提交请求\nSystem-->>User: 返回结果"
        if diagram_kind == "flowchart":
            return "flowchart TD\nA[输入需求] --> B[解析模板]\nB --> C[生成页面]\nC --> D[输出PPT]"
        return (
            "---\n"
            "config:\n"
            "  class:\n"
            "    hideEmptyMembersBox: true\n"
            "---\n"
            "classDiagram\n"
            "  direction LR\n"
            '  namespace 访问渠道 {\n'
            '    class Browser["浏览器"]\n'
            "  }\n"
            '  namespace 业务系统 {\n'
            '    class PTMS_IMS["PTMS-IMS"]\n'
            '    class ModelService["模型服务"]\n'
            "  }\n"
            "  Browser --> PTMS_IMS\n"
            "  PTMS_IMS --> ModelService"
        )


class OpenAICompatibleLLMClient(BaseLLMClient):
    def __init__(self, config: LLMConfig) -> None:
        if not config.base_url:
            raise ValueError("使用 openai_compatible 提供方时必须配置 PPTX_GEN_LLM_BASE_URL。")
        if not config.api_key:
            raise ValueError("使用 openai_compatible 提供方时必须配置 PPTX_GEN_LLM_API_KEY。")
        self.config = config

    def generate_page(self, requirement_text: str, page_rule: dict, system_prompt: str, user_prompt: str) -> PageGenerationResult:
        payload = {
            "model": self.config.model,
            "temperature": self.config.temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        request = urllib.request.Request(
            url=f"{self.config.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"模型请求失败: HTTP {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"模型请求失败: {exc}") from exc

        payload = json.loads(raw)
        content = payload["choices"][0]["message"]["content"]
        return self._parse_page_result(content, int(page_rule["page_no"]))

    def _parse_page_result(self, content: str, page_no: int) -> PageGenerationResult:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        payload = json.loads(cleaned)
        if "page_no" not in payload:
            payload["page_no"] = page_no
        for element in payload.get("elements", []):
            if element.get("type") != "image" or element.get("image_source_type") != "mermaid":
                continue
            mermaid_source = (element.get("mermaid_source") or "").strip()
            if not mermaid_source:
                continue
            mermaid_syntax, normalized_source = normalize_mermaid_source(element.get("diagram_kind"), mermaid_source)
            if mermaid_syntax:
                element["mermaid_syntax"] = mermaid_syntax
            if normalized_source:
                element["mermaid_source"] = normalized_source
        return PageGenerationResult.model_validate(payload)


def build_llm_client(config: LLMConfig) -> BaseLLMClient:
    if config.provider == "mock":
        return MockLLMClient()
    if config.provider == "openai_compatible":
        return OpenAICompatibleLLMClient(config)
    raise ValueError(f"不支持的模型提供方: {config.provider}")
