import pandas as pd
from pathlib import Path


# ============================================================
# MAVEN TAXI PROJECT
# FINANCIAL CORRECTION VALIDATION
# ============================================================

BASE = Path(r"C:\Users\Asus\OneDrive\Desktop\Maven Taxi")

RAW_FOLDER = BASE / "taxi_trips"

OUTPUT_FOLDER = BASE / "New CSV by Python"

OUTPUT_FOLDER.mkdir(exist_ok=True)

TRIP_FILES = [
    RAW_FOLDER / "2017_taxi_trips.csv",
    RAW_FOLDER / "2018_taxi_trips.csv",
    RAW_FOLDER / "2019_taxi_trips.csv",
    RAW_FOLDER / "2020_taxi_trips.csv"
]

CHUNK_SIZE = 200_000


# ============================================================
# Financial columns
# ============================================================

FINANCIAL_COLUMNS = [
    "fare_amount",
    "extra",
    "mta_tax",
    "tip_amount",
    "tolls_amount",
    "improvement_surcharge",
    "total_amount",
    "congestion_surcharge"
]


# ============================================================
# Process each year
# ============================================================

all_results = []


for file in TRIP_FILES:

    source_year = int(file.stem[:4])

    print("=" * 70)
    print(f"CHECKING {source_year}")
    print("=" * 70)

    total_rows = 0
    matching_rows = 0

    sample_rows = []

    for chunk in pd.read_csv(
        file,
        chunksize=CHUNK_SIZE
    ):

        total_rows += len(chunk)

        # 2017/2018 do not contain congestion_surcharge
        if "congestion_surcharge" not in chunk.columns:
            chunk["congestion_surcharge"] = pd.NA

        for col in FINANCIAL_COLUMNS:
            chunk[col] = pd.to_numeric(
                chunk[col],
                errors="coerce"
            )

        # ----------------------------------------------------
        # Check whether ALL available financial values
        # are <= 0 and at least one is actually negative.
        # ----------------------------------------------------

        available_columns = [
            col for col in FINANCIAL_COLUMNS
            if col in chunk.columns
        ]

        has_negative = (
            chunk[available_columns]
            .lt(0)
            .any(axis=1)
        )

        all_non_positive = (
            chunk[available_columns]
            .fillna(0)
            .le(0)
            .all(axis=1)
        )

        correction_mask = (
            has_negative
            & all_non_positive
        )

        count = int(correction_mask.sum())

        matching_rows += count

        # Save a small sample for inspection
        if count > 0 and len(sample_rows) < 20:

            sample = chunk.loc[
                correction_mask,
                [
                    "VendorID",
                    "lpep_pickup_datetime",
                    "lpep_dropoff_datetime",
                    "PULocationID",
                    "DOLocationID",
                    "fare_amount",
                    "extra",
                    "mta_tax",
                    "tip_amount",
                    "tolls_amount",
                    "improvement_surcharge",
                    "total_amount",
                    "payment_type",
                    "trip_type",
                    "congestion_surcharge"
                ]
            ]

            remaining = 20 - len(sample_rows)

            sample_rows.extend(
                sample.head(remaining).to_dict("records")
            )

    print(f"Total rows checked : {total_rows:,}")
    print(f"Matching records   : {matching_rows:,}")
    print()

    all_results.append({
        "SourceYear": source_year,
        "RowsChecked": total_rows,
        "MatchingFinancialCorrections": matching_rows
    })

    # --------------------------------------------------------
    # Save sample
    # --------------------------------------------------------

    sample_file = (
        OUTPUT_FOLDER
        / f"FinancialCorrection_Sample_{source_year}.csv"
    )

    pd.DataFrame(sample_rows).to_csv(
        sample_file,
        index=False
    )

    print(f"Sample saved: {sample_file}")
    print()


# ============================================================
# Summary
# ============================================================

summary = pd.DataFrame(all_results)

summary_file = (
    OUTPUT_FOLDER
    / "FinancialCorrection_Check_Summary.csv"
)

summary.to_csv(
    summary_file,
    index=False
)

print("=" * 70)
print("FINAL SUMMARY")
print("=" * 70)

print(summary.to_string(index=False))

print()
print(
    "Total matching records:",
    f"{summary['MatchingFinancialCorrections'].sum():,}"
)

print()
print(f"Summary saved to: {summary_file}")
print("=" * 70)