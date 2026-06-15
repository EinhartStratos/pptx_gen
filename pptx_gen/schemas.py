from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SchemaModel(BaseModel):
    """所有共享数据模型的统一父类。"""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    def to_dict(self, *, compact: bool = True) -> dict[str, Any]:
        """导出为便于查看的 JSON 友好字典。"""

        return self.model_dump(
            mode="json",
            exclude_none=True,
            exclude_defaults=compact,
        )


class BoundingBox(SchemaModel):
    """PPT 元素的位置和尺寸。"""

    x: int = Field(default=0, description="左上角横坐标，单位为 EMU")
    y: int = Field(default=0, description="左上角纵坐标，单位为 EMU")
    w: int = Field(default=0, description="宽度，单位为 EMU")
    h: int = Field(default=0, description="高度，单位为 EMU")


class SlideSize(SchemaModel):
    """整份 PPT 的页面尺寸。"""

    cx: int = Field(..., ge=0, description="页面总宽度，单位为 EMU")
    cy: int = Field(..., ge=0, description="页面总高度，单位为 EMU")


class TableSchema(SchemaModel):
    """表格元素的结构约束。"""

    rows: int = Field(default=0, ge=0, description="模板表格行数")
    cols: int = Field(default=0, ge=0, description="模板表格列数")
    default_cells: list[list[str]] | None = Field(default=None, description="模板表格中的默认单元格文本")
    max_rows: int | None = Field(default=None, ge=0, description="建议最大行数")
    max_cols: int | None = Field(default=None, ge=0, description="建议最大列数")


class TitleRule(SchemaModel):
    """页面标题规则。"""

    text: str = Field(default="", description="模板标题文本")
    bbox: BoundingBox = Field(default_factory=BoundingBox, description="标题位置与尺寸")
    style: dict[str, Any] | None = Field(default=None, description="标题样式信息")


class TemplateMeta(SchemaModel):
    """模板级元信息。"""

    file_name: str = Field(..., min_length=1, description="模板文件名")
    slide_count: int = Field(..., ge=0, description="模板总页数")
    slide_size: SlideSize = Field(..., description="PPT 页面尺寸")


class ElementRule(SchemaModel):
    """单个页面元素的模板规则。"""

    id: str = Field(..., min_length=1, description="元素唯一 ID")
    shape_id: int = Field(..., ge=0, description="PowerPoint 内部 shape id")
    type: str = Field(..., min_length=1, description="元素类型，如 title、text、table、image")
    role: str = Field(default="planner", min_length=1, description="节点角色")
    page_no: int = Field(..., ge=1, description="所在页码")
    bbox: BoundingBox = Field(..., description="元素位置与尺寸")
    z_order: int = Field(..., ge=0, description="元素层级顺序")
    editable: bool = Field(..., description="该元素是否允许脚本回填")
    default_text: str | None = Field(default=None, description="模板中已有的默认文字，用于人工排查")
    style: dict[str, Any] | None = Field(default=None, description="文本或图形样式信息")
    content_requirement: str | None = Field(default=None, description="给模型看的内容要求")
    fill_strategy: str = Field(default="replace_text", min_length=1, description="回填策略")
    table_schema: TableSchema | None = Field(default=None, description="表格结构约束")
    diagram_kind: str | None = Field(default=None, description="Mermaid 图类型，例如 architecture、flowchart、sequence")
    is_instructional: bool = Field(default=False, description="该元素是否主要是模板说明文字，而不是最终成品内容")


class PageRule(SchemaModel):
    """单页模板规则。"""

    page_no: int = Field(..., ge=1, description="页码")
    page_name: str = Field(..., min_length=1, description="页面名称")
    page_purpose: str = Field(..., min_length=1, description="页面用途，例如 cover、text、table、diagram")
    supports_mermaid: bool = Field(..., description="该页是否支持 Mermaid 图片生成")
    title: TitleRule = Field(..., description="标题规则")
    elements: list[ElementRule] = Field(default_factory=list, description="页面元素规则列表")

    def to_dict(self, *, compact: bool = True) -> dict[str, Any]:
        payload = super().to_dict(compact=compact)
        payload["elements"] = [item.to_dict(compact=compact) for item in self.elements]
        return payload


class TemplateRules(SchemaModel):
    """整份模板解析结果。"""

    template: TemplateMeta = Field(..., description="模板级元信息")
    pages: list[PageRule] = Field(default_factory=list, description="所有页面规则")

    def to_dict(self, *, compact: bool = True) -> dict[str, Any]:
        payload = super().to_dict(compact=compact)
        payload["pages"] = [page.to_dict(compact=compact) for page in self.pages]
        return payload


class GeneratedElement(SchemaModel):
    """模型生成的单个元素结果。"""

    id: str = Field(..., min_length=1, description="对应模板元素 ID")
    type: str = Field(..., min_length=1, description="生成结果类型")
    content: str | None = Field(default=None, description="文本内容")
    headers: list[str] | None = Field(default=None, description="表格表头")
    rows: list[list[str]] | None = Field(default=None, description="表格行数据")
    image_source_type: str | None = Field(default=None, description="图片来源类型，首版固定为 mermaid")
    diagram_kind: str | None = Field(default=None, description="图形类别")
    mermaid_syntax: str | None = Field(default=None, description="Mermaid 顶层语法，例如 architecture-beta")
    mermaid_source: str | None = Field(default=None, description="完整 Mermaid 原文")
    rendered_path: str | None = Field(default=None, description="渲染后图片路径")


class PageGenerationResult(SchemaModel):
    """单页模型生成结果。"""

    page_no: int = Field(..., ge=1, description="页码")
    should_generate: bool = Field(..., description="该页是否应该保留到最终 PPT")
    skip_reason: str = Field(default="", description="当页面被跳过时的原因")
    elements: list[GeneratedElement] = Field(default_factory=list, description="本页实际需要回填的元素")

    def to_dict(self, *, compact: bool = True) -> dict[str, Any]:
        payload = super().to_dict(compact=compact)
        payload["elements"] = [item.to_dict(compact=compact) for item in self.elements]
        return payload
