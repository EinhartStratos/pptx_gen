from __future__ import annotations

import re


_GROUP_RE = re.compile(r"^group\s+(?P<id>[A-Za-z_][A-Za-z0-9_-]*)\([^)]*\)\[(?P<label>.+)\]$")
_SERVICE_RE = re.compile(
    r"^service\s+(?P<id>[A-Za-z_][A-Za-z0-9_-]*)\([^)]*\)\[(?P<label>.+)\](?:\s+in\s+(?P<group>[A-Za-z_][A-Za-z0-9_-]*))?$"
)
_NAMESPACE_RE = re.compile(r"^namespace\s+(?P<id>[^\s\[{]+)(?:\[(?P<label>.+)\])?\s*\{$")
_CLASS_RE = re.compile(r"^class\s+(?P<id>[^\s\[{]+)(?:\[(?P<label>.+)\])?$")
_SAFE_ID_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def normalize_mermaid_source(diagram_kind: str | None, mermaid_source: str | None) -> tuple[str, str]:
    source = (mermaid_source or "").strip()
    if not source:
        return "", ""

    syntax = _detect_mermaid_syntax(source)
    if syntax == "architecture-beta":
        normalized = _sanitize_class_diagram(_convert_architecture_beta_to_class_diagram(_strip_frontmatter(source)))
        return "classDiagram", normalized
    if syntax == "classDiagram":
        if _has_frontmatter(source):
            return "classDiagram", source
        normalized = _sanitize_class_diagram(source)
        return "classDiagram", normalized

    return syntax, source


def _detect_mermaid_syntax(source: str) -> str:
    if not _has_frontmatter(source):
        return _first_non_empty_line(source)
    return _first_non_empty_line(_strip_frontmatter(source))


def _has_frontmatter(source: str) -> bool:
    lines = [line.strip() for line in source.splitlines() if line.strip()]
    return len(lines) >= 3 and lines[0] == "---" and "---" in lines[1:]


def _strip_frontmatter(source: str) -> str:
    if not _has_frontmatter(source):
        return source
    delimiter_count = 0
    body_lines: list[str] = []
    for line in source.splitlines():
        stripped = line.strip()
        if stripped == "---":
            delimiter_count += 1
            continue
        if delimiter_count >= 2:
            body_lines.append(line)
    return "\n".join(body_lines).strip()


def _convert_architecture_beta_to_class_diagram(source: str) -> str:
    logical_lines = _to_logical_lines(source)
    if not logical_lines:
        return 'classDiagram\n  class Diagram["系统架构图"]'

    group_labels: dict[str, str] = {}
    service_labels: dict[str, str] = {}
    service_groups: dict[str, str] = {}
    service_order: list[str] = []
    edge_lines: list[str] = []

    for line in logical_lines[1:]:
        if line.startswith("group "):
            match = _GROUP_RE.match(line)
            if match:
                group_labels[match.group("id")] = _clean_label(match.group("label"))
            continue

        if line.startswith("service "):
            match = _SERVICE_RE.match(line)
            if match:
                service_id = match.group("id")
                if service_id not in service_labels:
                    service_order.append(service_id)
                service_labels[service_id] = _clean_label(match.group("label"))
                group_id = match.group("group")
                if group_id:
                    service_groups[service_id] = group_id
            continue

        if line.startswith("junction "):
            continue

        if "--" in line or ".." in line:
            edge_lines.append(line)

    if not service_labels:
        return 'classDiagram\n  class Diagram["系统架构图"]'

    rendered_lines = ["classDiagram", "  direction LR"]
    grouped_service_ids: set[str] = set()
    used_namespace_names: set[str] = set()
    for group_id, label in group_labels.items():
        members = [service_id for service_id in service_order if service_groups.get(service_id) == group_id]
        if not members:
            continue
        rendered_lines.append(f"  namespace {_normalize_namespace_name(label, group_id, used_namespace_names)} {{")
        for service_id in members:
            grouped_service_ids.add(service_id)
            rendered_lines.append(f'    class {service_id}["{service_labels[service_id]}"]')
        rendered_lines.append("  }")

    for service_id in service_order:
        if service_id in grouped_service_ids:
            continue
        rendered_lines.append(f'  class {service_id}["{service_labels[service_id]}"]')

    known_nodes = set(service_labels)
    for edge_line in edge_lines:
        edge = _convert_edge_line(edge_line, known_nodes)
        if edge:
            rendered_lines.append(f"  {edge}")

    return "\n".join(rendered_lines)


def _sanitize_class_diagram(source: str) -> str:
    logical_lines = _to_logical_lines(source)
    if not logical_lines:
        return _with_class_diagram_config('classDiagram\n  class node_1["系统架构图"]')

    id_map: dict[str, str] = {}
    namespace_labels: dict[str, str] = {}
    namespace_name_map: dict[str, str] = {}
    class_labels: dict[str, str] = {}
    class_count = 1
    used_namespace_names: set[str] = set()

    for line in logical_lines[1:]:
        if line.startswith("namespace "):
            match = _NAMESPACE_RE.match(line)
            if not match:
                continue
            original_id = match.group("id")
            label = _clean_label(match.group("label") or original_id)
            namespace_labels[original_id] = label
            if original_id not in namespace_name_map:
                namespace_name_map[original_id] = _normalize_namespace_name(label, original_id, used_namespace_names)
            continue

        if line.startswith("class "):
            match = _CLASS_RE.match(line)
            if not match:
                continue
            original_id = match.group("id")
            label = _clean_label(match.group("label") or original_id)
            if original_id not in id_map:
                id_map[original_id] = original_id if _SAFE_ID_RE.fullmatch(original_id) else f"node_{class_count}"
                if not _SAFE_ID_RE.fullmatch(original_id):
                    class_count += 1
            class_labels[original_id] = label

    rendered_lines: list[str] = []
    for line in logical_lines:
        if line == "classDiagram":
            rendered_lines.append(line)
            continue
        if line.startswith("direction "):
            rendered_lines.append(line)
            continue
        if line == "}":
            rendered_lines.append(line)
            continue
        if line.startswith("namespace "):
            match = _NAMESPACE_RE.match(line)
            if not match:
                continue
            original_id = match.group("id")
            rendered_lines.append(f"  namespace {namespace_name_map[original_id]} {{")
            continue
        if line.startswith("class "):
            match = _CLASS_RE.match(line)
            if not match:
                continue
            original_id = match.group("id")
            rendered_lines.append(f'    class {id_map[original_id]}["{class_labels[original_id]}"]')
            continue

        normalized_line = line
        for original_id, safe_id in sorted(id_map.items(), key=lambda item: len(item[0]), reverse=True):
            normalized_line = normalized_line.replace(original_id, safe_id)
        rendered_lines.append(normalized_line)

    return _with_class_diagram_config("\n".join(rendered_lines))


def _normalize_namespace_name(label: str, fallback: str, used_names: set[str]) -> str:
    candidate = re.sub(r"\s+", "", label)
    candidate = re.sub(r"[^\w.-]", "_", candidate)
    candidate = candidate.strip("_")
    if not candidate:
        candidate = fallback if _SAFE_ID_RE.fullmatch(fallback) else f"ns_{len(used_names) + 1}"
    unique_name = candidate
    suffix = 2
    while unique_name in used_names:
        unique_name = f"{candidate}_{suffix}"
        suffix += 1
    used_names.add(unique_name)
    return unique_name


def _with_class_diagram_config(source: str) -> str:
    if "hideEmptyMembersBox" in source:
        return source
    return "---\nconfig:\n  class:\n    hideEmptyMembersBox: true\n---\n" + source


def _convert_edge_line(line: str, known_nodes: set[str]) -> str | None:
    arrow = _extract_arrow(line)
    if arrow is None:
        return None

    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_-]*", line)
    nodes = [token for token in tokens if token in known_nodes]
    if len(nodes) < 2:
        return None

    src, dst = nodes[0], nodes[1]
    label = _extract_edge_label(line)
    edge = f"{src} {arrow} {dst}"
    if label:
        edge += f" : {label}"
    return edge


def _extract_arrow(line: str) -> str | None:
    if "<-->" in line:
        return "<-->"
    if "-->" in line:
        return "-->"
    if "<--" in line:
        return "<--"
    if "--" in line:
        return "--"
    if "..>" in line:
        return "..>"
    if ".." in line:
        return ".."
    return None


def _extract_edge_label(line: str) -> str:
    match = re.search(r"\s:\s(.+)$", line)
    if match is None:
        return ""
    label = match.group(1).strip()
    if re.fullmatch(r"[RTBL]", label):
        return ""
    return _clean_label(label)


def _to_logical_lines(source: str) -> list[str]:
    logical_lines: list[str] = []
    buffer = ""
    for raw_line in source.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if not buffer:
            buffer = line
        else:
            buffer = f"{buffer} {line}"
        if _brackets_balanced(buffer):
            logical_lines.append(buffer)
            buffer = ""
    if buffer:
        logical_lines.append(buffer)
    return logical_lines


def _brackets_balanced(line: str) -> bool:
    pairs = [("[", "]"), ("(", ")")]
    return all(line.count(left) <= line.count(right) for left, right in pairs)


def _clean_label(label: str) -> str:
    cleaned = label.replace("\\n", " ")
    cleaned = cleaned.replace("\n", " ")
    cleaned = cleaned.strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {'"', "'", "`"}:
        cleaned = cleaned[1:-1]
    cleaned = cleaned.replace('"', "'")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _first_non_empty_line(source: str) -> str:
    return next((line.strip() for line in source.splitlines() if line.strip()), "")
