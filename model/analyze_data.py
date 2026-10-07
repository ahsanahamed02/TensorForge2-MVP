import pandas as pd

train = pd.read_csv("data/train.csv")
validation = pd.read_csv("data/validation.csv")

print("\n=== TENSORFORGE DATASET ===")
print("Training tickets:", len(train))
print("Validation tickets:", len(validation))

print("\n=== COLUMNS ===")
print(train.columns.tolist())

print("\n=== FIRST 5 TICKETS ===")
print(train.head())

print("\n=== CATEGORY DISTRIBUTION ===")
print(train["category"].value_counts())

print("\n=== LANGUAGE DISTRIBUTION ===")
print(train["language"].value_counts())

print("\n=== URGENCY DISTRIBUTION ===")
print(train["is_urgent"].value_counts())

print("\n=== MISSING VALUES ===")
print(train.isnull().sum())