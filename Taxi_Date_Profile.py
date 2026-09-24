import pandas as pd
import os

BASE = r"C:\Users\Asus\OneDrive\Desktop\Maven Taxi\taxi_trips"

FILES = {
    2017: os.path.join(BASE, "2017_taxi_trips.csv"),
    2018: os.path.join(BASE, "2018_taxi_trips.csv"),
    2019: os.path.join(BASE, "2019_taxi_trips.csv"),
    2020: os.path.join(BASE, "2020_taxi_trips.csv"),
}

for expected_year, filepath in FILES.items():

    print("\n" + "=" * 60)
    print(f"FILE: {expected_year}")
    print("=" * 60)

    year_counts = {}

    for chunk in pd.read_csv(
        filepath,
        chunksize=200_000,
        low_memory=False
    ):

        pickup = pd.to_datetime(
            chunk["lpep_pickup_datetime"],
            errors="coerce"
        )

        years = pickup.dt.year.value_counts(dropna=False)

        for year, count in years.items():

            key = "Invalid/NaT" if pd.isna(year) else int(year)

            year_counts[key] = year_counts.get(key, 0) + int(count)

    for year, count in sorted(
        year_counts.items(),
        key=lambda x: str(x[0])
    ):

        print(f"{year}: {count:,}")

    print("\nExpected year:", expected_year)

    valid = year_counts.get(expected_year, 0)

    total = sum(year_counts.values())

    print(f"Records in expected year: {valid:,}")
    print(f"Total records: {total:,}")

    if total > 0:
        print(
            f"Expected-year percentage: "
            f"{valid / total * 100:.2f}%"
        )