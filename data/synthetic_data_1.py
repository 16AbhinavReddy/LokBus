import json
import random
from datetime import datetime, timedelta
import torch
from transformers import (AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig)
import re


model_name = "Qwen/Qwen2.5-3B-Instruct"
total = 50
batch = 5
random.seed(42)
cat = ["Driving", "Disruptions", "Ticket Handling"]
sentiment_counts = {"Driving": {"Positive": 8, "Negative": 6, "Neutral": 2}, "Disruptions": {"Positive": 7,"Negative": 9, "Neutral": 2}, "Ticket Handling": {"Positive": 8, "Negative": 8, "Neutral": 2}}
scenarios = {"Driving": {"Positive": ["safe driving", "smooth driving", "following traffic signals", "careful overtaking", "smooth braking"], "Negative": ["rash driving", "overspeeding", "sudden braking", "dangerous overtaking", "sudden lane changes", "ignoring traffic signals"], "Neutral": ["normal driving", "average driving", "moderate speed"]},
"Disruptions": {"Positive": ["on-time arrival", "normal travel time", "smooth journey", "minimal traffic delay"], "Negative": ["heavy traffic", "long travel time", "unexpected delay","road construction", "vehicle breakdown", "route diversion", "long waiting at stops"], "Neutral": ["moderate traffic", "minor delay", "average travel time"]},
"Ticket Handling": {"Positive": ["ticket issued immediately", "correct fare charged", "correct change returned", "ticket provided without asking"],"Negative": ["fare collected but no ticket issued","same ticket reused for another passenger","conductor refusing to provide ticket","incorrect fare charged","change not returned", "cash collected without issuing ticket"], "Neutral": ["normal ticket issuing", "minor waiting for ticket", "normal fare collection"]}}

def check():
    if not torch.cuda.is_available():
        print("\nGPU not found")
    name = torch.cuda.get_device_name(0)
    mem = (torch.cuda.get_device_properties(0).total_memory/ (1024 ** 3))
    print(f"\nName: {name}")
    print(f"Mem: {mem:.2f} GB")
    print(f"cuda version: {torch.version.cuda}")
    print()


def load_model():
    print(f"\nmodel: {model_name}")
    conf = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name, quantization_config = conf, device_map = "auto", torch_dtype = torch.float16)
    model.eval()
    print("\nModel loaded")
    return tokenizer, model

def generate_review(tokenizer, model, batch):
    category = batch[0]["category"]
    requirements = []
    for i, item in enumerate(batch):
        requirements.append({"id": i, "sentiment": item["sentiment"], "scenario": item["scenario"]})
    prompt = f"""
        Generate realistic passenger reviews for a local city bus.
        Category: {category}
        Generate exactly {len(batch)} reviews.
        Each review must match its assigned scenario and sentiment.
        The reviews should:
            - Sound like ordinary passengers.
            - Use conversational english.
            - Be realistic.
            - Be different from each other.
            - Vary sentence length.
            - Vary sentence structure.
            - Do not use the same sentence template repeatedly.
            - Some reviews should be short.
            - Some reviews can be 2 sentences.
            - Do not use markdown.
            - Do not use bullet points.
            - Do not mention that the reviews are synthetic.
        Return only valid json.
        Format:
        [
            {{
                "id": 0,
                "review": "..."
            }}
        ]
        Required reviews:
        {json.dumps(requirements, indent=2)}
    """

    messages = [{"role": "system", "content": "You generate realistic and diverse synthetic bus passenger reviews."},{"role": "user","content": prompt}]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors="pt")

    for k in inputs:
        inputs[k] = inputs[k].to(model.device)
    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=1000, do_sample=True, temperature=0.85,top_p=0.9, repetition_penalty=1.1, pad_token_id=tokenizer.eos_token_id)
    tokens = outputs[0][inputs["input_ids"].shape[1]:]
    text = tokenizer.decode(tokens, skip_special_tokens=True)
    return extract_json(text)

def build_plan():
    plan = []
    for category, sentiments in sentiment_counts.items():
        for sent, cnt in sentiments.items():
            opt = scenarios[category][sent]
            for i in range(cnt):
                plan.append({"category": category, "sentiment": sent, "scenario": random.choice(opt)})
    random.shuffle(plan)
    return plan

def extract_json(text):
    text = text.strip()
    text = re.sub(r"```json", "", text, flags=re.IGNORECASE)
    text = text.replace("```", "")
    text = text.strip()
    s = text.find("[")
    e = text.rfind("]")

    if s == -1 or e == -1:
        return None
    json_text = text[s:e + 1]
    return json.loads(json_text)

def generate_timestamp():
    s = datetime(2025, 1, 1)
    e = datetime(2026, 10, 1)
    sec = random.randint(0, int((e - s).total_seconds()))
    return (s+ timedelta(seconds=sec))

def generate_dataset(tokenizer, model):
    plan = build_plan()
    print(f"\nTotal reviews: {len(plan)}")
    reviews = []
    sum = (len(plan) + batch-1) // batch
    for num, start in enumerate(range(0, len(plan), batch), start=1):
        curr = plan[start:start + batch]
        print(f"\nBatch {num}/{sum}")
        gen = None
        for i in range(3):
            gen = generate_review(tokenizer, model, curr)
            if gen:
                break
            print(f"Generation failed. Try {i + 1}/3")
        if not gen:
            print("Skipping failed batch.")
            continue
        for item in gen:
            idx = int(item["id"])
            if idx >= len(curr):
                continue
            review = item.get("review", "")
            if not review:
                continue
            config = curr[idx]
            reviews.append({"category": config["category"], "scenario": config["scenario"], "sentiment": config["sentiment"], "timestamp": generate_timestamp(), "review": review })
        print(f"Reviews collected: {len(reviews)}")
        torch.cuda.empty_cache()
    return reviews


def main():
    #check()
    tokenizer, model = load_model()
    reviews = generate_dataset(tokenizer, model)
    print(reviews[1])
    print("Done")

if __name__ == "__main__":
    main()

