# Retrieval evaluation

Document: `samples/daleel-sample-guide.pdf` (4 pages, fictional). 20 answerable questions (arabic, cross-lingual, dialect, english), 5 unanswerable.
Embedding model: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`; chunks of 450 characters; RRF k = 60; hybrid keeps keyword results covering ≥ 60% of the question's keywords.

| Method | Recall@1 | Recall@3 | Recall@5 | MRR | Median latency |
| --- | --- | --- | --- | --- | --- |
| vector | 90% | 90% | 100% | 0.92 | 8 ms |
| keyword | 65% | 70% | 70% | 0.68 | 2 ms |
| hybrid | 95% | 95% | 100% | 0.96 | 10 ms |

Rank of the first correct passage per question (— = not in top 5):

| Question | Kind | vector | keyword | hybrid |
| --- | --- | --- | --- | --- |
| ما شروط القبول في الجامعة؟ | arabic | 1 | 1 | 1 |
| كم أقل عدد ساعات أقدر أسجلها في الفصل؟ | dialect | 1 | — | 1 |
| كم رسوم بدل فاقد البطاقة الجامعية؟ | arabic | 1 | 1 | 1 |
| What is the minimum score for admission? | cross-lingual | 1 | — | 1 |
| متى أسجل المقررات؟ | dialect | 1 | 1 | 1 |
| وش شروط التسجيل في التدريب التعاوني؟ | dialect | 1 | 1 | 1 |
| كم مدة التدريب التعاوني؟ | arabic | 1 | 1 | 1 |
| كيف يتم تقييم الطالب في التدريب؟ | arabic | 1 | 1 | 1 |
| هل أقدر أقسم التدريب على فصلين؟ | dialect | 1 | 1 | 1 |
| How long is the cooperative training? | cross-lingual | 1 | — | 1 |
| كيف أعتذر عن التدريب التعاوني؟ | dialect | 1 | 2 | 1 |
| كم نسبة الغياب اللي تحرمني من الاختبار؟ | dialect | 4 | 1 | 1 |
| متى آخر موعد للاعتذار عن الفصل؟ | arabic | 1 | 1 | 1 |
| أبي أنسحب من مادة، متى آخر موعد؟ | dialect | 1 | 1 | 1 |
| كم فصل أقدر أأجل دراستي؟ | dialect | 5 | 1 | 5 |
| What happens if I miss too many lectures? | cross-lingual | 1 | — | 1 |
| Who is eligible for university housing? | english | 1 | 1 | 1 |
| كم رسوم السكن؟ | cross-lingual | 1 | — | 1 |
| How much does a parking permit cost? | english | 1 | 1 | 1 |
| هل يرجعون فلوس السكن إذا طلعت منه؟ | cross-lingual | 1 | — | 1 |

Unanswerable questions (best vector similarity, any keyword match):

- `intl-fees`: 0.60, keyword match: True
- `summer`: 0.32, keyword match: False
- `dress-code`: 0.42, keyword match: True
- `scholarships`: 0.67, keyword match: False
- `president`: 0.36, keyword match: False
- Lowest best-similarity among answerable questions: 0.32

Limitations: one short document (8 passages) and a small hand-written question set, so these numbers show relative differences between methods, not expected accuracy on real documents. With only 8 passages, Recall@5 is close to trivial; Recall@1 and MRR are the informative columns. The coverage threshold was chosen on this same set (results were identical at 60% and 75%), so a larger held-out set is needed to confirm it.
