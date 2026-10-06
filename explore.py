import os
import requests
import pandas as pd

TABLE = "RIH02"
URL = (
    "https://ws.cso.ie/public/api.restful/"
    f"PxStat.Data.Cube_API.ReadDataset/{TABLE}/CSV/1.0/en"
)
PATH = f"data/raw/{TABLE}.csv"
headers = {"User-Agent": "Mozilla/5.0 (costas-hacktoberfest)"}

os.makedirs("data/raw", exist_ok=True)

# Download only if we don't already have the file (the file is ~94 MB)
if not os.path.exists(PATH):
    resp = requests.get(URL, headers=headers, timeout=120)
    resp.raise_for_status()
    with open(PATH, "wb") as f:
        f.write(resp.content)

df = pd.read_csv(PATH)

print("Shape (rows, columns):", df.shape)
print("\nColumns:", list(df.columns))
print("\nFirst 5 rows:")
print(df.head())

for col in df.select_dtypes(include="object").columns:
    values = df[col].unique()
    print(f"\n--- {col} ({len(values)} distinct) ---")
    print(values[:40])