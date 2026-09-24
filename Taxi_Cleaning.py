import pandas as pd
from pathlib import Path


# ============================================================
# MAVEN TAXI PROJECT
# DATA CLEANING PIPELINE
# ============================================================
#
# Purpose:
# Create a clean analytical version of the 2017–2020
# NYC Green Taxi trip data using the documented
# Maven Taxi Challenge cleaning rules.
#
# IMPORTANT:
# - Original CSV files are NEVER modified.
# - Processing is done in chunks to avoid loading
#   28M+ records into memory.
# - An audit report is created for every major action.
#
# ============================================================


# ============================================================
# 1. PROJECT FOLDERS
# ============================================================

BASE = Path(r"C:\Users\Asus\OneDrive\Desktop\Maven Taxi")

RAW_FOLDER = BASE / "taxi_trips"

OUTPUT_FOLDER = BASE / "New CSV by Python"

OUTPUT_FOLDER.mkdir(exist_ok=True)


# ============================================================
# 2. INPUT FILES
# ============================================================

TRIP_FILES = [
    RAW_FOLDER / "2017_taxi_trips.csv",
    RAW_FOLDER / "2018_taxi_trips.csv",
    RAW_FOLDER / "2019_taxi_trips.csv",
    RAW_FOLDER / "2020_taxi_trips.csv"
]


# ============================================================
# 3. SETTINGS
# ============================================================

CHUNK_SIZE = 200_000


# ============================================================
# 4. EXPECTED COLUMNS
# ============================================================

BASE_COLUMNS = [
    "VendorID",
    "lpep_pickup_datetime",
    "lpep_dropoff_datetime",
    "store_and_fwd_flag",
    "RatecodeID",
    "PULocationID",
    "DOLocationID",
    "passenger_count",
    "trip_distance",
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


# ============================================================
# 5. LOAD VALID TAXI ZONES
# ============================================================

print("=" * 70)
print("LOADING TAXI ZONES")
print("=" * 70)

zones = pd.read_csv(BASE / "taxi_zones.csv")

valid_zone_ids = set(
    pd.to_numeric(
        zones["LocationID"],
        errors="coerce"
    )
    .dropna()
    .astype(int)
)

print(f"Valid zone IDs: {len(valid_zone_ids)}")
print()


# ============================================================
# 6. CLEANING FUNCTION
# ============================================================

def clean_chunk(df, source_year, audit):

    original_rows = len(df)

    # --------------------------------------------------------
    # Standardize schema
    # --------------------------------------------------------

    if "congestion_surcharge" not in df.columns:
        df["congestion_surcharge"] = pd.NA

    df["SourceYear"] = source_year


    # --------------------------------------------------------
    # Convert data types
    # --------------------------------------------------------

    df["lpep_pickup_datetime"] = pd.to_datetime(
        df["lpep_pickup_datetime"],
        errors="coerce"
    )

    df["lpep_dropoff_datetime"] = pd.to_datetime(
        df["lpep_dropoff_datetime"],
        errors="coerce"
    )


    numeric_columns = [
        "VendorID",
        "RatecodeID",
        "PULocationID",
        "DOLocationID",
        "passenger_count",
        "trip_distance",
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

    for col in numeric_columns:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )


    # ========================================================
    # AUDIT: ORIGINAL ROW COUNT
    # ========================================================

    audit["OriginalRows"] += original_rows


    # ========================================================
    # RULE 1
    # EXPECTED SOURCE YEAR
    # ========================================================

    invalid_year = (
        df["lpep_pickup_datetime"].dt.year != source_year
    )

    invalid_year &= df["lpep_pickup_datetime"].notna()

    count = int(invalid_year.sum())

    audit["Excluded_WrongYear"] += count

    df = df.loc[~invalid_year].copy()


    # ========================================================
    # RULE 2
    # INVALID DATETIME
    # ========================================================

    invalid_datetime = (
        df["lpep_pickup_datetime"].isna()
        | df["lpep_dropoff_datetime"].isna()
    )

    count = int(invalid_datetime.sum())

    audit["Excluded_InvalidDatetime"] += count

    df = df.loc[~invalid_datetime].copy()


    # ========================================================
    # RULE 3
    # UNKNOWN ZONES
    # ========================================================

    unknown_pickup = (
        ~df["PULocationID"].isin(valid_zone_ids)
    )

    unknown_dropoff = (
        ~df["DOLocationID"].isin(valid_zone_ids)
    )

    unknown_zone = unknown_pickup | unknown_dropoff

    count = int(unknown_zone.sum())

    audit["Excluded_UnknownZone"] += count

    df = df.loc[~unknown_zone].copy()


    # ========================================================
    # RULE 4
    # PASSENGER COUNT
    #
    # Maven rule:
    # Missing passenger count → assume 1
    # ========================================================

    missing_passengers = df["passenger_count"].isna()

    count = int(missing_passengers.sum())

    audit["Corrected_MissingPassenger"] += count

    df.loc[missing_passengers, "passenger_count"] = 1


    # ========================================================
    # RULE 5
    # STORE & FORWARD
    #
    # Remove trips where store_and_fwd_flag = Y
    # ========================================================

    store_forward = (
        df["store_and_fwd_flag"]
        .astype("string")
        .str.upper()
        .eq("Y")
    )

    count = int(store_forward.sum())

    audit["Excluded_StoreForward"] += count

    df = df.loc[~store_forward].copy()


    # ========================================================
    # RULE 6
    # RATE CODE
    #
    # Keep Standard Rate only
    # ========================================================

    invalid_rate = df["RatecodeID"] != 1

    count = int(invalid_rate.sum())

    audit["Excluded_NonStandardRate"] += count

    df = df.loc[~invalid_rate].copy()


    # ========================================================
    # RULE 7
    # PAYMENT TYPE
    #
    # Keep:
    # 1 = Credit Card
    # 2 = Cash
    # ========================================================

    invalid_payment = ~df["payment_type"].isin([1, 2])

    count = int(invalid_payment.sum())

    audit["Excluded_InvalidPayment"] += count

    df = df.loc[~invalid_payment].copy()


    # ========================================================
    # RULE 8
    # TRIP TYPE
    #
    # Keep:
    # 1 = Street Hail
    # ========================================================

    invalid_trip_type = df["trip_type"] != 1

    count = int(invalid_trip_type.sum())

    audit["Excluded_NonStreetHail"] += count

    df = df.loc[~invalid_trip_type].copy()


    # ========================================================
    # RULE 9
    # INCORRECT TIMESTAMP ORDER
    #
    # If pickup > dropoff:
    # swap them
    # ========================================================

    reversed_time = (
        df["lpep_pickup_datetime"]
        > df["lpep_dropoff_datetime"]
    )

    count = int(reversed_time.sum())

    audit["Corrected_ReversedTimestamps"] += count

    pickup_temp = df.loc[
        reversed_time,
        "lpep_pickup_datetime"
    ].copy()

    df.loc[
        reversed_time,
        "lpep_pickup_datetime"
    ] = df.loc[
        reversed_time,
        "lpep_dropoff_datetime"
    ].values

    df.loc[
        reversed_time,
        "lpep_dropoff_datetime"
    ] = pickup_temp.values


    # ========================================================
    # RULE 10
    # TRIP DURATION
    # ========================================================

    duration_hours = (
        df["lpep_dropoff_datetime"]
        - df["lpep_pickup_datetime"]
    ).dt.total_seconds() / 3600


    # ========================================================
    # RULE 11
    # REMOVE TRIPS > 24 HOURS
    # ========================================================

    too_long = duration_hours > 24

    count = int(too_long.sum())

    audit["Excluded_Over24Hours"] += count

    df = df.loc[~too_long].copy()


    # ========================================================
    # RULE 12
    # ZERO DISTANCE + ZERO FARE
    #
    # Remove records where BOTH are zero.
    # ========================================================

    zero_distance_zero_fare = (
        (df["trip_distance"] == 0)
        & (df["fare_amount"] == 0)
    )

    count = int(zero_distance_zero_fare.sum())

    audit["Excluded_ZeroDistanceZeroFare"] += count

    df = df.loc[~zero_distance_zero_fare].copy()


    # ========================================================
    # RULE 13
    # ZERO DISTANCE BUT POSITIVE FARE
    #
    # Distance = (Fare - 2.5) / 2.5
    # ========================================================

    recover_distance = (
        (df["trip_distance"] == 0)
        & (df["fare_amount"] > 0)
    )

    count = int(recover_distance.sum())

    audit["Corrected_ZeroDistance"] += count

    df.loc[
        recover_distance,
        "trip_distance"
    ] = (
        df.loc[recover_distance, "fare_amount"] - 2.5
    ) / 2.5


    # ========================================================
    # RULE 14
    # POSITIVE DISTANCE BUT ZERO FARE
    #
    # Fare = 2.5 + (distance × 2.5)
    # ========================================================

    recover_fare = (
        (df["trip_distance"] > 0)
        & (df["fare_amount"] == 0)
    )

    count = int(recover_fare.sum())

    audit["Corrected_ZeroFare"] += count

    df.loc[
        recover_fare,
        "fare_amount"
    ] = (
        2.5
        + (
            df.loc[recover_fare, "trip_distance"]
            * 2.5
        )
    )


    # ========================================================
    # RULE 15
    # NEGATIVE FINANCIAL VALUES
    #
    # If fare + taxes + surcharges are all negative,
    # make the applicable negative values positive.
    # ========================================================

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

    available_financial_columns = [
        col for col in financial_columns
        if col in df.columns
    ]

    negative_mask = (
        df[available_financial_columns]
        .notna()
        .any(axis=1)
    )

    for col in available_financial_columns:
        negative_mask &= (
            df[col].fillna(0) <= 0
        )

    count = int(negative_mask.sum())

    audit["Corrected_AllNegativeFinancial"] += count

    for col in available_financial_columns:
        df.loc[
            negative_mask & (df[col] < 0),
            col
        ] = df.loc[
            negative_mask & (df[col] < 0),
            col
        ].abs()


    # ========================================================
    # FINAL ROW COUNT
    # ========================================================

    audit["FinalRows"] += len(df)


    # ========================================================
    # SELECT FINAL COLUMNS
    # ========================================================

    final_columns = [
        "VendorID",
        "lpep_pickup_datetime",
        "lpep_dropoff_datetime",
        "store_and_fwd_flag",
        "RatecodeID",
        "PULocationID",
        "DOLocationID",
        "passenger_count",
        "trip_distance",
        "fare_amount",
        "extra",
        "mta_tax",
        "tip_amount",
        "tolls_amount",
        "improvement_surcharge",
        "total_amount",
        "payment_type",
        "trip_type",
        "congestion_surcharge",
        "SourceYear"
    ]

    return df[final_columns]


# ============================================================
# 7. PROCESS EACH YEAR
# ============================================================

all_audits = []


for trip_file in TRIP_FILES:

    source_year = int(trip_file.stem[:4])

    print("=" * 70)
    print(f"PROCESSING {source_year}")
    print("=" * 70)

    output_file = (
        OUTPUT_FOLDER
        / f"taxi_cleaned_{source_year}.csv"
    )

    # Remove existing output if present
    if output_file.exists():
        output_file.unlink()

    audit = {
        "SourceYear": source_year,
        "OriginalRows": 0,
        "Excluded_WrongYear": 0,
        "Excluded_InvalidDatetime": 0,
        "Excluded_UnknownZone": 0,
        "Corrected_MissingPassenger": 0,
        "Excluded_StoreForward": 0,
        "Excluded_NonStandardRate": 0,
        "Excluded_InvalidPayment": 0,
        "Excluded_NonStreetHail": 0,
        "Corrected_ReversedTimestamps": 0,
        "Excluded_Over24Hours": 0,
        "Excluded_ZeroDistanceZeroFare": 0,
        "Corrected_ZeroDistance": 0,
        "Corrected_ZeroFare": 0,
        "Corrected_AllNegativeFinancial": 0,
        "FinalRows": 0
    }

    first_chunk = True

    for chunk_number, chunk in enumerate(
        pd.read_csv(
            trip_file,
            chunksize=CHUNK_SIZE
        ),
        start=1
    ):

        cleaned = clean_chunk(
            chunk,
            source_year,
            audit
        )

        if len(cleaned) > 0:

            cleaned.to_csv(
                output_file,
                mode="w" if first_chunk else "a",
                header=first_chunk,
                index=False
            )

            first_chunk = False

        if chunk_number % 10 == 0:
            print(
                f"  Processed chunk {chunk_number:,} | "
                f"Rows read: {audit['OriginalRows']:,}"
            )

    all_audits.append(audit)

    print()
    print(f"Original rows : {audit['OriginalRows']:,}")
    print(f"Final rows    : {audit['FinalRows']:,}")
    print(
        f"Rows removed  : "
        f"{audit['OriginalRows'] - audit['FinalRows']:,}"
    )
    print(f"Output file   : {output_file}")
    print()


# ============================================================
# 8. CREATE AUDIT REPORT
# ============================================================

audit_df = pd.DataFrame(all_audits)

audit_file = (
    OUTPUT_FOLDER
    / "Taxi_Cleaning_Audit.csv"
)

audit_df.to_csv(
    audit_file,
    index=False
)


# ============================================================
# 9. PROJECT TOTALS
# ============================================================

print("=" * 70)
print("CLEANING COMPLETE")
print("=" * 70)

total_original = audit_df["OriginalRows"].sum()
total_final = audit_df["FinalRows"].sum()

print(f"Total original rows : {total_original:,}")
print(f"Total final rows    : {total_final:,}")
print(
    f"Total removed       : "
    f"{total_original - total_final:,}"
)

print()
print(f"Audit report:")
print(audit_file)

print()
print("Generated files:")
for file in sorted(OUTPUT_FOLDER.glob("taxi_cleaned_*.csv")):
    print(f"  {file.name}")

print()
print("The original raw files were NOT modified.")
print("=" * 70)