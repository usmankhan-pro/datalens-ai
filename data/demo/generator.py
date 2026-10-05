"""
Synthetic demo dataset generator for DataLens AI.

Generates a ~5,000 row business dataset with realistic relationships
and KNOWN injected data quality issues for testing and demonstration.

Random state is fixed at 42 for reproducibility.
"""

import json
import os
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd


# Fixed product-to-category mapping
PRODUCT_CATEGORIES = {
    "Laptop": "Electronics",
    "Smartphone": "Electronics",
    "Tablet": "Electronics",
    "Headphones": "Electronics",
    "Monitor": "Electronics",
    "Desk Chair": "Furniture",
    "Standing Desk": "Furniture",
    "Bookshelf": "Furniture",
    "Notebook": "Office Supplies",
    "Printer Paper": "Office Supplies",
    "Pen Set": "Office Supplies",
    "Backpack": "Accessories",
    "Mouse Pad": "Accessories",
    "USB Cable": "Accessories",
    "Webcam": "Electronics",
}

PRODUCTS = list(PRODUCT_CATEGORIES.keys())
REGIONS = ["North", "South", "East", "West"]

# Base price ranges per product
PRICE_RANGES = {
    "Laptop": (800, 2000),
    "Smartphone": (400, 1200),
    "Tablet": (300, 800),
    "Headphones": (50, 300),
    "Monitor": (200, 800),
    "Desk Chair": (150, 600),
    "Standing Desk": (300, 1200),
    "Bookshelf": (80, 400),
    "Notebook": (5, 25),
    "Printer Paper": (8, 30),
    "Pen Set": (10, 50),
    "Backpack": (30, 150),
    "Mouse Pad": (10, 40),
    "USB Cable": (5, 25),
    "Webcam": (50, 200),
}


def generate_demo_dataset(seed: int = 42) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Generate the synthetic demo dataset with injected quality issues.

    Args:
        seed: Random seed for reproducibility.

    Returns:
        Tuple of (DataFrame, ground_truth_dict).
        Ground truth contains exact counts of all injected issues.
    """
    rng = np.random.RandomState(seed)
    n_rows = 5000

    # ---- Generate clean base data ----

    # Dates: 2023-01-01 to 2024-06-30 with seasonal weights
    date_range = pd.date_range("2023-01-01", "2024-06-30", freq="D")
    # Weight by month: peak in Dec (12), dip in Feb (2)
    month_weights = {
        1: 1.0, 2: 0.6, 3: 0.9, 4: 1.0, 5: 1.1, 6: 1.1,
        7: 1.0, 8: 1.0, 9: 1.1, 10: 1.2, 11: 1.3, 12: 1.6,
    }
    day_weights = np.array([month_weights[d.month] for d in date_range], dtype=float)
    day_weights /= day_weights.sum()
    dates = rng.choice(date_range, size=n_rows, p=day_weights)
    dates = pd.to_datetime(dates)

    # Customer IDs
    customer_ids = [f"C{rng.randint(1, 501):04d}" for _ in range(n_rows)]

    # Regions
    regions = rng.choice(REGIONS, size=n_rows, p=[0.30, 0.25, 0.25, 0.20])

    # Products and Categories
    products = rng.choice(PRODUCTS, size=n_rows)
    categories = [PRODUCT_CATEGORIES[p] for p in products]

    # Quantity: 1-20, skewed towards smaller quantities
    quantities = rng.geometric(p=0.15, size=n_rows).clip(1, 50)

    # Marketing Spend: base 100-5000
    marketing_spend = rng.uniform(100, 5000, size=n_rows)

    # Revenue: correlated with marketing spend (~0.6-0.8) + product price
    base_prices = np.array([rng.uniform(*PRICE_RANGES[p]) for p in products])
    revenue = (
        base_prices * quantities
        + marketing_spend * rng.uniform(0.3, 0.8, size=n_rows)  # correlation
        + rng.normal(0, 200, size=n_rows)  # noise
    ).clip(10, None).round(2)

    # Cost: 40-70% of revenue
    cost_ratio = rng.uniform(0.40, 0.70, size=n_rows)
    cost = (revenue * cost_ratio).round(2)

    # Profit: Revenue - Cost
    profit = (revenue - cost).round(2)

    # Round marketing spend
    marketing_spend = marketing_spend.round(2)

    # Build DataFrame
    df = pd.DataFrame({
        "Date": dates.strftime("%Y-%m-%d"),
        "Customer_ID": customer_ids,
        "Region": regions.tolist(),
        "Product": products.tolist(),
        "Category": categories,
        "Quantity": quantities.astype(int),
        "Revenue": revenue,
        "Cost": cost,
        "Profit": profit,
        "Marketing_Spend": marketing_spend,
    })

    # ---- Inject known quality issues ----
    ground_truth: Dict[str, Any] = {}

    # 1. Missing Marketing_Spend: 8% (~400)
    n_missing_marketing = int(n_rows * 0.08)
    missing_marketing_idx = rng.choice(n_rows, size=n_missing_marketing, replace=False)
    df.loc[missing_marketing_idx, "Marketing_Spend"] = np.nan
    ground_truth["missing_marketing_spend"] = int(n_missing_marketing)

    # 2. Missing Cost: 3% (~150)
    n_missing_cost = int(n_rows * 0.03)
    missing_cost_idx = rng.choice(n_rows, size=n_missing_cost, replace=False)
    df.loc[missing_cost_idx, "Cost"] = np.nan
    # Also set Profit to NaN where Cost is missing
    df.loc[missing_cost_idx, "Profit"] = np.nan
    ground_truth["missing_cost"] = int(n_missing_cost)

    # 3. Missing Region: 2% (~100)
    n_missing_region = int(n_rows * 0.02)
    missing_region_idx = rng.choice(n_rows, size=n_missing_region, replace=False)
    df.loc[missing_region_idx, "Region"] = np.nan
    ground_truth["missing_region"] = int(n_missing_region)

    # 4. Duplicate rows: 40 exact duplicates
    n_duplicates = 40
    dup_source_idx = rng.choice(n_rows, size=n_duplicates, replace=True)
    dup_rows = df.iloc[dup_source_idx].copy()
    df = pd.concat([df, dup_rows], ignore_index=True)
    ground_truth["duplicate_rows"] = int(n_duplicates)

    # 5. Extreme Revenue outliers: 15 values (~10x normal)
    n_outliers = 15
    outlier_idx = rng.choice(len(df), size=n_outliers, replace=False)
    df.loc[outlier_idx, "Revenue"] = df.loc[outlier_idx, "Revenue"] * rng.uniform(8, 12, size=n_outliers)
    df.loc[outlier_idx, "Revenue"] = df.loc[outlier_idx, "Revenue"].round(2)
    ground_truth["revenue_outliers"] = int(n_outliers)

    # 6. Negative Quantity values: 6
    n_neg_qty = 6
    neg_qty_idx = rng.choice(len(df), size=n_neg_qty, replace=False)
    df.loc[neg_qty_idx, "Quantity"] = -rng.randint(1, 10, size=n_neg_qty)
    ground_truth["negative_quantities"] = int(n_neg_qty)

    # 7. Unparseable date strings: 8
    n_bad_dates = 8
    bad_date_idx = rng.choice(len(df), size=n_bad_dates, replace=False)
    bad_date_values = ["not_a_date", "N/A", "TBD", "pending", "???", "INVALID", "null", "---"]
    for i, idx in enumerate(bad_date_idx):
        df.loc[idx, "Date"] = bad_date_values[i % len(bad_date_values)]
    ground_truth["unparseable_dates"] = int(n_bad_dates)

    # 8. Inconsistent casing in Region: 12 variants
    n_casing = 12
    casing_idx = rng.choice(
        df[df["Region"].notna()].index, size=n_casing, replace=False
    )
    casing_variants = [
        "north", "NORTH", "NORTH ", "  North", "south ", "SOUTH",
        "east", "EAST ", " East", "west", "WEST", " west ",
    ]
    for i, idx in enumerate(casing_idx):
        df.loc[idx, "Region"] = casing_variants[i]
    ground_truth["inconsistent_casing_region"] = int(n_casing)

    # Record total shape
    ground_truth["total_rows"] = len(df)
    ground_truth["total_columns"] = len(df.columns)
    ground_truth["original_rows_before_duplicates"] = n_rows

    # Shuffle to mix injected issues throughout
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)

    return df, ground_truth


def save_ground_truth(ground_truth: Dict[str, Any], output_dir: str = None) -> str:
    """
    Save ground truth to data/demo/ground_truth.json.

    Args:
        ground_truth: Dictionary of injected issue counts.
        output_dir: Directory to save to. Defaults to data/demo/.

    Returns:
        Path to the saved file.
    """
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__))
    
    filepath = os.path.join(output_dir, "ground_truth.json")
    with open(filepath, "w") as f:
        json.dump(ground_truth, f, indent=2)
    return filepath


if __name__ == "__main__":
    df, gt = generate_demo_dataset()
    save_ground_truth(gt)
    print(f"Generated demo dataset: {df.shape}")
    print(f"Ground truth: {json.dumps(gt, indent=2)}")
