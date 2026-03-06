# OpenCC File Converter 简繁通转换大师 

**简繁通转换大师**是一款功能完善的中文繁简转换软件，基于 [OpenCC](https://github.com/BYVoid/OpenCC) 开源项目开发，支持Word文档（DOCX）、文本文件（TXT）、字幕文件（SRT、ASS/SSA、LRC）的转换。

本工具不仅支持简体与繁体之间的相互转换，也支持陆、台、港三地的繁体标准互相转换，并提供词汇级别的智能转换能力，能够准确处理地域间的异体字和词汇差异。

## 主要特性

### 多格式文件支持

本工具支持多种常见的文本文件格式，满足不同场景下的繁简转换需求：

| 文件格式 | 说明 | 特殊处理 |
|---------|------|---------|
| **DOCX** | Microsoft Word 文档 | 保留原有格式、排版，可选择是否转换页眉页脚、脚注尾注 |
| **TXT** | 纯文本文件 | 自动检测编码并转换为 UTF-8 |
| **SRT** | SubRip 字幕文件 | 保留时间码，支持 ASS/SSA 样式标签 |
| **ASS/SSA** | Advanced SubStation Alpha 字幕 | 保留样式定义，仅转换对话文本 |
| **LRC** | 歌词文件 | 保留时间标签和增强型标签 |

### 丰富的转换标准

程序内置 17 种转换模式，覆盖主流的繁简转换需求：

**基础转换模式：**
- 简体 → 繁体（OpenCC 标准）
- 繁体 → 简体（OpenCC 标准）

**地区标准转换：**
- 简体 ↔ 台湾正体
- 简体 ↔ 香港繁体
- 繁体 ↔ 台湾正体
- 繁体 ↔ 香港繁体

**《通用规范汉字表》标准转换：**
- 简体 ↔ 繁体（《通用规范汉字表》标准）
- 繁体 → 繁体（《通用规范汉字表》标准）

**词汇转换模式：**
- 简体 → 繁体（台湾标准）并转换为台湾常用词汇
- 繁体（台湾标准）→ 简体并转换为中国大陆常用词汇

**日文汉字转换：**
- 繁体（OpenCC 标准，旧字体）↔ 日文新字体

### 核心功能亮点

**智能编码检测：**
- 采用 Chardet 库进行文件编码自动识别
- 特别优化 GB2312、GBK、GB18030 等中文编码的处理
- 支持多种中文编码的智能识别与兼容读取

**文档格式保留：**
- DOCX 文档转换后完整保留原有格式
- 支持字体、颜色、大小、粗体、斜体、下划线等格式属性
- 支持页眉、页脚、表格等复杂文档元素
- 可选转换脚注和尾注内容

**字幕文件智能处理：**
- SRT 字幕：保留序号和时间码，仅转换字幕文本
- ASS/SSA 字幕：保留样式标签 `{...}`，只转换显示文本
- LRC 歌词：保留时间标签 `[mm:ss.xx]` 和增强型标签 `<xx>`

**批量处理能力：**
- 支持文件夹级别的批量转换
- 自动识别文件夹内所有支持的文件格式
- 实时显示处理进度和转换日志


## 安装与运行

### 方式一：下载发行版（ Windows 10/11 ）

直接从 [Releases](https://github.com/TerryTian-tech/OpenCC-DocxConverter/releases) 页面下载对应平台的压缩包，解压后即可运行，无需配置 Python 环境。

### 方式二：从源码运行

#### 1. 克隆仓库

```bash
git clone https://github.com/TerryTian-tech/OpenCC-DocxConverter.git
cd OpenCC-DocxConverter/opencc-docxconverter
```

#### 2. 安装依赖

```bash
pip install -r requirements.txt
```

#### 3. 运行程序

```bash
python main.py
```

#### 从源码运行时如何获取《通用规范汉字表》标准转换支持

从源码直接运行本软件时，如需使用《通用规范汉字表》相关的转换选项，请完成以下额外配置：

1. 下载 [OpenCC-Traditional Chinese to Traditional Chinese (The Chinese Government Standard)](https://github.com/TerryTian-tech/OpenCC-Traditional-Chinese-characters-according-to-Chinese-government-standards) 项目中的转换词典和 JSON 方案文件

2. 将词典文件和 JSON 文件重命名（具体名称请参考源码中的调用选项）

3. 将文件放入 OpenCC 的转换方案目录：
   ```bash
   # 查找 OpenCC 安装位置
   pip show opencc
   
   # 方案文件通常位于：
   # opencc/clib/share/opencc/
   ```

## 项目结构

```
OpenCC-DocxConverter/
├── main.py              # 主程序入口
├── requirements.txt     # Python 依赖列表
├── logo.ico             # 程序图标
└── README.md            # 项目说明文档
```

## 技术栈

| 组件 | 版本 | 说明 |
|-----|------|-----|
| [OpenCC](https://github.com/BYVoid/OpenCC) | 1.2.0 | 开源中文繁简转换库 |
| [Python-docx](https://github.com/python-openxml/python-docx) | 1.2.0 | Word 文档处理库 |
| [PySide6](https://www.qt.io/qt-for-python) | - | Qt for Python GUI 框架 |
| [Chardet](https://github.com/chardet/chardet) | - | 字符编码检测库 |
| [OpenCC-Traditional Chinese to Traditional Chinese (The Chinese Government Standard)](https://github.com/TerryTian-tech/OpenCC-Traditional-Chinese-characters-according-to-Chinese-government-standards)| - | 《通用规范汉字表》标准转换词典|

## 隐私与安全

- **本地处理**：所有文件转换均在本地完成，不会上传至任何服务器，保障您的数据安全
- **无网络依赖**：核心功能完全离线可用（更新检查除外）
- **开源透明**：完整源代码公开，可供安全审计

## 开源协议

Apache-2.0 LICENSE
