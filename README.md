# OpenCC-DocxConverter
基于OpenCC的文本文件繁简转换工具
## 介绍
本工具是基于[OpenCC](https://github.com/BYVoid/OpenCC)、[Python-docx](https://github.com/python-openxml/python-docx)封装的文本文件转换工具，支持中文简、繁体之间词汇级别的转换，同时还支持地域间异体字以及词汇的转换。

本程序所收录的《通用规范汉字表》(2013)标准的繁简转换词典来自[OpenCC-Traditional Chinese to Traditional Chinese (The Chinese Government Standard)](https://github.com/TerryTian-tech/OpenCC-Traditional-Chinese-characters-according-to-Chinese-government-standards)。

## 功能特性
- 支持DOCX文档、TXT文本文件、SRT字幕文件的中文繁、简转换

- 自动检测并转写TXT文件为UTF-8编码，以兼容OpenCC转换（检测基于[Chardet](https://github.com/chardet/chardet)）

- 转换后默认保留DOCX文档格式、排版不变

- 支持批量处理文件转换

- 支持转换DOCX文档中的脚注和尾注文本

## 使用方式
### 1.下载发行版（Windows 10/11）
直接下载[Releases](https://github.com/TerryTian-tech/OpenCC-DocxConverter/releases)中的压缩包，解压并运行。

### 2.从源码运行（Windows/MacOS/Linux）
> [!NOTE]
> 如果需要使用《通用规范汉字表》相关的转换选项，需要下载[OpenCC-Traditional Chinese to Traditional Chinese (The Chinese Government Standard)](https://github.com/TerryTian-tech/OpenCC-Traditional-Chinese-characters-according-to-Chinese-government-standards)的转换词典和json方案文件，并重命名词典文件和json文件，json文件重命名后的具体名称请参看程序源码的调用选项；重命名后放入OpenCC储存转换方案的目录下（先执行pip show opencc命令找到OpenCC包具体所在位置，储存转换方案的位置一般在opencc/clib/share/opencc下，若不是可尝试搜索t2s.json等文件所在位置）。
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