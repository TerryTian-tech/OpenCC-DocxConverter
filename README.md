# OpenCC-DocxConverter
基于OpenCC的DOCX文档和TXT文件的繁简转换工具
## 介绍
本工具是基于[OpenCC](https://github.com/BYVoid/OpenCC)、[Python-docx](https://github.com/python-openxml/python-docx)封装的文本文件转换工具，支持中文简、繁体之间词汇级别的转换，同时还支持地域间异体字以及词汇的转换。
## 功能特性
- 支持DOCX文档、TXT文件的中文繁、简转换

- 自动检测并转写TXT文件为UTF-8编码，以兼容OpenCC转换（基于[Chardet](https://github.com/chardet/chardet)）

- 转换后默认保留DOCX文档格式、排版不变

- 支持批量处理文件转换

- 支持转换DOCX文档中的脚注和尾注文本

## 使用说明
### 1.下载发行版（Windows 10/11）
直接下载[Releases](https://github.com/TerryTian-tech/OpenCC-DocxConverter/releases)中的压缩包，解压并运行。

### 2.从源码编译运行（Windows/MacOS/Linux）
#### 克隆这个仓库
```bash
git clone https://github.com/TerryTian-tech/OpenCC-DocxConverter.git
cd OpenCC-DocxConverter/opencc-docxconverter
```
#### 安装依赖(使用pip)
```bash
pip install -r requirements.txt
```

#### 运行程序
```bash
python main.py