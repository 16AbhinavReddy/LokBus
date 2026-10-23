import json
import re

with open("keywords.json", "r", encoding="utf-8") as file:
    keywords = json.load(file)

def classify(review):
    text = re.sub(r"\s+", " ", review.lower()).strip()
    scores = {}
    for cat, words in keywords.items():
        matched = []
        for word in words:
            pattern = (r"(?<!\w)" + re.escape(word) + r"(?!\w)")
            if re.search(pattern, text):
                matched.append(word)
        scores[cat] = matched
    max_score = max(len(matches) for matches in scores.values())
    res = []
    for cat, mat in scores.items():
        if (len(mat) == max_score):
            res.append(cat)
    predicted = res[0]
    return predicted, scores[predicted], scores

arr = ["The bus was overcrowded and there was no standing space.", "The bus seats were torn and the air conditioning was broken.", "The bus broke down halfway through the journey and arrived late.", "The driver was speeding and overtaking other vehicles dangerously.", "The conductor collected my fare but did not give me a ticket.", "The bus was clean and the journey was comfortable."]
for i, r in enumerate(arr):
    predicted, matched, scores = classify(r)
    print(f"\nTest {i+1}")
    print(f"Review: {r}")
    print(f"Prediction: {predicted}")
    print(f"Matched keywords: {matched}")
    print("Scores:")
    for cat, matches in scores.items():
        print(f"  {cat}: {len(matches)}")

