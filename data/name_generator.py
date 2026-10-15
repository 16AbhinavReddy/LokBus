import pandas as pd
import random

file1 = "bus_route_driver_conductor_mapping.csv"
out1 = "bus_route_driver_conductor_mapping_with_names.csv"
df = pd.read_csv(file1)
random.seed(42)

first_names = ["Aarav", "Aadhya", "Abhay", "Aditya", "Akash", "Akhil", "Ananya", "Anil", "Anjali", "Arjun", "Ashok", "Charan", "Deepa", "Deepak", "Divya", "Gaurav", "Harish", "Karthik", "Kavya", "Kiran", "Lakshmi", "Manoj", "Meera", "Mohan", "Naveen", "Neha", "Nikhil", "Pooja", "Pranav", "Priya", "Rahul", "Rajesh", "Ravi", "Riya", "Rohit", "Sanjay", "Suresh", "Swathi", "Varun", "Vijay", "Vikram", "Vishal"]
last_names = ["Reddy", "Kumar", "Sharma", "Patel", "Rao", "Naidu", "Verma", "Singh", "Yadav", "Nair", "Iyer", "Menon", "Joshi", "Gupta", "Das", "Mishra", "Kulkarni", "Shetty", "Pillai", "Gowda", "Bhat", "Desai", "Chavan", "Mehta", "Khan", "Ali", "Kapoor", "Fernandes"]
def name_generator(names_set):
    while True:
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        if name not in names_set:
            names_set.add(name)
            return name

names = {}
names_set = set()
all_ids = pd.concat([df["driver_id"], df["conductor_id"]]).dropna().unique()
for person_id in all_ids:
    names[person_id] = name_generator(names_set)

df["driver_name"] = df["driver_id"].map(names)
df["conductor_name"] = df["conductor_id"].map(names)
df.to_csv(out1, index=False)
print(f"Updated mapping saved to: {out1}")

