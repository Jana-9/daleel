# Retrieval evaluation

Document: `samples/daleel-sample-guide.pdf` (4 pages, fictional). 20 answerable questions (arabic, cross-lingual, dialect, english), 5 unanswerable.
Embedding model: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`; chunks of 450 characters; RRF k = 60.

| Method | Recall@1 | Recall@3 | Recall@5 | MRR | Median latency |
| --- | --- | --- | --- | --- | --- |
| vector | 90% | 90% | 100% | 0.92 | 7 ms |
| keyword | 60% | 60% | 75% | 0.63 | 1 ms |
| hybrid | 95% | 95% | 100% | 0.96 | 7 ms |

Rank of the first correct passage per question (— = not in top 5):

| Question | Kind | vector | keyword | hybrid |
| --- | --- | --- | --- | --- |
| ما شروط القبول في الجامعة؟ | arabic | 1 | 1 | 1 |
| كم أقل عدد ساعات أقدر أسجلها في الفصل؟ | dialect | 1 | 5 | 1 |
| كم رسوم بدل فاقد البطاقة الجامعية؟ | arabic | 1 | 1 | 1 |
| What is the minimum score for admission? | cross-lingual | 1 | — | 1 |
| متى أسجل المقررات؟ | dialect | 1 | 1 | 1 |
| وش شروط التسجيل في التدريب التعاوني؟ | dialect | 1 | 1 | 1 |
| كم مدة التدريب التعاوني؟ | arabic | 1 | 1 | 1 |
| كيف يتم تقييم الطالب في التدريب؟ | arabic | 1 | 1 | 1 |
| هل أقدر أقسم التدريب على فصلين؟ | dialect | 1 | 1 | 1 |
| How long is the cooperative training? | cross-lingual | 1 | — | 1 |
| كيف أعتذر عن التدريب التعاوني؟ | dialect | 1 | 1 | 1 |
| كم نسبة الغياب اللي تحرمني من الاختبار؟ | dialect | 4 | 1 | 1 |
| متى آخر موعد للاعتذار عن الفصل؟ | arabic | 1 | 1 | 1 |
| أبي أنسحب من مادة، متى آخر موعد؟ | dialect | 1 | 5 | 1 |
| كم فصل أقدر أأجل دراستي؟ | dialect | 5 | 4 | 5 |
| What happens if I miss too many lectures? | cross-lingual | 1 | — | 1 |
| Who is eligible for university housing? | english | 1 | 1 | 1 |
| كم رسوم السكن؟ | cross-lingual | 1 | — | 1 |
| How much does a parking permit cost? | english | 1 | 1 | 1 |
| هل يرجعون فلوس السكن إذا طلعت منه؟ | cross-lingual | 1 | — | 1 |

Unanswerable questions (best vector similarity, any keyword match):

- `intl-fees`: 0.60, keyword match: True
- `summer`: 0.32, keyword match: False
- `dress-code`: 0.42, keyword match: False
- `scholarships`: 0.67, keyword match: False
- `president`: 0.36, keyword match: False
- Lowest best-similarity among answerable questions: 0.32

Limitations: one short document and a small hand-written question set, so these numbers show relative differences between methods, not expected accuracy on real documents.
