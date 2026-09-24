import pandas as pd
from pathlib import Path

BASE = Path(r"C:\Users\Asus\OneDrive\Desktop\Maven Taxi")

TRIP_FILES = [
    BASE / "taxi_trips" / "2017_taxi_trips.csv",
    BASE / "taxi_trips" / "2018_taxi_trips.csv",
    BASE / "taxi_trips" / "2019_taxi_trips.csv",
    BASE / "taxi_trips" / "2020_taxi_trips.csv"
]

ZONE_FILE = BASE / "taxi_zones.csv"

CHUNK_SIZE = 200_000


# ---------------------------------------------------------
# 1. Load valid Taxi Zone IDs
# ---------------------------------------------------------

zones = pd.read_csv(ZONE_FILE)

valid_zone_ids = set(
    pd.to_numeric(zones["LocationID"], errors="coerce")
    .dropna()
    .astype(int)
)

print(f"Valid Taxi Zone IDs found: {len(valid_zone_ids)}")
print()


# ---------------------------------------------------------
# 2. Check every trip file
# ---------------------------------------------------------

results = []

for file in TRIP_FILES:

    print(f"Checking: {file.name}")

    total_rows = 0
    unknown_pickup = 0
    unknown_dropoff = 0

    unknown_pickup_ids = {}
    unknown_dropoff_ids = {}

    for chunk in pd.read_csv(
        file,
        usecols=["PULocationID", "DOLocationID"],
        chunksize=CHUNK_SIZE
    ):

        total_rows += len(chunk)

        pickup_ids = pd.to_numeric(
            chunk["PULocationID"],
            errors="coerce"
        )

        dropoff_ids = pd.to_numeric(
            chunk["DOLocationID"],
            errors="coerce"
        )

        # Unknown pickup zones
        pickup_unknown_mask = (
            pickup_ids.notna()
            & ~pickup_ids.isin(valid_zone_ids)
        )

        unknown_pickup += pickup_unknown_mask.sum()

        for zone_id, count in pickup_ids[pickup_unknown_mask].value_counts().items():
            unknown_pickup_ids[int(zone_id)] = (
                unknown_pickup_ids.get(int(zone_id), 0) + int(count)
            )

        # Unknown dropoff zones
        dropoff_unknown_mask = (
            dropoff_ids.notna()
            & ~dropoff_ids.isin(valid_zone_ids)
        )

        unknown_dropoff += dropoff_unknown_mask.sum()

        for zone_id, count in dropoff_ids[dropoff_unknown_mask].value_counts().items():
            unknown_dropoff_ids[int(zone_id)] = (
                unknown_dropoff_ids.get(int(zone_id), 0) + int(count)
            )

    results.append({
        "File": file.name,
        "Rows": total_rows,
        "UnknownPickup": unknown_pickup,
        "UnknownPickupPct": unknown_pickup / total_rows * 100,
        "UnknownDropoff": unknown_dropoff,
        "UnknownDropoffPct": unknown_dropoff / total_rows * 100,
        "UniqueUnknownPickupIDs": len(unknown_pickup_ids),
        "UniqueUnknownDropoffIDs": len(unknown_dropoff_ids)
    })

    print(f"Rows: {total_rows:,}")
    print(f"Unknown pickup: {unknown_pickup:,}")
    print(f"Unknown dropoff: {unknown_dropoff:,}")
    print()


# ---------------------------------------------------------
# 3. Save summary
# ---------------------------------------------------------

result_df = pd.DataFrame(results)

output_file = BASE / "Taxi_UnknownZone_Check.csv"

result_df.to_csv(output_file, index=False)

print("=" * 60)
print("FINAL SUMMARY")
print("=" * 60)

print(result_df.to_string(index=False))

print()
print(f"Saved to: {output_file}")