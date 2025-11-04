# automotive-pricing-intelligence.py
# Simple script: loads the Excel, cleans a bit, creates columns, saves results and charts.

import pandas as pd
import matplotlib.pyplot as plt
import os
import sys
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
import matplotlib.pyplot as plt


file_name = "automotive_pricing_bi_dataset.xlsx"
if not os.path.exists(file_name):
    print("ERROR: Excel file not found in project folder:", file_name)
    print("Please put the file in the same folder as this script and run again.")
    sys.exit(1)

# Load file
df = pd.read_excel(file_name)

print("Loaded file. Rows:", len(df), "Columns:", len(df.columns))
print("Column names:", list(df.columns))

# Basic cleaning and safety: strip strings and ensure numeric types for key columns
text_cols = df.select_dtypes(include=['object']).columns
for c in text_cols:
    try:
        df[c] = df[c].astype(str).str.strip()
    except Exception:
        pass

# Make sure these columns exist — if a name is slightly different, we try to guess common alternatives
col_map = {}
def find_col(possible_names):
    for name in possible_names:
        if name in df.columns:
            return name
    return None

col_map['price'] = find_col(['Price','price','Unit_Price'])
col_map['competitor_price'] = find_col(['Competitor_Price','competitor_price','Comp_Price','Competitor price'])
col_map['cost'] = find_col(['Cost','cost','Unit_Cost'])
col_map['units'] = find_col(['Units_Sold','Units','Quantity','units_sold'])
col_map['part'] = find_col(['Part_Name','Part','Part_ID','PartName'])

print("\nDetected columns (may be None if missing):")
for k,v in col_map.items():
    print(k, "->", v)

# Convert numeric columns
for key in ['price','competitor_price','cost','units']:
    col = col_map.get(key)
    if col:
        df[col] = pd.to_numeric(df[col], errors='coerce')

# Remove exact duplicates
before = len(df)
df = df.drop_duplicates()
after = len(df)
print(f"\nRemoved duplicates: {before - after} rows dropped")

# Drop rows missing price or part id/name (we can't analyse these)
if col_map['price'] is None or col_map['part'] is None:
    print("ERROR: Required column(s) missing (price or part). Please check column names and run again.")
    sys.exit(1)

df = df.dropna(subset=[col_map['price'], col_map['part']])
print("Rows after dropping missing key fields:", len(df))

# Create helpful columns (safe with missing competitor price / cost)
cp = col_map['competitor_price']
co = col_map['cost']
pr = col_map['price']
un = col_map['units']

df['Price_diff'] = df[pr] - df[cp] if cp is not None else pd.NA
df['Price_pct_diff'] = (df['Price_diff'] / df[cp] * 100) if cp is not None else pd.NA
df['Margin'] = (df[pr] - df[co]) if co is not None else pd.NA
df['Revenue_calc'] = (df[pr] * df[un]) if un is not None else pd.NA

# Save cleaned data
clean_name = "cleaned_automotive_pricing.csv"
df.to_csv(clean_name, index=False)
print("\n✅ Cleaned CSV saved as:", clean_name)

# ---- Simple analyses and CSV outputs ----

# 1) Top 20 parts by Revenue (use Revenue column if exists, otherwise Revenue_calc)
rev_col = find_col(['Revenue','revenue']) or 'Revenue_calc'
if rev_col not in df.columns:
    rev_col = 'Revenue_calc'
top_revenue = df.sort_values(by=rev_col, ascending=False).head(20)
top_revenue.to_csv("top20_by_revenue.csv", index=False)
print("Top 20 by revenue saved to top20_by_revenue.csv")

# 2) Parts priced much higher than competitor (if competitor price exists)
if cp is not None:
    overpriced = df[df['Price_pct_diff'] > 10].sort_values('Price_pct_diff', ascending=False)
    overpriced.to_csv("parts_overpriced_gt10pct.csv", index=False)
    print("Parts priced >10% above competitor saved to parts_overpriced_gt10pct.csv")
else:
    print("Competitor price column not found — skipping overpriced list.")

# 3) Low margin & high sales (if Margin and Units exist)
if co is not None and un is not None:
    # define low margin as bottom 25% and high sales as top 25% (simple rule)
    margin_q = df['Margin'].quantile(0.25)
    units_q = df[un].quantile(0.75)
    low_margin_high_sales = df[(df['Margin'] <= margin_q) & (df[un] >= units_q)].sort_values(by=un, ascending=False)
    low_margin_high_sales.to_csv("low_margin_high_sales.csv", index=False)
    print("Low margin & high sales parts saved to low_margin_high_sales.csv")
else:
    print("Cost or Units column not found — skipping low-margin-high-sales list.")

# ---- Make and save charts (png) ----
plt.figure(figsize=(8,5))
df[pr].dropna().hist(bins=20)
plt.title("Price Distribution")
plt.xlabel("Price")
plt.ylabel("Count")
plt.tight_layout()
plt.savefig("chart_price_distribution.png")
plt.close()
print("Saved chart_price_distribution.png")

if cp is not None:
    plt.figure(figsize=(8,5))
    df['Price_pct_diff'].dropna().hist(bins=20)
    plt.title("Price % Difference vs Competitor")
    plt.xlabel("Price % Difference")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig("chart_price_pct_diff.png")
    plt.close()
    print("Saved chart_price_pct_diff.png")
else:
    print("No competitor price -> skipped chart_price_pct_diff")

print("\nAll done. Output files in project folder:")
for f in ["cleaned_automotive_pricing.csv","top20_by_revenue.csv",
          "parts_overpriced_gt10pct.csv","low_margin_high_sales.csv",
          "chart_price_distribution.png","chart_price_pct_diff.png"]:
    if os.path.exists(f):
        print(" -", f)
        # ============================
        # EXTRA ANALYTICS SECTION
        # ============================

        print("\n--- EXTRA ANALYTICS SUMMARY ---")

        # 1. Revenue by Brand
        brand_revenue = df.groupby("Brand")["Revenue"].sum().sort_values(ascending=False)
        print("\n💰 Revenue by Brand:")
        print(brand_revenue.head(10))

        # 2. Average Profit Margin by Region
        region_margin = df.groupby("Region")["Gross_Margin_%"].mean().sort_values(ascending=False)
        print("\n🌍 Average Gross Margin (%) by Region:")
        print(region_margin)

        # 3. Top 10 Most Profitable Parts
        top_profit_parts = df.sort_values("Profit", ascending=False).head(10)
        top_profit_parts.to_csv("top10_profitable_parts.csv", index=False)
        print("\n📈 Top 10 profitable parts saved to top10_profitable_parts.csv")

        # 4. Correlation between Cost, Price, and Profit
        print("\n📊 Correlation between Cost, Price, and Profit:")
        print(df[["Cost", "Price", "Profit"]].corr())

        print("\n✅ Extra analytics completed.")

