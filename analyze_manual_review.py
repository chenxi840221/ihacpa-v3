import pandas as pd
import warnings
warnings.filterwarnings("ignore")

# Read the file
df = pd.read_excel("2023-07 IHACPA Python Review (REQ2486483) REVIEW DJM 2025-07-18.xlsx", header=2)

# Look for packages where manual review found issues
print("Analyzing manual review results...")
print("\n1. Checking REVIEW NOTES columns for non-standard entries:")

error_packages = []

# Check each REVIEW NOTES column
for col in ["REVIEW NOTES", "REVIEW NOTES.1", "REVIEW NOTES.2", "REVIEW NOTES.3"]:
    if col in df.columns:
        # Find entries that are not standard Reviewed OK
        mask = df[col].notna() & ~df[col].str.contains("Reviewed OK", na=False)
        if mask.any():
            print(f"\n{col}:")
            for idx in df[mask].index:
                pkg = df.loc[idx, "Package Name"]
                note = df.loc[idx, col]
                print(f"  - {pkg}: {note}")
                error_packages.append((pkg, col, note))

# Check MANUAL Recommendation
print("\n2. Checking MANUAL Recommendation for non-PROCEED entries:")
if "MANUAL Recommendation" in df.columns:
    mask = df["MANUAL Recommendation"].notna() & (df["MANUAL Recommendation"] != "PROCEED")
    if mask.any():
        for idx in df[mask].index:
            pkg = df.loc[idx, "Package Name"]
            rec = df.loc[idx, "MANUAL Recommendation"]
            print(f"  - {pkg}: {rec}")
            error_packages.append((pkg, "MANUAL Recommendation", rec))

# Check AUTO vs MANUAL mismatches
print("\n3. Checking AUTO vs MANUAL recommendation mismatches:")
if "AUTO Recommendation" in df.columns and "MANUAL Recommendation" in df.columns:
    # Compare recommendations
    auto_rec = df["AUTO Recommendation"]
    manual_rec = df["MANUAL Recommendation"]
    
    # Find where AUTO said PROCEED but MANUAL said something else
    mask = (auto_rec.str.contains("PROCEED", na=False) & 
            manual_rec.notna() & 
            (manual_rec != "PROCEED"))
    
    if mask.any():
        print("\nPackages where AUTO said PROCEED but MANUAL disagreed:")
        for idx in df[mask].index:
            pkg = df.loc[idx, "Package Name"]
            auto = df.loc[idx, "AUTO Recommendation"]
            manual = df.loc[idx, "MANUAL Recommendation"]
            print(f"  - {pkg}:")
            print(f"    AUTO: {auto[:80]}...")
            print(f"    MANUAL: {manual}")

print(f"\nTotal unique packages with issues: {len(set(pkg for pkg, _, _ in error_packages))}")

# Save detailed analysis
if error_packages:
    error_df = pd.DataFrame(error_packages, columns=["Package", "Column", "Issue"])
    error_df.to_csv("manual_review_errors.csv", index=False)
    print("\nDetailed errors saved to manual_review_errors.csv")