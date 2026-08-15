"""
自定义转换表模块。

实现原理（与 OpenCC 官方文档的「内聯字典（inline dictionary）」一致）：
基于当前转换类型所用的 OpenCC 配置 JSON（如 s2t.json），在其转换链第一个
步骤的词典组最前面动态插入一个 inline 字典，使自定义规则以最高优先级生效，
无需修改任何内置配置或字典文件。
"""

import json
import os
import tempfile

import opencc as _opencc

# 自定义规则的分隔符（按优先级匹配，遇到多个时取最靠前的一个）
_SEPARATORS = ('→', '=>', '->', '\t', '=')


def get_opencc_share_dir():
    """定位 opencc 包内置的配置与词典目录"""
    share_dir = os.path.join(os.path.dirname(os.path.abspath(_opencc.__file__)),
                             'clib', 'share', 'opencc')
    if not os.path.isdir(share_dir):
        raise RuntimeError(f"未找到 OpenCC 数据目录: {share_dir}")
    return share_dir


def parse_custom_entries(text):
    """
    解析用户输入的自定义转换规则文本。

    每一行一条规则，格式为「原词→目标词」（也支持 =、=>、-> 或 Tab 分隔）；
    以 # 或 // 开头的行视为注释，空行自动忽略。
    返回 {原词: 目标词} 字典；格式非法时抛出 ValueError（含具体行号）。

    与 OpenCC 内联字典的限制一致：key/value 必须为非空字符串，
    重复 key 不受支持（会导致加载失败），因此在这里提前校验并给出友好提示。
    """
    entries = {}
    seen = {}
    # 去掉可能的 BOM
    text = text.lstrip('\ufeff')

    for line_no, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith('#') or line.startswith('//'):
            continue

        # 取所有分隔符中位置最靠前的一个；同一位置时按 _SEPARATORS 优先级
        # （如 => 优先于 =），避免把 => 拆成 = 导致目标词多出一个 > 号
        best = None
        for sep in _SEPARATORS:
            idx = line.find(sep)
            if idx != -1 and (best is None or idx < best[0]):
                best = (idx, sep)
        if best is None:
            raise ValueError(f"第 {line_no} 行缺少分隔符，请使用 →、=、=> 或 Tab 分隔")

        idx, sep = best
        key = line[:idx].strip()
        value = line[idx + len(sep):].strip()

        if not key or not value:
            raise ValueError(f"第 {line_no} 行的原词或目标词不能为空")

        if key in seen:
            raise ValueError(f"原词“{key}”重复（第 {seen[key]} 行与第 {line_no} 行），"
                             f"内联字典不支持重复 key")

        seen[key] = line_no
        entries[key] = value

    return entries


def _absolutize_dict_paths(node, base_dir):
    """递归将配置中所有 dict.file 相对路径改写为绝对路径"""
    if isinstance(node, dict):
        if isinstance(node.get('file'), str) and not os.path.isabs(node['file']):
            node['file'] = os.path.join(base_dir, node['file'])
        for value in node.values():
            _absolutize_dict_paths(value, base_dir)
    elif isinstance(node, list):
        for item in node:
            _absolutize_dict_paths(item, base_dir)


def build_custom_config_file(base_config_name, entries):
    """
    基于指定的 OpenCC 配置（如 s2t、s2t_jieba）生成一份新的配置 JSON：
    在转换链第一个步骤的词典组最前面插入内联自定义词典，并把配置中所有
    内置词典路径改写为绝对路径，使生成的配置文件可以放在任意目录加载。
    返回生成的临时配置文件路径，使用完毕后应由调用方删除。
    """
    share_dir = get_opencc_share_dir()
    config_path = os.path.join(share_dir, base_config_name + '.json')
    if not os.path.isfile(config_path):
        raise RuntimeError(f"未找到转换配置 {base_config_name}.json（{config_path}）")

    with open(config_path, encoding='utf-8') as f:
        config = json.load(f)

    _absolutize_dict_paths(config, share_dir)

    # 结巴分词资源路径（若配置带有 segmentation 段），同样改写为绝对路径
    segmentation = config.get('segmentation')
    if isinstance(segmentation, dict):
        resources = segmentation.get('resources')
        if isinstance(resources, dict):
            for key, value in resources.items():
                if isinstance(value, str) and not os.path.isabs(value):
                    resources[key] = os.path.join(share_dir, value)

    # 在转换链第一个步骤的词典组最前面插入内联自定义词典
    chain = config.get('conversion_chain')
    if (not isinstance(chain, list) or not chain
            or not isinstance(chain[0].get('dict'), dict)):
        raise RuntimeError(f"配置 {base_config_name}.json 结构不符合预期，无法加入自定义转换表")
    group = chain[0]['dict']
    if group.get('type') != 'group' or not isinstance(group.get('dicts'), list):
        raise RuntimeError(f"配置 {base_config_name}.json 结构不符合预期，无法加入自定义转换表")
    group['dicts'].insert(0, {"type": "inline", "entries": entries})

    fd, tmp_path = tempfile.mkstemp(prefix='opencc_custom_', suffix='.json')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    return tmp_path
