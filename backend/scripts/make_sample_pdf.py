"""Generate samples/daleel-sample-guide.pdf: a fictional student guide used for demos and tests.

The university and every rule in it are invented. The file is committed, so this script is only
needed to change its content. It needs a font with Arabic glyphs (DejaVu Sans by default):

    uv run python -m scripts.make_sample_pdf --font-dir /usr/share/fonts/truetype/dejavu
"""

import argparse
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "samples" / "daleel-sample-guide.pdf"

# One entry per page: (direction, heading, paragraphs). Plain text only: no diacritics, so the
# extracted text is predictable for tests.
PAGES: list[tuple[str, str, list[str]]] = [
    (
        "rtl",
        "دليل الطالب - جامعة الساحل - نموذج تجريبي",
        [
            "هذا الدليل نموذج تجريبي لجامعة غير حقيقية، أعد لاختبار منصة دليل. لا تمثل أي من المواد التالية أنظمة جامعة فعلية.",
            "المادة الأولى - القبول: يقبل الطالب في الجامعة إذا حصل على شهادة الثانوية العامة أو ما يعادلها بنسبة لا تقل عن 85 بالمئة، واجتاز اختبار القدرات العامة.",
            "المادة الثانية - التسجيل: يسجل الطالب مقرراته إلكترونيا قبل بداية الفصل الدراسي بأسبوعين، ولا يجوز أن يقل العبء الدراسي عن 12 ساعة معتمدة أو يزيد على 20 ساعة معتمدة في الفصل الواحد.",
            "المادة الثالثة - البطاقة الجامعية: تصدر البطاقة الجامعية للطالب المستجد خلال الأسبوع الأول من الدراسة، ويتحمل الطالب رسوم بدل الفاقد وقدرها 50 ريالا.",
        ],
    ),
    (
        "rtl",
        "الفصل الثاني: التدريب التعاوني",
        [
            "المادة الرابعة - شروط التسجيل: يشترط لتسجيل مقرر التدريب التعاوني أن يكون الطالب قد أتم 100 ساعة معتمدة على الأقل، وألا يقل معدله التراكمي عن 2.5 من 5.",
            "المادة الخامسة - مدة التدريب: تكون مدة التدريب التعاوني ثمانية أسابيع متصلة في جهة تدريب معتمدة من الكلية، ولا يجوز تقسيم المدة على فصلين.",
            "المادة السادسة - التقييم: يقيم الطالب في التدريب من قبل المشرف في جهة التدريب بنسبة 60 بالمئة، ومن قبل المشرف الأكاديمي بنسبة 40 بالمئة بناء على التقرير النهائي والعرض التقديمي.",
            "المادة السابعة - الاعتذار عن التدريب: يجوز للطالب الاعتذار عن التدريب التعاوني بعذر مقبول قبل بدايته بأسبوعين على الأقل، ويعتمد الاعتذار من وكيل الكلية.",
        ],
    ),
    (
        "rtl",
        "الفصل الثالث: الحضور والاعتذار عن الدراسة",
        [
            "المادة الثامنة - الحضور: يجب على الطالب حضور المحاضرات، ويحرم من دخول الاختبار النهائي إذا تجاوزت نسبة غيابه 25 بالمئة من مجموع المحاضرات دون عذر مقبول.",
            "المادة التاسعة - الاعتذار عن الفصل: يحق للطالب الاعتذار عن الفصل الدراسي كاملا قبل نهاية الأسبوع العاشر من بداية الفصل، ولا يحسب الفصل المعتذر عنه ضمن المدة النظامية للتخرج.",
            "المادة العاشرة - الانسحاب من مقرر: يجوز للطالب الانسحاب من مقرر واحد في الفصل قبل نهاية الأسبوع الثامن، ويرصد له تقدير منسحب دون أن يؤثر في معدله.",
            "المادة الحادية عشرة - التأجيل: يجوز للطالب تأجيل الدراسة مدة لا تتجاوز فصلين دراسيين متتاليين أو ثلاثة فصول متفرقة طوال مدة دراسته.",
        ],
    ),
    (
        "ltr",
        "Chapter 4: Housing and Fees",
        [
            "Article 12 - Housing eligibility: University housing is available to students whose permanent address is more than 100 kilometres from campus. Priority is given to first-year students.",
            "Article 13 - Housing fees: Housing fees of 1,500 riyals per semester are paid at the start of each semester. Students who leave housing after week four are not refunded.",
            "Article 14 - Parking: Students may register one car for campus parking each academic year. The parking permit costs 200 riyals and must be displayed at all times.",
        ],
    ),
]

CSS = """
@font-face { font-family: body; src: url(DejaVuSans.ttf); }
@font-face { font-family: body; src: url(DejaVuSans-Bold.ttf); font-weight: bold; }
* { font-family: body; }
h1 { font-size: 17px; margin-bottom: 10px; }
p { font-size: 12px; line-height: 1.7; margin-bottom: 10px; }
"""


def build(font_dir: Path) -> None:
    archive = pymupdf.Archive(str(font_dir))
    doc = pymupdf.open()
    for direction, heading, paragraphs in PAGES:
        page = doc.new_page(width=595, height=842)  # A4
        body = "".join(f"<p>{text}</p>" for text in paragraphs)
        html = f'<div dir="{direction}"><h1>{heading}</h1>{body}</div>'
        page.insert_htmlbox(pymupdf.Rect(56, 56, 539, 800), html, css=CSS, archive=archive)
    doc.set_metadata({"title": "Daleel sample student guide (fictional)", "author": "Daleel"})
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.subset_fonts()  # embed only the glyphs used, keeps the file small
    doc.save(str(OUTPUT), garbage=4, deflate=True)
    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size // 1024} KB, {len(PAGES)} pages)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--font-dir", default="/usr/share/fonts/truetype/dejavu", type=Path)
    build(parser.parse_args().font_dir)
