import io
import os
import re
from typing import Callable, List, Optional, Tuple, Union

from opencc import OpenCC
from pdf_oxide import DocumentBuilder, EmbeddedFont, PdfDocument
from PIL import Image, ImageFont

# ---------------------------------------------------------------------------
# 输出 PDF 使用的内嵌字体查找
# ---------------------------------------------------------------------------

# 各平台常见 CJK 字体（按优先级排列），用于输出 PDF 的中文渲染
_CJK_FONT_REGULAR_CANDIDATES = [
    # Windows
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\Deng.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
    r"C:\Windows\Fonts\simkai.ttf",
    # Linux
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc",
    "/usr/share/fonts/wenquanyi/wqy-microhei/wqy-microhei.ttc",
    "/usr/share/fonts/wqy-zenhei/wqy-zenhei.ttc",
    # macOS
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
]

_CJK_FONT_BOLD_CANDIDATES = [
    # Windows
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\Dengb.ttf",
    # Linux
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
]

# 拉丁字体（用于英文、数字等纯西文内容，避免中文字体的方块半角拉丁字形）
_LATIN_SANS_CANDIDATES = [
    r"C:\Windows\Fonts\arial.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]

_LATIN_SANS_BOLD_CANDIDATES = [
    r"C:\Windows\Fonts\arialbd.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]

_LATIN_SERIF_CANDIDATES = [
    r"C:\Windows\Fonts\times.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "/usr/share/fonts/dejavu/DejaVuSerif.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
]

_LATIN_SERIF_BOLD_CANDIDATES = [
    r"C:\Windows\Fonts\timesbd.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSerif-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
]

# 原文 span 字体名包含这些关键词时，西文部分使用衬线拉丁字体
_SERIF_NAME_HINTS = ('times', 'roman', 'serif', 'georgia', 'garamond', 'book',
                     'song', 'sun', 'ming', 'kai')

_ASCII_RUN_RE = re.compile(r'([\x20-\x7e]+)')


def _find_first_loadable_font(candidates: List[str], log: Callable[[str], None]) -> Optional[str]:
    """在候选列表中找到第一个存在且可被 EmbeddedFont 加载的字体文件"""
    for path in candidates:
        if not os.path.isfile(path):
            continue
        try:
            EmbeddedFont.from_file(path)
            return path
        except Exception:
            log(f"警告：字体文件无法加载，已跳过 - {path}")
    return None


# ---------------------------------------------------------------------------
# 文本宽度测量（PIL，用于精确推进绘制位置和自适应缩放）
# ---------------------------------------------------------------------------

_font_measure_cache = {}


def _measure(text: str, font_path: str, size: float) -> Optional[float]:
    """
    用 PIL 测量文本以指定字体渲染时的 advance 宽度（PDF pt，1px@72dpi = 1pt）。
    测量失败（字体不支持）返回 None，调用方回退到不缩放。
    """
    if not text:
        return 0.0
    key = (font_path, round(size, 2))
    font = _font_measure_cache.get(key)
    if font is None:
        try:
            font = ImageFont.truetype(font_path, round(size, 2) or 1)
        except Exception:
            _font_measure_cache[key] = False  # 标记该字体不可测量
            return None
        _font_measure_cache[key] = font
    if font is False:
        return None
    try:
        return float(font.getlength(text))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# 文本绘制（中英分字体 + 按脚本切分 + 宽度自适应）
# ---------------------------------------------------------------------------

# 输出文档中各逻辑字体的默认注册名（convert_pdf_file 中按可用字体实例化）
_DEFAULT_FONT_NAMES = {
    'cjk': "CJK-Reg",
    'cjk_bold': "CJK-Bold",
    'latin_sans': "Latin-Sans",
    'latin_sans_bold': "Latin-Sans-Bold",
    'latin_serif': "Latin-Serif",
    'latin_serif_bold': "Latin-Serif-Bold",
}


def _split_by_script(text: str) -> List[Tuple[str, bool]]:
    """
    将文本切分为 (片段, 是否纯西文) 序列，保持原有顺序。
    英文/数字/半角符号使用拉丁字体，其余（中文、全角标点等）使用中文字体。
    """
    runs = []
    for part in re.findall(r'[\x20-\x7e]+|[^\x20-\x7e]+', text):
        if part:
            runs.append((part, ord(part[0]) < 0x80))
    return runs


def _draw_span_text(page_builder, cc, span, fonts: dict,
                    ox: float, oy: float) -> bool:
    """
    转换单个文本片段并按脚本分组绘制。

    - 纯西文片段按原文字体特征选择衬线/非衬线拉丁字体
    - 各片段用 PIL 精确测量宽度，顺序推进绘制位置
    - 总宽超出原文片段宽度时按比例缩小字号，避免与后续文字重叠

    fonts 为 逻辑字体键 -> {'name': 注册名, 'path': 字体文件路径}。
    返回是否实际绘制了内容。
    """
    text = span.text
    if not text or not text.strip():
        return False
    converted = cc.convert(text)
    if not converted:
        return False

    x, y = _offset_point(span.bbox[0], span.bbox[1], ox, oy)
    span_w = span.bbox[2]
    size = span.font_size if span.font_size and span.font_size > 0 else 10.0
    color = span.color or (0.0, 0.0, 0.0)

    # 根据原文字体名判断西文用衬线还是非衬线拉丁字体
    orig_name = (span.font_name or '').lower()
    serif = any(hint in orig_name for hint in _SERIF_NAME_HINTS)

    runs = []
    for part, is_ascii in _split_by_script(converted):
        if is_ascii:
            if serif:
                key = 'latin_serif_bold' if span.is_bold else 'latin_serif'
            else:
                key = 'latin_sans_bold' if span.is_bold else 'latin_sans'
        else:
            key = 'cjk_bold' if span.is_bold else 'cjk'
        entry = fonts.get(key) or fonts['cjk']
        runs.append([part, entry['name'], entry['path']])

    # 宽度自适应：测量失败则不做缩放
    widths = [_measure(r[0], r[2], size) for r in runs]
    if all(w is not None for w in widths):
        total = sum(widths)
        if total > span_w + 0.5 and total > 0:
            scale = max(span_w / total, 0.5)
            size *= scale
            widths = [_measure(r[0], r[2], size) for r in runs]

    for (part, font_name, _path), width in zip(runs, widths):
        page_builder.font(font_name, size).at(x, y).inline_color(
            color[0], color[1], color[2], part)
        if width:
            x += width
    return True


# ---------------------------------------------------------------------------
# 页面元素重建辅助
# ---------------------------------------------------------------------------

def _offset_point(x: float, y: float, ox: float, oy: float) -> Tuple[float, float]:
    """将用户空间坐标平移到以裁剪框左下角为原点的页面坐标系"""
    return x - ox, y - oy


def _draw_lines(page_builder, lines: list, ox: float, oy: float) -> None:
    """按矢量线条的操作序列重画线段（表格边框、下划线等）"""
    for line in lines:
        color = line.get('stroke_color') or (0.0, 0.0, 0.0)
        width = line.get('stroke_width') or 1.0
        cur = None
        for op in line.get('operations', []):
            name = op.get('op')
            if name == 'move_to':
                cur = (op.get('x', 0.0), op.get('y', 0.0))
            elif name == 'line_to' and cur is not None:
                end = (op.get('x', 0.0), op.get('y', 0.0))
                x1, y1 = _offset_point(cur[0], cur[1], ox, oy)
                x2, y2 = _offset_point(end[0], end[1], ox, oy)
                page_builder.stroke_line(x1, y1, x2, y2, width, color)
                cur = end


def _draw_rects(page_builder, rects: list, ox: float, oy: float) -> None:
    """重画矩形（底色块、边框等）；有填充色优先按填充绘制"""
    for rect in rects:
        x, y, w, h = rect.get('bbox', (0.0, 0.0, 0.0, 0.0))
        x, y = _offset_point(x, y, ox, oy)
        fill = rect.get('fill_color')
        if fill is not None:
            page_builder.filled_rect(x, y, w, h, fill[0], fill[1], fill[2])
        else:
            stroke = rect.get('stroke_color') or (0.0, 0.0, 0.0)
            width = rect.get('stroke_width') or 1.0
            page_builder.stroke_rect(x, y, w, h, width, stroke)


def _draw_images(page_builder, doc: PdfDocument, page_index: int,
                 ox: float, oy: float, log: Callable[[str], None]) -> int:
    """
    将页面上的图片按原位置嵌入新文档。
    extract_images 提供位置（bbox），extract_image_bytes 提供图像字节，
    两者按内容流顺序一一对应。
    """
    metas = doc.extract_images(page_index) or []
    blobs = doc.extract_image_bytes(page_index) or []
    if len(metas) != len(blobs):
        log(f"  ⚠ 第{page_index + 1}页图片位置与图像数据数量不一致"
            f"（{len(metas)}/{len(blobs)}），仅按序号对齐绘制")

    drawn = 0
    for meta, blob in zip(metas, blobs):
        bbox = meta.get('bbox')
        data = blob.get('data') if isinstance(blob, dict) else blob
        if not bbox or not data:
            continue
        x, y = _offset_point(bbox[0], bbox[1], ox, oy)
        page_builder.image_with_alt(data, x, y, bbox[2], bbox[3], "")
        drawn += 1
    return drawn


def _rasterize_page_png(doc: PdfDocument, page_index: int, dpi: int = 150) -> Optional[bytes]:
    """
    将整页栅格化为 PNG 字节（用于没有文本层的扫描页，保留原页面外观）。
    栅格化失败返回 None，调用方按空白页处理。
    """
    try:
        pm = doc.render_pixmap(page_index, dpi=dpi)
        im = Image.frombytes("RGBA", (pm.width, pm.height), pm.data)
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        bg.alpha_composite(im)
        buf = io.BytesIO()
        bg.convert("RGB").save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# 公开接口
# ---------------------------------------------------------------------------

def convert_pdf_file(
    input_path: str,
    output_folder: str,
    conversion_type: str,
    log_callback: Optional[Callable[[str], None]] = None,
    is_cancelled_callback: Optional[Callable[[], bool]] = None
) -> Union[str, bool]:
    """
    转换 PDF 文件中的文本内容并输出新的 PDF 文件。

    由于 PDF 的文本与字体深度绑定（嵌入式子集字体无法容纳转换后的新字符），
    本模块采用“提取 + 按原版式重建”策略：
    - 按原文位置、字号、颜色重排转换后的文字
    - 保留页面尺寸、图片、矢量线条与矩形
    - 无文本层的扫描页按原图栅格化保留

    参数
    ----------
    input_path : str
        源 PDF 文件路径
    output_folder : str
        输出文件夹路径
    conversion_type : str
        OpenCC 转换类型配置名称，如 's2t', 't2s' 等
    log_callback : callable or None
        日志回调函数，接收字符串参数
    is_cancelled_callback : callable or None
        取消检查回调，返回 True 表示用户请求取消

    返回
    -------
    str or bool
        成功时返回输出文件路径，失败时返回 False
    """
    def log(msg: str) -> None:
        if log_callback:
            log_callback(msg)

    # --- 参数校验 ---
    if not os.path.isfile(input_path):
        log(f"错误：文件不存在 - {input_path}")
        return False

    if input_path.lower().endswith('.pdf'):
        log(f"正在处理 PDF 文件: {os.path.basename(input_path)}")
    else:
        log(f"警告：文件后缀不是 .pdf，将尝试以 PDF 格式打开: {os.path.basename(input_path)}")

    # --- 创建输出目录 ---
    try:
        os.makedirs(output_folder, exist_ok=True)
    except OSError as e:
        log(f"错误：无法创建输出目录 - {e}")
        return False

    # --- 取消检查 ---
    if is_cancelled_callback and is_cancelled_callback():
        return False

    # --- 初始化 OpenCC ---
    try:
        cc = OpenCC(conversion_type)
    except Exception as e:
        log(f"错误：OpenCC 初始化失败 ({conversion_type}) - {e}")
        return False

    # --- 查找输出用字体 ---
    font_regular = _find_first_loadable_font(_CJK_FONT_REGULAR_CANDIDATES, log)
    if not font_regular:
        log("错误：系统中未找到可用的中文字体（SimHei/微软雅黑/Noto CJK 等），无法生成中文 PDF")
        return False
    font_bold = _find_first_loadable_font(_CJK_FONT_BOLD_CANDIDATES, log)
    latin_sans = _find_first_loadable_font(_LATIN_SANS_CANDIDATES, log)
    latin_sans_bold = _find_first_loadable_font(_LATIN_SANS_BOLD_CANDIDATES, log)
    latin_serif = _find_first_loadable_font(_LATIN_SERIF_CANDIDATES, log)
    latin_serif_bold = _find_first_loadable_font(_LATIN_SERIF_BOLD_CANDIDATES, log)

    font_paths = {
        'cjk': font_regular,
        'cjk_bold': font_bold or font_regular,
        'latin_sans': latin_sans or font_regular,
        'latin_sans_bold': latin_sans_bold or latin_sans or font_regular,
        'latin_serif': latin_serif or latin_sans or font_regular,
        'latin_serif_bold': latin_serif_bold or latin_serif or latin_sans_bold
                            or latin_sans or font_regular,
    }
    log(f"输出中文字体: {os.path.basename(font_regular)}"
        + (f"（粗体: {os.path.basename(font_bold)}）" if font_bold else "（未找到粗体字体，粗体文字将以常规字体渲染）"))
    if latin_sans:
        latin_desc = os.path.basename(latin_serif) if latin_serif else os.path.basename(latin_sans)
        log(f"输出西文字体: {latin_desc}")
    else:
        log("警告：系统中未找到拉丁字体（Arial/Times 等），西文将使用中文字体渲染，可能与原文观感有差异")

    # --- 打开 PDF ---
    try:
        doc = PdfDocument(input_path)
    except Exception as e:
        msg = str(e)
        log(f"错误：无法读取 PDF 文件 - {msg}")
        if 'password' in msg.lower() or 'encrypt' in msg.lower():
            log("提示：该文件已加密，本工具暂不支持带密码的 PDF")
        elif 'head' in msg.lower() or 'EOF' in msg or 'format' in msg.lower():
            log("提示：该文件可能不是有效的 PDF 文件")
        return False

    try:
        total_pages = int(doc.page_count)
        if total_pages <= 0:
            log("错误：PDF 中没有任何页面")
            return False

        # --- 预检文本层：全部为扫描页时无法转换 ---
        text_pages = sum(1 for i in range(total_pages) if doc.has_text_layer(i))
        if text_pages == 0:
            log("错误：该 PDF 没有可提取的文本层（可能是扫描或纯图片 PDF），无法进行文字转换")
            log("提示：如需转换扫描件，请先使用 OCR 工具识别文字后再尝试")
            return False
        if text_pages < total_pages:
            log(f"警告：{total_pages - text_pages}/{total_pages} 页没有文本层（扫描页），这些页面将按原样栅格化保留")

        # --- 初始化输出文档 ---
        builder = DocumentBuilder().title(f"convert_{os.path.splitext(os.path.basename(input_path))[0]}")

        # 实例化逻辑字体表；同一字体文件只注册一次，多个逻辑名共享注册名
        fonts = {}
        registered_by_path = {}
        for key, default_name in _DEFAULT_FONT_NAMES.items():
            path = font_paths[key]
            if path not in registered_by_path:
                try:
                    builder = builder.register_embedded_font(default_name, EmbeddedFont.from_file(path))
                    registered_by_path[path] = default_name
                except Exception as e:
                    log(f"警告：字体 {os.path.basename(path)} 注册失败（{e}），相关文字将使用中文字体渲染")
                    fonts[key] = {'name': _DEFAULT_FONT_NAMES['cjk'], 'path': font_paths['cjk']}
                    continue
            fonts[key] = {'name': registered_by_path[path], 'path': path}

        converted_spans = 0
        warned_rotation = False

        for page_index in range(total_pages):
            if is_cancelled_callback and is_cancelled_callback():
                log("转换已被取消")
                return False

            log(f"  [{page_index + 1}/{total_pages}] 处理第 {page_index + 1} 页")

            # 裁剪框决定可见区域，输出页面以它为基准
            try:
                cx0, cy0, cx1, cy1 = doc.page_crop_box(page_index)
            except Exception:
                cx0, cy0, cx1, cy1 = doc.page_media_box(page_index)
            page_w, page_h = cx1 - cx0, cy1 - cy0
            if page_w <= 0 or page_h <= 0:
                mb = doc.page_media_box(page_index)
                cx0, cy0 = mb[0], mb[1]
                page_w, page_h = mb[2] - mb[0], mb[3] - mb[1]

            rotation = doc.page_rotation(page_index)
            if rotation and not warned_rotation:
                log(f"  ⚠ 第{page_index + 1}页设置了页面旋转（{rotation}°），该页输出方向可能与原文不同")
                warned_rotation = True

            page_builder = builder.page(page_w, page_h)

            # --- 无文本层的扫描页：整页栅格化保留 ---
            if not doc.has_text_layer(page_index):
                png = _rasterize_page_png(doc, page_index)
                if png:
                    page_builder.image_with_alt(png, 0.0, 0.0, page_w, page_h, "")
                else:
                    log(f"  ⚠ 第{page_index + 1}页栅格化失败，输出为空白页")
                builder = page_builder.done()
                continue

            # --- 图片（先画，位于文字下层） ---
            try:
                _draw_images(page_builder, doc, page_index, cx0, cy0, log)
            except Exception as e:
                log(f"  ⚠ 第{page_index + 1}页图片保留失败: {e}")

            # --- 矢量线条与矩形 ---
            try:
                _draw_lines(page_builder, doc.extract_lines(page_index) or [], cx0, cy0)
                _draw_rects(page_builder, doc.extract_rects(page_index) or [], cx0, cy0)
            except Exception as e:
                log(f"  ⚠ 第{page_index + 1}页矢量图形保留失败: {e}")

            # --- 文本：逐 span 转换并按原位置重排 ---
            try:
                spans = doc.extract_spans(page_index)
            except Exception as e:
                log(f"  ⚠ 第{page_index + 1}页文本提取失败: {e}")
                spans = []

            for span in spans:
                if _draw_span_text(page_builder, cc, span, fonts, cx0, cy0):
                    converted_spans += 1

            builder = page_builder.done()

        # --- 取消检查 ---
        if is_cancelled_callback and is_cancelled_callback():
            return False

        # --- 写出文件 ---
        output_filename = f"convert_{os.path.basename(input_path)}"
        output_path = os.path.join(output_folder, output_filename)
        if not output_path.lower().endswith('.pdf'):
            output_path += '.pdf'

        try:
            builder.save(output_path)
        except Exception as e:
            log(f"错误：写出 PDF 文件失败 - {e}")
            return False

        log(f"已保存: {output_path}")
        log(f"PDF 转换完成：共 {total_pages} 页，转换 {converted_spans} 个文本片段")
        return output_path
    finally:
        try:
            doc.close() if hasattr(doc, 'close') else None
        except Exception:
            pass
