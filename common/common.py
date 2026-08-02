import glob
import json
import mimetypes
import os
import re
import sys
import zipfile
from typing import Any, Dict, List, Tuple

import docx
import fitz
import yaml
from PIL import Image
from langchain_openai import OpenAIEmbeddings

sys.path.append('../')
from setting.setting import *
from _model.model import *

TEXT_FILE_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".xml", ".yaml", ".yml",
    ".csv", ".log", ".html", ".css", ".sql", ".ini", ".cfg", ".conf", ".env", ".sh", ".bat",
    ".ps1", ".java", ".c", ".cpp", ".h", ".go", ".rs", ".swift", ".kt"
}
DOCUMENT_FILE_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".pptx"}
IMAGE_FILE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".ico", ".tiff", ".tif"}
XML_TAG_PATTERN = re.compile(r"<[^>]+>")


def _read_text_with_fallback(file_path: str) -> str:
    for encoding in ("utf-8", "gbk", "utf-8-sig"):
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _strip_xml_tags(raw: str) -> str:
    text = XML_TAG_PATTERN.sub(" ", raw)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _truncate_preview(text: str, limit: int) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    keep = max(limit // 2, 1)
    head = text[: keep // 2]
    tail = text[-keep // 2:]
    return f"{head}\n\n[...中间内容已截断...]\n\n{tail}"


def preliminary_compression(data: str) -> str:
    if len(data) < threshold:
        return data
    logger.info(f"--- 检测到过长 ({len(data)} 字符)，执行首尾截断并尝试摘要 ---")
    keep_len = threshold // 2
    return f"{data[:keep_len // 2]}\n\n[...中间内容已截断...]\n\n{data[-keep_len // 2:]}"


def _parse_frontmatter(raw_content: str) -> Tuple[Dict[str, Any], str]:
    if not raw_content.startswith("---"):
        return dict(), raw_content.strip()

    lines = raw_content.splitlines()
    if not lines or lines[0].strip() != "---":
        return dict(), raw_content.strip()

    end_index = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_index = idx
            break
    if end_index is None:
        return dict(), raw_content.strip()

    frontmatter_text = "\n".join(lines[1:end_index]).strip()
    body = "\n".join(lines[end_index + 1:]).strip()
    if not frontmatter_text:
        return dict(), body

    try:
        data = yaml.safe_load(frontmatter_text) or {}
        if isinstance(data, dict):
            return data, body
    except Exception as e:
        logger.warning(f"技能 frontmatter 解析失败: {e}")
    return dict(), raw_content.strip()


def _read_skill_meta(folder_path: str) -> Dict[str, Any]:
    meta_path = os.path.join(folder_path, "_meta.json")
    if not os.path.exists(meta_path):
        return {}
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.warning(f"读取技能元数据失败 {meta_path}: {e}")
        return {}


def _ensure_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in re.split(r"[,|/\n]+", value) if item.strip()]
    return [str(value).strip()]


def _normalize_extension(value: str) -> str:
    ext = (value or "").strip().lower()
    if not ext:
        return ""
    return ext if ext.startswith(".") else f".{ext}"


def _extract_markdown_headings(text: str) -> List[str]:
    headings = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            headings.append(re.sub(r"^#+\s*", "", stripped))
    return headings


def _build_skill_aliases(entry_name: str, skill_name: str, meta: Dict[str, Any], frontmatter: Dict[str, Any]) -> List[str]:
    aliases = []
    aliases.extend(_ensure_list(frontmatter.get("aliases")))
    aliases.extend(_ensure_list(meta.get("aliases")))
    aliases.extend([entry_name, skill_name])
    if meta.get("slug", ""):
        aliases.extend([entry_name, skill_name,meta.get("slug", "")])


    normalized = []
    seen = set()
    for alias in aliases:
        item = str(alias).strip()
        if not item:
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(item)
    return normalized


def _load_skill_descriptors(skill_folders: List[str] = None) -> List[SkillDescriptor]:
    if not os.path.exists(skills_path):
        return list()

    descriptors: List[SkillDescriptor] = []

    folders_to_process = []
    if skill_folders is not None:
        for name in skill_folders:
            path = os.path.join(skills_path, name)
            if not os.path.isdir(path):
                continue
            folders_to_process.append((name, path))
    else:
        for entry in sorted(os.scandir(skills_path), key=lambda item: item.name):
            if not entry.is_dir():
                continue
            folders_to_process.append((entry.name, entry.path))

    for folder_name, folder_path in folders_to_process:
        skill_md_path = None
        scripts_path_val = ""
        for sub_entry in os.scandir(folder_path):
            if sub_entry.is_file() and sub_entry.name.lower() == "skill.md":
                skill_md_path = sub_entry.path
            elif sub_entry.is_dir() and sub_entry.name.lower() == "scripts":
                scripts_path_val = sub_entry.path

        if not skill_md_path:
            continue

        meta = _read_skill_meta(folder_path)
        skill_slug = str(meta.get("slug") or folder_name)
        skill_name = folder_name
        bodies = []
        files = [skill_md_path]
        merged_frontmatter: Dict[str, Any] = {}
        declared_extensions: List[str] = []

        try:
            raw = _read_text_with_fallback(skill_md_path).strip()
        except Exception as e:
            logger.warning(f"读取技能文件失败 {skill_md_path}: {e}")
            continue

        frontmatter, body = _parse_frontmatter(raw)
        if frontmatter:
            merged_frontmatter.update(frontmatter)
        skill_name = frontmatter.get("name") or skill_name
        description = frontmatter.get("description", "")
        declared_extensions.extend(_ensure_list(frontmatter.get("extensions")))
        if body:
            bodies.append(f"[文件: {os.path.basename(skill_md_path)}]\n{body}")

        if not bodies:
            continue

        merged_body = "\n\n".join(bodies).strip()
        aliases = _build_skill_aliases(folder_name, skill_name, meta, merged_frontmatter)
        extensions = []
        for ext in declared_extensions:
            normalized = _normalize_extension(ext)
            if normalized and normalized not in extensions:
                extensions.append(normalized)

        descriptors.append(
            SkillDescriptor(
                slug=skill_slug,
                name=str(skill_name),
                description=str(description or f"{folder_name} 技能"),
                body=merged_body,
                folder=folder_path,
                files=files,
                extensions=extensions,
                aliases=aliases,
                version=str(meta.get("version") or ""),
                scripts=scripts_path_val
            )
        )

    return descriptors





def _tokenize_for_match(text: str) -> List[str]:
    tokens = []
    seen = set()
    for token in re.findall(r"[a-z0-9_-]+|[\u4e00-\u9fff]{2,}", text.lower()):
        cleaned = token.strip()
        if not cleaned:
            continue
        if cleaned not in seen:
            seen.add(cleaned)
            tokens.append(cleaned)

        # 中文连续短语需要额外拆分，否则“小红书笔记评论”会被当成一个整体，无法命中外部技能包里的中文描述
        if re.fullmatch(r"[\u4e00-\u9fff]{2,}", cleaned):
            length = len(cleaned)
            for gram_size in range(2, min(6, length) + 1):
                for start in range(0, length - gram_size + 1):
                    gram = cleaned[start:start + gram_size]
                    if gram not in seen:
                        seen.add(gram)
                        tokens.append(gram)
    return tokens


def _score_skill_relevance(skill: SkillDescriptor, user_input: str, file_url_path_list: List[str] = None) -> int:
    text = f"{user_input or ''}\n" + "\n".join(file_url_path_list or [])
    lowered = text.lower()
    user_tokens = set(_tokenize_for_match(text))
    score = 0.0

    alias_hits = 0
    for alias in {skill.slug, skill.name, *skill.aliases}:
        normalized_alias = (alias or "").strip().lower()
        if normalized_alias and normalized_alias in lowered:
            alias_hits += 1
    score += alias_hits * 12

    matching_source = "\n".join([
        skill.slug,
        skill.name,
        skill.description,
        "\n".join(skill.aliases),
        skill.body[:2000],
    ])
    matching_terms = set(_tokenize_for_match(matching_source))
    overlap = user_tokens & matching_terms
    overlap_score = min(len(overlap), 12) * 2.5
    score += overlap_score

    if file_url_path_list and skill.extensions:
        input_exts = {_normalize_extension(os.path.splitext(path)[1]) for path in file_url_path_list if path}
        input_exts.discard("")
        if input_exts & set(skill.extensions):
            score += 8

    if not alias_hits and not overlap:
        summary_terms = set(_tokenize_for_match(f"{skill.name}\n{skill.description}"))
        score += min(len(user_tokens & summary_terms), 6)

    return int(score)


def _build_skill_catalog_context(skills: List[SkillDescriptor]) -> str:
    lines = [
        "以下是当前可用的本地技能目录摘要。",
        "借鉴 Kocoro 的做法：系统提示词只保留技能目录，完整技能正文在命中当前任务时再按需注入，避免把全部技能全文塞进上下文。"
    ]
    lines.append("当任务明显属于某个专项技能时，优先调用 use_skill_tool 读取该技能完整说明，再继续执行具体工具。")
    for skill in skills:
        rel_path = os.path.relpath(skill.folder, ROOT_PATH).replace("\\", "/")
        lines.append(f"- {skill.name}: {skill.description} (路径: {rel_path})")
    return "\n".join(lines)


def _build_skill_detail_context(skills: List[SkillDescriptor], content_limit: int) -> str:
    if not skills:
        return "当前任务未命中强相关技能，保留技能目录摘要作为兼容兜底。"

    lines = [
        "以下是与当前任务最相关的技能正文。",
        "这是借鉴 Kocoro 的按需 skill activation 思路后生成的运行时技能上下文，仅注入命中的技能详情："
    ]
    lines.append("如需再次显式拉取某个技能，请调用 use_skill_tool。")
    for skill in skills:
        rel_path = os.path.relpath(skill.folder, ROOT_PATH).replace("\\", "/")
        lines.append(f"\n--- 技能: {skill.name} ---")
        lines.append(f"路径: {rel_path}")
        lines.append(f"描述: {skill.description}")
        lines.append(_truncate_preview(skill.body, content_limit))
    return "\n".join(lines)


def get_skills_context(
    content_limit: int = 3000,
    user_input: str = "",
    file_url_path_list: List[str] = None,
    max_skills: int = 3,
    skill_folders: List[str] = None,
) -> str:
    """读取技能目录上下文，支持全量、目录摘要、按需加载 3 种模式。"""
    descriptors = _load_skill_descriptors(skill_folders=skill_folders)
    init_skill_prompt = f'本地技能skills 存储总路径:{skills_path}'
    if not skill_folders:
        scored = [
            (skill, _score_skill_relevance(skill, user_input=user_input, file_url_path_list=file_url_path_list))
            for skill in descriptors
        ]
        selected = [skill for skill, score in sorted(scored, key=lambda item: item[1], reverse=True) if score > 0][
                   :max_skills]
        if not selected:
            compact_lines = ["未命中强相关技能，下面给出全量技能摘要兜底："]
            for skill in descriptors:
                compact_lines.append(f"- {skill.name}(skill目录:{skill.folder}): {skill.description}")
            return "\n".join(compact_lines)
        return f"{init_skill_prompt} {_build_skill_detail_context(selected, content_limit=content_limit)}"
    else:
        compact_lines = [
            f"- {skill.name}(skill目录:{skill.folder}): {skill.description}" for skill in descriptors
        ]
        skills_prompt = "\n".join(compact_lines)
        return f'{init_skill_prompt}\n{skills_prompt}'


def embedding_text(api_key: str, base_url: str, model: str, text: str, dim: int = 1024) -> Dict:
    try:
        embedding_config: dict[str, Any] = {
            "api_key": api_key,
            "model": model,
            "check_embedding_ctx_length": False
        }
        if base_url:
            embedding_config["base_url"] = base_url
        if dim:
            embedding_config["dimensions"] = dim

        embedder = OpenAIEmbeddings(**embedding_config)
        vector = embedder.embed_query(text)
        return {'error_code': 0, 'error_msg': '', 'vector': vector}
    except Exception as e:
        return {'error_code': -1, 'error_msg': str(e), 'vector': []}



def _parse_pdf_page_selector(page_selector: str, total_pages: int) -> Tuple[int, int]:
    selector = (page_selector or "all").strip().lower()
    if selector in {"", "all"}:
        return 0, max(total_pages - 1, 0)

    if "-" in selector:
        start_str, end_str = selector.split("-", 1)
        start = max(int(start_str.strip()) - 1, 0)
        end = min(int(end_str.strip()) - 1, total_pages - 1)
        if end < start:
            raise ValueError(f"无效的 PDF 页码范围: {page_selector}")
        return start, end

    page_index = int(selector) - 1
    if page_index < 0:
        raise ValueError(f"无效的 PDF 页码: {page_selector}")
    page_index = min(page_index, total_pages - 1)
    return page_index, page_index


def read_pdf(pdf_path: str, pages: str = "all") -> str:
    """直接读取 PDF 文本，可指定页码或页码范围。"""
    doc = None
    try:
        doc = fitz.open(pdf_path)
        if doc.page_count == 0:
            return ""
        start, end = _parse_pdf_page_selector(pages, doc.page_count)
        text_content = []
        for page_index in range(start, end + 1):
            page = doc.load_page(page_index)
            text_content.append(page.get_text("text"))
        return "\n\n".join(text_content).strip()
    finally:
        if doc:
            doc.close()


def read_docx(docx_path: str) -> str:
    """读取 docx 文件内容，优先使用 python-docx，失败时回退为原始 XML 文本提取。"""
    try:
        document = docx.Document(docx_path)
        return "\n".join(para.text for para in document.paragraphs if para.text)
    except Exception:
        with zipfile.ZipFile(docx_path, "r") as zf:
            raw = zf.read("word/document.xml").decode("utf-8", errors="ignore")
        return _strip_xml_tags(raw)


def read_xlsx(xlsx_path: str) -> str:
    """读取 xlsx 文件内容，回退为共享字符串和工作表 XML 的纯文本拼接。"""
    texts = []
    with zipfile.ZipFile(xlsx_path, "r") as zf:
        for member in sorted(zf.namelist()):
            if member == "xl/sharedStrings.xml" or (member.startswith("xl/worksheets/") and member.endswith(".xml")):
                raw = zf.read(member).decode("utf-8", errors="ignore")
                texts.append(f"=== {os.path.basename(member)} ===\n{_strip_xml_tags(raw)}")
    return "\n\n".join(texts).strip()


def read_pptx(pptx_path: str) -> str:
    """读取 pptx 文件内容，提取每一页 slide 的纯文本。"""
    slides = []
    with zipfile.ZipFile(pptx_path, "r") as zf:
        for member in sorted(zf.namelist()):
            if member.startswith("ppt/slides/slide") and member.endswith(".xml"):
                raw = zf.read(member).decode("utf-8", errors="ignore")
                slides.append(f"=== {os.path.basename(member)} ===\n{_strip_xml_tags(raw)}")
    return "\n\n".join(slides).strip()


def extract_supported_text(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext in TEXT_FILE_EXTENSIONS:
        return _read_text_with_fallback(file_path)
    if ext == ".docx":
        return read_docx(file_path)
    if ext == ".pdf":
        return read_pdf(file_path)
    if ext == ".xlsx":
        return read_xlsx(file_path)
    if ext == ".pptx":
        return read_pptx(file_path)
    return ""


def _build_image_attachment_preview(file_path: str) -> str:
    try:
        with Image.open(file_path) as image:
            width, height = image.size
            image_format = image.format or "unknown"
            image_mode = image.mode or "unknown"
        file_size = os.path.getsize(file_path)
        return (
            f"类型: 图片\n"
            f"格式: {image_format}\n"
            f"尺寸: {width}x{height}\n"
            f"颜色模式: {image_mode}\n"
            f"文件大小: {file_size} bytes\n"
            f"处理策略: 借鉴 Kocoro 的附件分流思路，仅注入路径和元信息，不直接把图片二进制塞进上下文。"
        )
    except Exception as e:
        return f"类型: 图片\n处理策略: 检测到图片附件，但图片元信息读取失败: {e}"


def build_attachment_context(
    file_url_path_list: List[str] = None,
    per_file_limit: int = 4000,
    total_limit: int = 12000,
) -> str:
    """按附件类型切分上下文，文档提取文本，图片只保留元信息，避免二进制污染。"""
    if not file_url_path_list:
        return ""

    blocks = ["以下是按附件类型分流后的上下文片段（借鉴 Kocoro 的附件处理思路）："]
    for index, raw_path in enumerate(file_url_path_list[:file_list_max_length], start=1):
        file_path = (raw_path or "").strip()
        if not file_path:
            continue

        if file_path.startswith("http://") or file_path.startswith("https://"):
            blocks.append(
                f"\n--- 附件 {index} ---\n"
                f"来源: 远程链接\n"
                f"地址: {file_path}\n"
                f"处理策略: 远程文件先保留链接，不把远程二进制内容直接注入上下文；需要时应先下载再处理。"
            )
            continue

        ext = os.path.splitext(file_path)[1].lower()
        if not os.path.exists(file_path):
            blocks.append(
                f"\n--- 附件 {index} ---\n"
                f"路径: {file_path}\n"
                f"状态: 文件不存在，暂无法提取内容。"
            )
            continue

        mime_type, _ = mimetypes.guess_type(file_path)
        header = f"\n--- 附件 {index} ---\n路径: {file_path}\n扩展名: {ext or 'unknown'}\nMIME: {mime_type or 'unknown'}"

        if ext in IMAGE_FILE_EXTENSIONS:
            blocks.append(f"{header}\n{_build_image_attachment_preview(file_path)}")
            continue

        extracted_text = ""
        try:
            extracted_text = extract_supported_text(file_path)
        except Exception as e:
            logger.warning(f"附件文本提取失败 {file_path}: {e}")

        if extracted_text:
            blocks.append(
                f"{header}\n"
                f"类型: 可提取文本附件\n"
                f"处理策略: 仅提取可读文本片段进入上下文，原文件路径仍保留给工具调用。\n"
                f"内容预览:\n{_truncate_preview(extracted_text.strip(), per_file_limit)}"
            )
            continue

        file_size = os.path.getsize(file_path)
        blocks.append(
            f"{header}\n"
            f"类型: 非文本/未支持直接解析的附件\n"
            f"文件大小: {file_size} bytes\n"
            f"处理策略: 仅保留路径和类型，不将二进制内容注入上下文。"
        )

    return _truncate_preview("\n\n".join(blocks), total_limit)


def read_and_split_file(file_path: str, split_pattern: str = r"\n\n", chunk_size: int = 5000) -> List:
    """
    读取文件并按规则切片。
    支持 txt、md、docx、pdf、xlsx、pptx 等可提取文本的文件。
    """
    if not os.path.exists(file_path):
        logger.warning(f"文件不存在: {file_path}")
        return list()

    try:
        content = extract_supported_text(file_path)
    except Exception as e:
        logger.warning(f"读取文件失败 {file_path}: {e}")
        return list()

    if not content:
        logger.warning(f"不支持的文件格式或内容为空: {file_path}")
        return list()

    try:
        fragments = re.split(split_pattern, content)
    except re.error as e:
        logger.warning(f"无效的正则表达式: {split_pattern}, 错误: {e}")
        return list()

    chunks = list()
    current_chunk = ""
    for frag in fragments:
        if not current_chunk:
            current_chunk = frag
        elif len(current_chunk) + len(frag) <= chunk_size:
            current_chunk += "\n\n" + frag
        else:
            chunks.append(current_chunk)
            current_chunk = frag

        while len(current_chunk) > chunk_size:
            chunks.append(current_chunk[:chunk_size])
            current_chunk = current_chunk[chunk_size:]

    if current_chunk:
        chunks.append(current_chunk)
    return chunks


# --- MCP 工具插件加载 ---
# def get_mcp_tools():
#     """从 setting.mcp_tool_config 配置中加载所有 MCP 工具并返回 LangChain 工具列表"""
#
#
#     mcp_compat = McpCompatible(mcp_tool_config)
#     return mcp_compat.load_mcp_tools()
