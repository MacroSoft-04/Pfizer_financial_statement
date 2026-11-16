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

DEBUG = False


def debug_print(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)


debug_print(f"facts.keys() : {list(facts.keys())}")

debug_print(f"cik : {facts["cik"]}")
debug_print(f"entityName : {facts["entityName"]}")
debug_print(f"facts : {list(facts["facts"].keys())}")
debug_print("\n---facts---")
debug_print(f"dei : {list(facts["facts"]["dei"].keys())}")
debug_print(f"srt : {list(facts["facts"]["srt"].keys())}")
debug_print(f"ffd : {list(facts["facts"]["ffd"].keys())}")


def annual(tag, unit="USD"):
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

    return (
        df.sort_values("filed")
        .drop_duplicates("end", keep="last")
        .set_index("end")["val"]
    )


for tag in [
    "Revenues",
    "ResearchAndDevelopmentExpense",
    "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
    "OtherNonoperatingIncomeExpense",
    "CostOfGoodsAndServicesSold",
]:
    concepts = facts["facts"]["us-gaap"]
    if tag in concepts:
        s = annual(tag)
        print(f"{tag}: {s.index.min()}~" f"{s.index.max()}({len(s)} yrs)~")
    else:
        print(f"{tag}: Not found")

pretax = annual(
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"
)
other = annual("OtherNonoperatingIncomeExpense")
operating_income = pretax - other
gross_profit = annual("Revenues") - annual("CostOfGoodsAndServicesSold")
