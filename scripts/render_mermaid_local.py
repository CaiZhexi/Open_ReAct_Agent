#!/usr/bin/env python3
"""
渲染 Mermaid 流程图为图片 - 本地方法

方法：生成 HTML 文件，使用浏览器打开后手动截图，
或者安装 mermaid-cli 工具自动渲染
"""

import re
import os
from pathlib import Path

def extract_mermaid_blocks(md_file):
    """从 Markdown 文件中提取所有 Mermaid 代码块"""
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    pattern = r'```mermaid\n(.*?)```'
    matches = re.findall(pattern, content, re.DOTALL)
    
    diagrams = []
    for i, match in enumerate(matches, 1):
        diagrams.append({
            'index': i,
            'code': match.strip()
        })
    
    return diagrams

def generate_diagram_names(diagrams):
    """根据图表内容生成文件名"""
    names = []
    for diagram in diagrams:
        code = diagram['code']
        if 'graph TD' in code and 'Start[开始]' in code:
            names.append('v2_overall_flow')
        elif 'sequenceDiagram' in code:
            names.append('v2_iteration_sequence')
        elif 'graph TD' in code and '多个问题' in code:
            names.append('v2_multi_task_decompose')
        else:
            names.append(f'diagram_{diagram["index"]}')
    return names

def create_html_viewer(diagrams, diagram_names, output_dir):
    """创建 HTML 文件用于查看和截图"""
    
    html_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>V2 架构流程图</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 40px 20px;
            background: #f5f5f5;
        }
        .diagram-container {
            background: white;
            margin: 40px 0;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .diagram-title {
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 20px;
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }
        .diagram-subtitle {
            font-size: 14px;
            color: #666;
            margin-bottom: 30px;
        }
        .mermaid {
            display: flex;
            justify-content: center;
            background: white;
        }
        .instructions {
            background: #e3f2fd;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            border-left: 4px solid #2196F3;
        }
        .instructions h2 {
            margin-top: 0;
            color: #1976D2;
        }
        .instructions ol {
            margin: 10px 0;
            padding-left: 20px;
        }
        .instructions li {
            margin: 8px 0;
            line-height: 1.6;
        }
        .instructions code {
            background: #fff;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 13px;
        }
    </style>
</head>
<body>
    <div class="instructions">
        <h2>📸 截图说明</h2>
        <p><strong>方法一：手动截图（推荐）</strong></p>
        <ol>
            <li>滚动到要截图的流程图</li>
            <li>macOS: 按 <code>Cmd + Shift + 4</code>，然后按空格键，点击流程图区域</li>
            <li>Windows: 使用截图工具或 <code>Win + Shift + S</code></li>
            <li>将截图保存到 <code>images/</code> 目录，命名如下：
                <ul>
                    <li><code>v2_overall_flow.png</code> - 总体流程图</li>
                    <li><code>v2_iteration_sequence.png</code> - 迭代序列图</li>
                    <li><code>v2_multi_task_decompose.png</code> - 多任务分解图</li>
                </ul>
            </li>
        </ol>
        
        <p><strong>方法二：使用命令行工具（自动）</strong></p>
        <ol>
            <li>安装 mermaid-cli: <code>npm install -g @mermaid-js/mermaid-cli</code></li>
            <li>运行渲染脚本: <code>python scripts/render_with_mmdc.py</code></li>
        </ol>
    </div>
"""
    
    # 添加每个图表
    titles = {
        'v2_overall_flow': '总体流程图',
        'v2_iteration_sequence': '详细迭代序列图',
        'v2_multi_task_decompose': '多任务分解流程图'
    }
    
    for diagram, name in zip(diagrams, diagram_names):
        title = titles.get(name, f'流程图 {diagram["index"]}')
        html_content += f"""
    <div class="diagram-container" id="{name}">
        <div class="diagram-title">{title}</div>
        <div class="diagram-subtitle">保存为: images/{name}.png</div>
        <div class="mermaid">
{diagram['code']}
        </div>
    </div>
"""
    
    html_content += """
    <script>
        mermaid.initialize({ 
            startOnLoad: true,
            theme: 'default',
            flowchart: {
                useMaxWidth: true,
                htmlLabels: true,
                curve: 'basis'
            },
            sequence: {
                diagramMarginX: 50,
                diagramMarginY: 10,
                actorMargin: 50,
                width: 150,
                height: 65,
                boxMargin: 10,
                boxTextMargin: 5,
                noteMargin: 10,
                messageMargin: 35,
                mirrorActors: true
            }
        });
    </script>
</body>
</html>
"""
    
    output_file = output_dir / 'mermaid_diagrams.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return output_file

def create_mmdc_script(diagrams, diagram_names, output_dir):
    """创建使用 mermaid-cli (mmdc) 的脚本"""
    
    # 为每个图表创建单独的 .mmd 文件
    mmd_files = []
    for diagram, name in zip(diagrams, diagram_names):
        mmd_file = output_dir / f'{name}.mmd'
        with open(mmd_file, 'w', encoding='utf-8') as f:
            f.write(diagram['code'])
        mmd_files.append((mmd_file, name))
    
    # 创建 shell 脚本
    script_content = """#!/bin/bash
# 使用 mermaid-cli 渲染流程图
# 需要先安装: npm install -g @mermaid-js/mermaid-cli

cd "$(dirname "$0")/.."

echo "检查 mmdc 是否已安装..."
if ! command -v mmdc &> /dev/null; then
    echo "❌ mmdc 未安装"
    echo "请运行: npm install -g @mermaid-js/mermaid-cli"
    exit 1
fi

echo "✅ mmdc 已安装"
echo ""

mkdir -p images

"""
    
    for mmd_file, name in mmd_files:
        script_content += f"""
echo "渲染: {name}"
mmdc -i "images/{name}.mmd" -o "images/{name}.png" -b white -w 1400 -H 1000
mmdc -i "images/{name}.mmd" -o "images/{name}.svg" -b white
"""
    
    script_content += """
echo ""
echo "✅ 所有图表渲染完成！"
echo "图片已保存到 images/ 目录"
"""
    
    script_file = output_dir.parent / 'render_diagrams.sh'
    with open(script_file, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    # 添加执行权限
    os.chmod(script_file, 0o755)
    
    return script_file

def main():
    """主函数"""
    
    project_root = Path(__file__).parent.parent
    md_file = project_root / 'V2_ARCHITECTURE.md'
    image_dir = project_root / 'images'
    image_dir.mkdir(exist_ok=True)
    
    print("="*80)
    print("V2 架构流程图渲染工具（本地版本）")
    print("="*80)
    print(f"文档路径: {md_file}")
    print(f"图片目录: {image_dir}")
    print()
    
    # 提取 Mermaid 代码块
    print("步骤 1: 提取 Mermaid 代码块...")
    diagrams = extract_mermaid_blocks(md_file)
    print(f"找到 {len(diagrams)} 个图表")
    print()
    
    # 生成文件名
    diagram_names = generate_diagram_names(diagrams)
    print("图表列表:")
    for name in diagram_names:
        print(f"  - {name}")
    print()
    
    # 创建 HTML 查看器
    print("步骤 2: 创建 HTML 查看器...")
    html_file = create_html_viewer(diagrams, diagram_names, image_dir)
    print(f"✅ HTML 文件: {html_file}")
    print()
    
    # 创建自动渲染脚本
    print("步骤 3: 创建自动渲染脚本...")
    script_file = create_mmdc_script(diagrams, diagram_names, image_dir)
    print(f"✅ Shell 脚本: {script_file}")
    print()
    
    print("="*80)
    print("完成！请选择以下方法之一：")
    print("="*80)
    print()
    print("方法 1：手动截图（推荐）")
    print(f"  1. 在浏览器中打开: {html_file}")
    print(f"  2. 截图并保存到 images/ 目录")
    print()
    print("方法 2：自动渲染（需要 Node.js）")
    print(f"  1. 安装 mermaid-cli: npm install -g @mermaid-js/mermaid-cli")
    print(f"  2. 运行脚本: bash {script_file}")
    print()
    
    # 尝试自动打开浏览器
    try:
        import webbrowser
        print("正在打开浏览器...")
        webbrowser.open(f'file://{html_file.absolute()}')
        print("✅ 浏览器已打开")
    except:
        print("⚠️  无法自动打开浏览器，请手动打开上述 HTML 文件")

if __name__ == '__main__':
    main()
