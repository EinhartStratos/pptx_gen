from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_project_env(env_file: str | Path | None = None) -> Path | None:
    """加载项目根目录或显式指定路径下的 .env 文件。"""

    candidates: list[Path] = []
    if env_file is not None:
        candidates.append(Path(env_file))
    candidates.append(Path.cwd() / ".env")
    candidates.append(PROJECT_ROOT / ".env")

    for candidate in candidates:
        if candidate.exists():
            load_dotenv(candidate, override=False)
            return candidate
    return None


@dataclass(slots=True)
class LLMConfig:
    provider: str = "mock"
    model: str = "mock-ppt-generator"
    base_url: str = ""
    api_key: str = ""
    timeout_seconds: int = 120
    temperature: float = 0.2

    @classmethod
    def from_env(cls) -> "LLMConfig":
        load_project_env()
        return cls(
            provider=os.getenv("PPTX_GEN_LLM_PROVIDER", "mock"),
            model=os.getenv("PPTX_GEN_LLM_MODEL", "mock-ppt-generator"),
            base_url=os.getenv("PPTX_GEN_LLM_BASE_URL", "").rstrip("/"),
            api_key=os.getenv("PPTX_GEN_LLM_API_KEY", ""),
            timeout_seconds=int(os.getenv("PPTX_GEN_LLM_TIMEOUT", "120")),
            temperature=float(os.getenv("PPTX_GEN_LLM_TEMPERATURE", "0.2")),
        )


@dataclass(slots=True)
class PipelinePaths:
    template_pptx: Path
    requirement_text: Path
    output_dir: Path

    @property
    def rules_json(self) -> Path:
        return self.output_dir / "template_rules.json"

    @property
    def page_results_dir(self) -> Path:
        return self.output_dir / "pages"

    @property
    def mermaid_dir(self) -> Path:
        return self.output_dir / "mermaid"

    @property
    def rendered_dir(self) -> Path:
        return self.output_dir / "rendered"

    @property
    def final_pptx(self) -> Path:
        return self.output_dir / "generated.pptx"
