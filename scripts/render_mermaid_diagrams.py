#!/usr/bin/env python3
"""
渲染 V2_ARCHITECTURE.md 中的 Mermaid 流程图为图片

使用 Mermaid Ink API 将 Mermaid 代码转换为 PNG 图片
"""

import re
import base64
import urllib.parse
import urllib.request
import os
from pathlib import Path

def extract_mermaid_blocks(md_file):
    """从 Markdown 文件中提取所有 Mermaid 代码块"""
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 匹配 ```mermaid ... ``` 代码块
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
    """根据图表内容生成有意义的文件名"""
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

def render_mermaid_to_png(mermaid_code, output_file):
    """使用 Mermaid Ink API 渲染图表为 PNG"""
    
    # 编码 Mermaid 代码
    encoded = base64.urlsafe_b64encode(mermaid_code.encode('utf-8')).decode('ascii')
    
    # Mermaid Ink API URL
    # 使用更高质量的 SVG 然后转换
    url = f'https://mermaid.ink/img/{encoded}?type=png'
    
    print(f"正在渲染: {output_file}")
    print(f"API URL: {url[:100]}...")
    
    try:
        # 下载图片
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=30) as response:
            image_data = response.read()
        
        # 保存图片
        with open(output_file, 'wb') as f:
            f.write(image_data)
        
        print(f"✅ 成功保存: {output_file}")
        return True
        
    except Exception as e:
        print(f"❌ 渲染失败: {e}")
        return False

def render_mermaid_to_svg(mermaid_code, output_file):
    """使用 Mermaid Ink API 渲染图表为 SVG（更清晰）"""
    
    # 编码 Mermaid 代码
    encoded = base64.urlsafe_b64encode(mermaid_code.encode('utf-8')).decode('ascii')
    
    # SVG 格式的 URL
    url = f'https://mermaid.ink/svg/{encoded}'
    
    print(f"正在渲染 SVG: {output_file}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=30) as response:
            svg_data = response.read()
        
        with open(output_file, 'wb') as f:
            f.write(svg_data)
        
        print(f"✅ 成功保存 SVG: {output_file}")
        return True
        
    except Exception as e:
        print(f"❌ SVG 渲染失败: {e}")
        return False

def update_markdown_with_images(md_file, diagram_names, image_dir):
    """更新 Markdown 文件，将 Mermaid 代码块替换为图片引用"""
    
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 为每个图表生成替换文本
    for i, name in enumerate(diagram_names, 1):
        # 匹配第 i 个 mermaid 代码块
        pattern = r'```mermaid\n(.*?)```'
        
        # 构造图片引用（支持 PNG 和 SVG）
        png_path = f'{image_dir}/{name}.png'
        svg_path = f'{image_dir}/{name}.svg'
        
        # 如果 SVG 存在，优先使用 SVG
        if os.path.exists(svg_path):
            replacement = f'![{name}]({image_dir}/{name}.svg)'
        else:
            replacement = f'![{name}]({image_dir}/{name}.png)'
        
        # 只替换第一个匹配（逐个处理）
        content = re.sub(pattern, replacement, content, count=1, flags=re.DOTALL)
    
    # 保存更新后的文件
    backup_file = md_file + '.backup'
    print(f"\n备份原文件到: {backup_file}")
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 注意：这里先不直接覆盖，让用户检查后再决定
    output_file = md_file.replace('.md', '_with_images.md')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 生成新文件: {output_file}")
    print(f"   （请检查后，如果满意可以替换原文件）")

def main():
    """主函数"""
    
    # 项目根目录
    project_root = Path(__file__).parent.parent
    md_file = project_root / 'V2_ARCHITECTURE.md'
    
    # 创建图片目录
    image_dir = project_root / 'images'
    image_dir.mkdir(exist_ok=True)
    
    print("="*80)
    print("V2 架构流程图渲染工具")
    print("="*80)
    print(f"文档路径: {md_file}")
    print(f"图片目录: {image_dir}")
    print()
    
    # 1. 提取 Mermaid 代码块
    print("步骤 1: 提取 Mermaid 代码块...")
    diagrams = extract_mermaid_blocks(md_file)
    print(f"找到 {len(diagrams)} 个图表")
    print()
    
    # 2. 生成文件名
    diagram_names = generate_diagram_names(diagrams)
    
    # 3. 渲染每个图表
    print("步骤 2: 渲染图表...")
    success_count = 0
    
    for diagram, name in zip(diagrams, diagram_names):
        print(f"\n图表 {diagram['index']}: {name}")
        print("-" * 60)
        
        # 渲染为 PNG
        png_file = image_dir / f'{name}.png'
        if render_mermaid_to_png(diagram['code'], png_file):
            success_count += 1
        
        # 同时渲染为 SVG（矢量图，更清晰）
        svg_file = image_dir / f'{name}.svg'
        render_mermaid_to_svg(diagram['code'], svg_file)
    
    print()
    print("="*80)
    print(f"渲染完成: {success_count}/{len(diagrams)} 个图表成功")
    print("="*80)
    
    # 4. 询问是否更新 Markdown 文件
    print("\n生成的图片文件：")
    for name in diagram_names:
        png_file = image_dir / f'{name}.png'
        svg_file = image_dir / f'{name}.svg'
        if png_file.exists():
            print(f"  - {png_file} ({png_file.stat().st_size / 1024:.1f} KB)")
        if svg_file.exists():
            print(f"  - {svg_file} ({svg_file.stat().st_size / 1024:.1f} KB)")
    
    print("\n是否更新 Markdown 文档，将 Mermaid 代码替换为图片引用？")
    print("（会先创建备份文件）")
    response = input("输入 'y' 确认，其他键跳过: ").strip().lower()
    
    if response == 'y':
        update_markdown_with_images(md_file, diagram_names, 'images')
    else:
        print("跳过文档更新")
    
    print("\n✅ 所有操作完成！")
    print(f"   图片已保存到: {image_dir}")

if __name__ == '__main__':
    main()
