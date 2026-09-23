"""
文字转换（一对多歧义标注）后端模块。

通过 OpenCC 原生命令行工具的 --ambiguities 模式转换文本，并将返回的
NDJSON 流解析为「转换结果 + 歧义跨度」：

- {"def":"文丑"}                        出现一对多映射的原文词（来源词），按首次出现顺序编号
- {"lit":"大戰"}                        无歧义的直出文本段
- {"amb":{"t":"文丑","s":0}}            歧义段：t 为实际采用的转换文本，s 为来源词编号
- {"end":{"output_bytes":45,...}}       结束标记，output_bytes 为全文 UTF-8 字节数

lit 与 amb 按出现顺序拼接即为转换结果全文。
"""

import json
import os
import shutil
import subprocess

import opencc as _opencc


class AmbiguityConversionError(RuntimeError):
    """文字转换失败（CLI 缺失、调用出错或输出不合法）"""


def locate_opencc_cli():
    """
    定位支持 --ambiguities 的 OpenCC 原生命令行工具。

    Python 包自带的 opencc 命令（Scripts/opencc.exe）不支持 --ambiguities，
    因此使用 opencc 包内 clib/bin 下的原生命令行工具。
    :return: 可执行文件路径；找不到返回 None
    """
    exe = "opencc.exe" if os.name == "nt" else "opencc"
    candidate = os.path.join(os.path.dirname(os.path.abspath(_opencc.__file__)),
                             "clib", "bin", exe)
    if os.path.isfile(candidate):
        return candidate
    return shutil.which("opencc")


def parse_ambiguity_stream(data):
    """
    解析 --ambiguities 输出的 NDJSON 流。

    :param data: 原始字节流（UTF-8）
    :return: dict：
        output  —— 转换结果全文（str）
        defs    —— 来源词列表（一对多映射的原文词，按首次出现顺序）
        spans   —— 歧义跨度列表 [{"start", "length", "def_idx"}]，
                   start/length 为 output 中的字符（码点）偏移
        stats   —— end 行的统计信息
    :raises AmbiguityConversionError: 输出行不合法或流不完整
    """
    output_parts = []
    defs = []
    spans = []
    stats = {}

    for raw_line in data.decode("utf-8", errors="strict").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as e:
            raise AmbiguityConversionError(f"无法解析 OpenCC 输出行：{line}（{e}）")

        if "def" in record:
            defs.append(str(record["def"]))
        elif "lit" in record:
            output_parts.append(str(record["lit"]))
        elif "amb" in record:
            amb = record["amb"]
            converted = str(amb["t"])
            def_idx = int(amb["s"])
            if not 0 <= def_idx < len(defs):
                raise AmbiguityConversionError(
                    f"歧义标注引用了不存在的来源词编号：{def_idx}"
                )
            spans.append({
                "start": sum(len(part) for part in output_parts),
                "length": len(converted),
                "def_idx": def_idx,
            })
            output_parts.append(converted)
        elif "end" in record:
            stats = record["end"] or {}
        else:
            raise AmbiguityConversionError(f"未知的 OpenCC 输出行类型：{line}")

    output = "".join(output_parts)
    expected_bytes = stats.get("output_bytes")
    if expected_bytes is not None and expected_bytes != len(output.encode("utf-8")):
        raise AmbiguityConversionError(
            "歧义标注流校验失败（output_bytes 与拼接结果不一致），转换结果可能不完整"
        )

    return {"output": output, "defs": defs, "spans": spans, "stats": stats}


def convert_with_ambiguities(text, config, timeout=60, on_spawn=None):
    """
    调用 OpenCC 原生 CLI 转换文本并解析歧义标注。

    :param text: 待转换文本（建议先将 \\r\\n 统一为 \\n，保证歧义跨度与显示对齐）
    :param config: OpenCC 配置名（如 "s2t.json"）或配置文件绝对路径
    :param timeout: 子进程超时秒数
    :param on_spawn: 子进程启动后的回调（参数为 Popen 对象），可供调用方终止进程
    :raises AmbiguityConversionError: CLI 不可用、执行失败或输出流不完整
    """
    cli = locate_opencc_cli()
    if not cli:
        raise AmbiguityConversionError(
            "未找到 OpenCC 原生命令行工具（opencc/clib/bin/opencc），"
            "无法进行带歧义标注的转换。"
        )

    proc = None
    try:
        proc = subprocess.Popen(
            [cli, "-c", config, "--include-tofu-risk-dictionaries", "--ambiguities"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if on_spawn:
            on_spawn(proc)
        stdout, stderr = proc.communicate(text.encode("utf-8"), timeout=timeout)
    except subprocess.TimeoutExpired:
        if proc:
            proc.kill()
            proc.communicate()
        raise AmbiguityConversionError(f"转换超时（超过 {timeout} 秒）")
    except OSError as e:
        raise AmbiguityConversionError(f"启动 OpenCC 命令行工具失败：{e}")

    if proc.returncode != 0:
        stderr_text = (stderr or b"").decode("utf-8", errors="replace").strip()
        raise AmbiguityConversionError(
            stderr_text or f"OpenCC 命令行工具返回码 {proc.returncode}"
        )

    return parse_ambiguity_stream(stdout)


# 词级候选查询：自 OpenCC 1.4.3（含 dev 构建）起在 opencc.OpenCC 实例上以
# query_candidates(word) -> list[str] 暴露（pybind11 绑定 opencc::GetAllConversions）。
# 旧版（1.4.2 及更早）没有该方法，探测失败后按“不可用”处理。
_CANDIDATE_QUERY_METHOD_NAMES = ("query_candidates",)

# 已缓存的 OpenCC 实例（按配置名），避免每次点击候选都重新加载词典
_candidate_query_converters = {}
# 候选查询缓存：{(config, word): 候选列表 或 None(不可用)}
_candidate_cache = {}


def _get_candidate_query_converter(config):
    """获取用于词级候选查询的 OpenCC 实例；不支持候选查询时返回 None"""
    config_key = os.path.abspath(config) if os.path.isabs(config) else config
    if config_key not in _candidate_query_converters:
        converter = None
        try:
            instance = _opencc.OpenCC(config_key)
            for name in _CANDIDATE_QUERY_METHOD_NAMES:
                method = getattr(instance, name, None)
                if callable(method):
                    converter = (instance, method)
                    break
        except Exception:
            converter = None
        _candidate_query_converters[config_key] = converter
    return _candidate_query_converters[config_key]


def query_candidates(config, word):
    """
    查询原文词在指定配置下的全部候选转换值。

    :param config: OpenCC 配置名或配置文件绝对路径
    :param word: 原文词（歧义标注 def 行给出的来源词）
    :return: 候选值列表；当前安装的 OpenCC 不支持词级候选查询时返回 None
    """
    config_key = os.path.abspath(config) if os.path.isabs(config) else config
    cache_key = (config_key, word)
    if cache_key in _candidate_cache:
        return _candidate_cache[cache_key]

    result = None
    converter = _get_candidate_query_converter(config_key)
    if converter is not None:
        instance, method = converter
        try:
            values = method(word)
            if isinstance(values, (list, tuple)):
                result = [str(v) for v in values]
        except Exception:
            result = None
    _candidate_cache[cache_key] = result
    return result
