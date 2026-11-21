import os

import requests, pandas as pd
from dotenv import load_dotenv
import numpy as np

HEADERS = {"User-Agent": os.environ["GM"]}
TARGET = "CIK0000078003"

url = f"https://data.sec.gov/api/xbrl/companyfacts/{TARGET}.json"
response = requests.get(url, headers=HEADERS)
response.raise_for_status()

facts = response.json()

TAG = {
    "Revenues": "Revenues",
    "R&D": "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost",
    "pretax": "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
    "other": "OtherNonoperatingIncomeExpense",
    "sold": "CostOfGoodsAndServicesSold",
}


def check_data():
    print(f"facts.keys() : {list(facts.keys())}")

    print(f"cik : {facts["cik"]}")
    print(f"entityName : {facts["entityName"]}")
    print(f"facts : {list(facts["facts"].keys())}")

    print("\n---facts---")
    print(f"dei : {list(facts["facts"]["dei"].keys())}")
    print(f"srt : {list(facts["facts"]["srt"].keys())}")
    print(f"ffd : {list(facts["facts"]["ffd"].keys())}")


def annual(tag, unit="USD") -> pd.DataFrame:
    concepts = facts["facts"]["us-gaap"][tag]

    df = pd.DataFrame(concepts["units"][unit])
    df = df[df["form"].eq("10-K")].copy()
    df["start"] = pd.to_datetime(df["start"])
    df["end"] = pd.to_datetime(df["end"])
    df["days"] = (df["end"] - df["start"]).dt.days

    # companies don't necessarily follow the calendar year.
    df = df[(df["days"] >= 350) & (df["days"] <= 380)]

    # Keep the latest filed observation for each fiscal year
    df = df.sort_values("filed")
    df = df.drop_duplicates(subset=["fy"], keep="last")
    df = df.dropna(subset=["start", "end"]).copy()

    return df.set_index("fy")["val"].sort_index()


def missing_years(s):
    if s.empty:
        return []

    years = set(s.index.astype(int))

    expected_years = set(range(min(years), max(years) + 1))

    return sorted(expected_years - years)


def report_coverage(tag):
    concepts = facts["facts"]["us-gaap"]
    for label, concept_tag in tag.items():
        print(f"\n---{label}---")
        if concept_tag not in concepts:
            print("Concept not found")
            continue
        s = annual(concept_tag)
        if s.empty:
            print("No annual observations found")
            continue
        print(f"FY range: {s.index.min()} ~ {s.index.max()}")
        print(f"Number of years: {len(s)}")
        print(f"Missing years: {missing_years(s)}")


def coverage():
    pretax = annual(
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"
    )
    other = annual("OtherNonoperatingIncomeExpense")
    operating_income = pretax - other
    gross_profit = annual("Revenues") - annual("CostOfGoodsAndServicesSold")


if __name__ == "__main__":
    report_coverage({"pretax": TAG["pretax"], "other": TAG["other"]})
