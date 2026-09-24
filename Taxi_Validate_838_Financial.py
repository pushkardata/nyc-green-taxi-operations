import pandas as pd
from pathlib import Path

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

ZONE_FILE = BASE / "taxi_zones.csv"

zones = pd.read_csv(ZONE_FILE)

valid_zone_ids = set(
    pd.to_numeric(
        zones["LocationID"],
        errors="coerce"
    )
    .dropna()
    .astype(int)
)

results = []
samples = []


for file in TRIP_FILES:

    source_year = int(file.stem[:4])

    print("=" * 70)
    print(f"VALIDATING {source_year}")
    print("=" * 70)

    checked_after_filters = 0
    financial_matches = 0

    for chunk in pd.read_csv(
        file,
        chunksize=CHUNK_SIZE
    ):

        # ----------------------------------------------------
        # Standardize 2017/2018 schema
        # ----------------------------------------------------

        if "congestion_surcharge" not in chunk.columns:
            chunk["congestion_surcharge"] = pd.NA

        # ----------------------------------------------------
        # Datetimes
        # ----------------------------------------------------

        chunk["lpep_pickup_datetime"] = pd.to_datetime(
            chunk["lpep_pickup_datetime"],
            errors="coerce"
        )

        chunk["lpep_dropoff_datetime"] = pd.to_datetime(
            chunk["lpep_dropoff_datetime"],
            errors="coerce"
        )

        # ----------------------------------------------------
        # Numeric columns
        # ----------------------------------------------------

        numeric_columns = [
            "RatecodeID",
            "PULocationID",
            "DOLocationID",
            "payment_type",
            "trip_type",
            "fare_amount",
            "extra",
            "mta_tax",
            "tip_amount",
            "tolls_amount",
            "improvement_surcharge",
            "total_amount",
            "congestion_surcharge"
        ]

        for col in numeric_columns:
            chunk[col] = pd.to_numeric(
                chunk[col],
                errors="coerce"
            )

        # ----------------------------------------------------
        # REPRODUCE OUR CLEANING FILTERS
        # ----------------------------------------------------

        # Expected source year
        mask = (
            chunk["lpep_pickup_datetime"].notna()
            & (
                chunk["lpep_pickup_datetime"].dt.year
                == source_year
            )
        )

        # Valid datetime
        mask &= (
            chunk["lpep_pickup_datetime"].notna()
            & chunk["lpep_dropoff_datetime"].notna()
        )

        # Valid zones
        mask &= chunk["PULocationID"].isin(valid_zone_ids)
        mask &= chunk["DOLocationID"].isin(valid_zone_ids)

        # Not store-forward
        mask &= (
            chunk["store_and_fwd_flag"]
            .astype("string")
            .str.upper()
            .ne("Y")
        )

        # Standard rate
        mask &= chunk["RatecodeID"].eq(1)

        # Card or cash
        mask &= chunk["payment_type"].isin([1, 2])

        # Street hail
        mask &= chunk["trip_type"].eq(1)

        filtered = chunk.loc[mask].copy()

        # ----------------------------------------------------
        # Reversed timestamps
        # ----------------------------------------------------

        reversed_time = (
            filtered["lpep_pickup_datetime"]
            > filtered["lpep_dropoff_datetime"]
        )

        pickup_temp = filtered.loc[
            reversed_time,
            "lpep_pickup_datetime"
        ].copy()

        filtered.loc[
            reversed_time,
            "lpep_pickup_datetime"
        ] = filtered.loc[
            reversed_time,
            "lpep_dropoff_datetime"
        ].values

        filtered.loc[
            reversed_time,
            "lpep_dropoff_datetime"
        ] = pickup_temp.values

        # ----------------------------------------------------
        # Remove trips >24 hours
        # ----------------------------------------------------

        duration_hours = (
            filtered["lpep_dropoff_datetime"]
            - filtered["lpep_pickup_datetime"]
        ).dt.total_seconds() / 3600

        filtered = filtered.loc[
            duration_hours <= 24
        ].copy()

        # ----------------------------------------------------
        # Remove distance = 0 AND fare = 0
        # ----------------------------------------------------

        zero_both = (
            (filtered["trip_distance"] == 0)
            & (filtered["fare_amount"] == 0)
        )

        filtered = filtered.loc[
            ~zero_both
        ].copy()

        checked_after_filters += len(filtered)

        # ----------------------------------------------------
        # FINANCIAL CONDITION
        #
        # Identify records where:
        # - at least one financial value is negative
        # - all available financial values are <= 0
        #
        # This is the condition our original script
        # classified as Corrected_AllNegativeFinancial.
        # ----------------------------------------------------

        financial_columns = [
            "fare_amount",
            "extra",
            "mta_tax",
            "tip_amount",
            "tolls_amount",
            "improvement_surcharge",
            "total_amount",
            "congestion_surcharge"
        ]

        has_negative = (
            filtered[financial_columns]
            .lt(0)
            .any(axis=1)
        )

        all_non_positive = (
            filtered[financial_columns]
            .fillna(0)
            .le(0)
            .all(axis=1)
        )

        financial_mask = (
            has_negative
            & all_non_positive
        )

        matches = filtered.loc[
            financial_mask
        ].copy()

        financial_matches += len(matches)

        # Keep samples for manual inspection
        if len(matches) > 0:

            remaining = 30 - len(samples)

            if remaining > 0:

                samples.extend(
                    matches[
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
                    .head(remaining)
                    .to_dict("records")
                )

    print(f"Records after population filters: {checked_after_filters:,}")
    print(f"Financial correction candidates: {financial_matches:,}")
    print()

    results.append({
        "SourceYear": source_year,
        "RecordsAfterPopulationFilters": checked_after_filters,
        "FinancialCorrectionCandidates": financial_matches
    })


# ============================================================
# SAVE RESULTS
# ============================================================

summary = pd.DataFrame(results)

summary_file = (
    OUTPUT_FOLDER
    / "Taxi_838_Financial_Validation_Summary.csv"
)

summary.to_csv(
    summary_file,
    index=False
)

sample_file = (
    OUTPUT_FOLDER
    / "Taxi_838_Financial_Validation_Sample.csv"
)

pd.DataFrame(samples).to_csv(
    sample_file,
    index=False
)


print("=" * 70)
print("FINAL VALIDATION")
print("=" * 70)

print(summary.to_string(index=False))

print()
print(
    "TOTAL FINANCIAL CORRECTION CANDIDATES:",
    f"{summary['FinancialCorrectionCandidates'].sum():,}"
)

print()
print(f"Summary saved to: {summary_file}")
print(f"Sample saved to : {sample_file}")
print("=" * 70)