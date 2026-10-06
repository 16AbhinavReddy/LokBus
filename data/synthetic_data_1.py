import json
import random
from datetime import datetime
import torch
from transformers import (AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig)


model = "Qwen/Qwen2.5-3B-Instruct"
total = 50
batch = 5
random.seed(42)
cat = ["Driving", "Disruptions", "Ticket Handling"]
scenes = {"Driving": ["safe driving", "smooth driving", "rash driving", "overspeeding", "sudden braking", "dangerous overtaking"], "Disruptions": ["on-time arrival", "smooth journey", "heavy traffic", "unexpected delay", "vehicle breakdown", "route diversion"], "Ticket Handling": ["ticket issued immediately", "correct fare charged", "fare collected but no ticket issued", "incorrect fare charged", "change not returned"]}

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
    print(f"\nmodel: {model}")
    conf = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True)
    tokenizer = AutoTokenizer.from_pretrained(model)
    model = AutoModelForCausalLM.from_pretrained(model, quantization_config = conf, device_map = "auto", torch_dtype = torch.float16)
    model.eval()
    print("\nModel loaded")
    return tokenizer, model

def generate_review(tokenizer, model, category, scenario):
    prompt = f"""
        Generate a realistic passenger review for a local city bus.
        Category: {category} 
        Scenario: {scenario}
        The review should:
            - Sound like an ordinary passenger.
            - Use conversational english.
            - Be realistic.
            - Be different from generic templates.
            - Be concise.
            - Do not use markdown.
            - Do not mention that the review is synthetic.
        Return only valid json.
        Format:
        {{
            "review": "..."
        }}
    """

    messages = [{"role": "system", "content": "You generate realistic bus passenger reviews."},{"role": "user","content": prompt}]
    prompt = (tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True))
    inputs = tokenizer(prompt, return_tensors="pt")
    for k in inputs:
        inputs[k] = inputs[k].to(model.device)

    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=200,do_sample=True,temperature=0.85,top_p=0.9, repetition_penalty=1.1, pad_token_id=tokenizer.eos_token_id)

    tokens = outputs[0][inputs["input_ids"].shape[1]:]
    text = tokenizer.decode(tokens, skip_special_tokens=True)
    return text


def main():
    #check()
    tokenizer, model = load_model()
    cat = random.choice(cat)
    scenes = random.choice(scenes[cat])

    print(f"\nCategory: {cat}")
    print(f"\nScenario: {scenes}")

    review = generate_review(tokenizer, model,cat,scenes)
    print("\nGenerated output:")
    print(review)

if __name__ == "__main__":
    main()
