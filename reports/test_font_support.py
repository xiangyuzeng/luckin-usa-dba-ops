#!/usr/bin/env python3
"""
Test script to check STSong-Light font support for insights text
测试STSong-Light字体对洞察文字的支持
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.units import mm

def main():
    print("=== 测试STSong-Light字体支持 ===")

    try:
        # 注册STSong-Light字体
        print("注册STSong-Light字体...")
        pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
        print("✅ 字体注册成功")

        # 测试文本 - 基于之前的dry run输出
        test_texts = [
            "本周关键洞察",  # 标题 - 应该正常
            "tapere 满意度 66.7%",  # RED洞察
            "33rd & 10th 满意度 96.0%",  # YELLOW洞察1
            "8th & Broadway 满意度 95.5%",  # YELLOW洞察2
            "自有渠道结构稳定",  # GREEN洞察1
            "回头客率 37.3%",  # GREEN洞察2
            "Top 3 商品占比 51.0%",  # GREEN洞察3
            # 其他常见文字
            "建议运营部安排现场巡检，排查出品质量和服务流程",
            "建议关注服务速度",
            "建议持续推进会员积分体系建设",
            "可考虑周末专属促销或社区活动引流"
        ]

        # 创建测试PDF
        print("创建测试PDF...")
        doc = SimpleDocTemplate('test_font_insights.pdf', pagesize=A4,
                              leftMargin=20*mm, rightMargin=20*mm)

        # 创建样式
        styles = getSampleStyleSheet()

        # 标题样式
        title_style = ParagraphStyle(
            'ChineseTitle',
            parent=styles['Heading1'],
            fontName='STSong-Light',
            fontSize=16,
            textColor=colors.black,
            alignment=1  # 居中
        )

        # 洞察样式 - RED
        red_style = ParagraphStyle(
            'ChineseRed',
            parent=styles['Normal'],
            fontName='STSong-Light',
            fontSize=12,
            textColor=colors.black,
            backColor=colors.Color(1, 0.92, 0.92),  # 浅红色背景
            leftIndent=10*mm,
            rightIndent=10*mm,
            spaceAfter=6
        )

        # 洞察样式 - YELLOW
        yellow_style = ParagraphStyle(
            'ChineseYellow',
            parent=styles['Normal'],
            fontName='STSong-Light',
            fontSize=12,
            textColor=colors.black,
            backColor=colors.Color(1, 0.97, 0.88),  # 浅黄色背景
            leftIndent=10*mm,
            rightIndent=10*mm,
            spaceAfter=6
        )

        # 洞察样式 - GREEN
        green_style = ParagraphStyle(
            'ChineseGreen',
            parent=styles['Normal'],
            fontName='STSong-Light',
            fontSize=12,
            textColor=colors.black,
            backColor=colors.Color(0.92, 0.98, 0.92),  # 浅绿色背景
            leftIndent=10*mm,
            rightIndent=10*mm,
            spaceAfter=6
        )

        # 普通文字样式
        normal_style = ParagraphStyle(
            'ChineseNormal',
            parent=styles['Normal'],
            fontName='STSong-Light',
            fontSize=12,
            textColor=colors.black,
            spaceAfter=6
        )

        # 构建PDF内容
        story = []

        # 标题
        story.append(Paragraph(test_texts[0], title_style))
        story.append(Spacer(1, 12))

        # RED洞察
        story.append(Paragraph(f"🔴 {test_texts[1]}", red_style))

        # YELLOW洞察
        story.append(Paragraph(f"🟡 {test_texts[2]}", yellow_style))
        story.append(Paragraph(f"🟡 {test_texts[3]}", yellow_style))

        # GREEN洞察
        story.append(Paragraph(f"🟢 {test_texts[4]}", green_style))
        story.append(Paragraph(f"🟢 {test_texts[5]}", green_style))
        story.append(Paragraph(f"🟢 {test_texts[6]}", green_style))

        story.append(Spacer(1, 12))
        story.append(Paragraph("其他测试文字:", normal_style))

        # 其他文字测试
        for text in test_texts[7:]:
            story.append(Paragraph(text, normal_style))

        # 生成PDF
        doc.build(story)

        print("✅ 测试PDF生成完成: test_font_insights.pdf")
        print()
        print("请检查PDF文件中的中文显示情况:")
        print("1. '本周关键洞察'标题是否正常")
        print("2. 5行洞察内容(红/黄/绿背景)是否正常")
        print("3. 其他中文文字是否正常")
        print()
        print("如果仍有乱码，问题可能是:")
        print("- STSong-Light字体缺少某些字符")
        print("- PDF查看器字体渲染问题")
        print("- 特定文字编码问题")

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()