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

**结巴分词预处理：**
- 支持转换前使用结巴分词进行分词预处理，提高准确度
- 转换后清除分词标记
- 结巴分词预置繁体中文和自定义词典

## 安装与运行

### 方式一：下载发行版（ Windows 10/11 ）

直接从 [Releases](https://github.com/TerryTian-tech/OpenCC-DocxConverter/releases) 页面下载对应平台的压缩包，解压后即可运行，无需配置 Python 环境。

### 方式二：从源码运行（ Windows/Linux/MacOS ）

在 Windows 系统上，使用者需预先部署 Python 运行环境。然后打开终端（PowerShell），执行以下命令安装依赖并运行：

```bash
git clone https://github.com/TerryTian-tech/OpenCC-DocxConverter.git
cd OpenCC-DocxConverter/opencc-docxconverter
pip install -r requirements.txt
Copy-Item -Path "..\dict\*" -Destination "$(python -c "import opencc, os; print(os.path.join(os.path.dirname(opencc.__file__), 'clib', 'share', 'opencc'))")" -Recurse -Force
Copy-Item -Path "..\jieba\*" -Destination "$(python -c 'import jieba, os; print(os.path.dirname(jieba.__file__))')" -Recurse -Force
python main.py
```

在 Linux 发行版和 Mac 下，使用者需预先部署 Python 运行环境，然后打开终端，执行以下命令安装依赖并运行：

```bash
git clone https://github.com/TerryTian-tech/OpenCC-DocxConverter.git
cd OpenCC-DocxConverter/opencc-docxconverter
pip install -r requirements.txt
cp -rf ../dict/* "$(python3 -c "import opencc, os; print(os.path.join(os.path.dirname(opencc.__file__), 'clib', 'share', 'opencc'))")"
cp -rf ../jieba/* "$(python3 -c "import jieba, os; print(os.path.dirname(jieba.__file__))")"
python3 main.py
```

## 项目结构

```
OpenCC-DocxConverter/
├── opencc-docxconverter/     # 主程序目录
│   ├── main.py               # 主程序入口，GUI界面与程序逻辑
│   ├── doc_converter.py      # Word文档(DOCX)转换模块
│   ├── text_converter.py     # 文本文件(TXT/SRT/ASS/SSA/LRC)转换模块
│   ├── updater.py            # 更新检查模块
│   ├── constants.py          # 版本常量
│   ├── requirements.txt      # Python 依赖列表
│   └── logo.ico              # 程序图标
├── dict/                     # 转换词典目录
├── jieba/                    # 结巴分词词典目录
└── README.md                 # 项目说明文档
```

## 技术栈

| 组件 | 版本 | 说明 |
|-----|------|-----|
| [OpenCC](https://github.com/BYVoid/OpenCC) | 1.2.0 | 开源中文繁简转换库 |
| [Python-docx](https://github.com/python-openxml/python-docx) | 1.2.0 | Word 文档处理库 |
| [PySide6](https://www.qt.io/qt-for-python) | 6.11.0 | Qt for Python GUI 框架 |
| [Chardet](https://github.com/chardet/chardet) | 7.4.0 | 字符编码检测库 |
| [Jieba](https://github.com/fxsjy/jieba) | 1.2.0 | 结巴分词库 |
| [OpenCC-Traditional Chinese to Traditional Chinese (The Chinese Government Standard)](https://github.com/TerryTian-tech/OpenCC-Traditional-Chinese-characters-according-to-Chinese-government-standards)| 1.3.0 | 《通用规范汉字表》标准转换词典|

## 隐私与安全

- **本地处理**：所有文件转换均在本地完成，不会上传至任何服务器，保障您的数据安全
- **无网络依赖**：核心功能完全离线可用（更新检查除外）
- **开源透明**：完整源代码公开，可供安全审计

## 开源协议

Apache-2.0 LICENSE

位于本仓库jieba目录下的结巴分词词典，默认词典dict.txt来自[结巴分词仓库](https://github.com/fxsjy/jieba)，自定义词典使用了[gumblex](https://github.com/gumblex)制作的[jiebazhc](https://github.com/The-Orizon/nlputils)和来自[hanzi-words](https://github.com/zispace/hanzi-words)的古汉语词汇数据。jieba目录下的所有文件中属于开源贡献者制作的部分均遵循MIT License。
