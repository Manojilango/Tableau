import pandas as pd
import numpy as np
import os
from collections import Counter

INPUT_FILE  = "metadata.csv"
OUTPUT_DIR  = "tableau_data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

USECOLS = ["cord_uid","title","abstract","publish_time","authors","journal","doi","source_x"]

print("Loading metadata.csv... (1-2 minutes)")
df = pd.read_csv(INPUT_FILE, usecols=USECOLS, low_memory=False, on_bad_lines="skip")
print(f"Loaded {len(df):,} rows")

print("Removing duplicates...")
df = df.drop_duplicates(subset=["cord_uid"])
df = df.drop_duplicates(subset=["doi"], keep="first")

print("Parsing dates...")
df["publish_time"] = pd.to_datetime(df["publish_time"], errors="coerce")
df = df[df["publish_time"].between("1990-01-01","2023-12-31")]
df["pub_year"]  = df["publish_time"].dt.year.astype("Int64")
df["pub_month"] = df["publish_time"].dt.month.astype("Int64")
df["year_month"]= df["publish_time"].dt.to_period("M").astype(str)

df["journal"]     = df["journal"].fillna("Unknown").str.strip().str.title().replace("","Unknown")
df["source_x"]    = df["source_x"].fillna("Unknown").str.strip()
df["author_count"]= df["authors"].fillna("").apply(lambda x: len(x.split(";")) if x.strip() else 0)

master_cols = ["cord_uid","title","journal","source_x","pub_year","pub_month","year_month","author_count","doi"]
df[master_cols].to_csv(f"{OUTPUT_DIR}/cord19_master.csv", index=False)

monthly = df.groupby(["pub_year","pub_month","year_month"]).size().reset_index(name="paper_count")
monthly.to_csv(f"{OUTPUT_DIR}/monthly_volume.csv", index=False)

df.groupby("pub_year").size().reset_index(name="paper_count").to_csv(f"{OUTPUT_DIR}/yearly_volume.csv", index=False)

top_journals = df[df["journal"]!="Unknown"].groupby("journal").size().reset_index(name="paper_count").sort_values("paper_count",ascending=False).head(20)
top_journals.to_csv(f"{OUTPUT_DIR}/top_journals.csv", index=False)

df.groupby("source_x").size().reset_index(name="paper_count").sort_values("paper_count",ascending=False).to_csv(f"{OUTPUT_DIR}/source_breakdown.csv", index=False)

top15 = top_journals["journal"].head(15).tolist()
journal_year = df[df["journal"].isin(top15)].groupby(["journal","pub_year"]).size().reset_index(name="paper_count")
journal_year.to_csv(f"{OUTPUT_DIR}/journal_year.csv", index=False)

kpi = pd.DataFrame([{
    "total_papers": len(df),
    "unique_journals": df[df["journal"]!="Unknown"]["journal"].nunique(),
    "unique_sources": df["source_x"].nunique(),
    "avg_papers_per_month": round(monthly["paper_count"].mean(),0),
    "peak_month": monthly.loc[monthly["paper_count"].idxmax(),"year_month"],
    "peak_month_count": monthly["paper_count"].max(),
}])
kpi.to_csv(f"{OUTPUT_DIR}/kpi_summary.csv", index=False)

stopwords = {"the","of","a","and","in","to","for","with","on","an","is","at","from","by","as","this","study","using","based","between","analysis","associated","role","effects","impact","effect","new","two","use","its","also","are","were","was","not","or","be","have","has","been","during","into","after","before","among","within","through","across","patients","covid","19","sars","cov","coronavirus","infection","disease","clinical","case","cases","virus","pandemic","data","health"}
word_counts = Counter()
for title in df["title"].dropna():
    for w in title.lower().split():
        clean = "".join(c for c in w if c.isalpha())
        if len(clean) > 3 and clean not in stopwords:
            word_counts[clean] += 1
pd.DataFrame(word_counts.most_common(100), columns=["keyword","frequency"]).to_csv(f"{OUTPUT_DIR}/top_keywords.csv", index=False)

print("DONE! Your tableau_data/ folder is ready.")
