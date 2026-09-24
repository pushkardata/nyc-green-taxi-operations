import pandas as pd
import os

BASE = r"C:\Users\Asus\OneDrive\Desktop\Maven Taxi\taxi_trips"

FILES = {
    2017: os.path.join(BASE, "2017_taxi_trips.csv"),
    2018: os.path.join(BASE, "2018_taxi_trips.csv"),
    2019: os.path.join(BASE, "2019_taxi_trips.csv"),
    2020: os.path.join(BASE, "2020_taxi_trips.csv"),
}

all_results = []

for year, filepath in FILES.items():

    print(f"\n{'=' * 60}")
    print(f"PROCESSING {year}")
    print(f"{'=' * 60}")

    total_rows = 0

    min_pickup = None
    max_pickup = None

    missing_passenger = 0
    missing_pickup = 0
    missing_dropoff = 0

    zero_distance = 0
    negative_distance = 0

    zero_fare = 0
    negative_fare = 0
    negative_total = 0

    store_forward_y = 0

    rate_counts = {}
    payment_counts = {}
    trip_type_counts = {}
    vendor_counts = {}

    # Read large file in manageable chunks
    for chunk in pd.read_csv(
        filepath,
        chunksize=200_000,
        low_memory=False
    ):

        total_rows += len(chunk)

        # -------------------------
        # Date range
        # -------------------------

        pickup = pd.to_datetime(
            chunk["lpep_pickup_datetime"],
            errors="coerce"
        )

        chunk_min = pickup.min()
        chunk_max = pickup.max()

        if pd.notna(chunk_min):
            if min_pickup is None or chunk_min < min_pickup:
                min_pickup = chunk_min

        if pd.notna(chunk_max):
            if max_pickup is None or chunk_max > max_pickup:
                max_pickup = chunk_max

        # -------------------------
        # Missing values
        # -------------------------

        missing_passenger += chunk["passenger_count"].isna().sum()
        missing_pickup += chunk["PULocationID"].isna().sum()
        missing_dropoff += chunk["DOLocationID"].isna().sum()

        # -------------------------
        # Distance checks
        # -------------------------

        zero_distance += (chunk["trip_distance"] == 0).sum()
        negative_distance += (chunk["trip_distance"] < 0).sum()

        # -------------------------
        # Fare checks
        # -------------------------

        zero_fare += (chunk["fare_amount"] == 0).sum()
        negative_fare += (chunk["fare_amount"] < 0).sum()
        negative_total += (chunk["total_amount"] < 0).sum()

        # -------------------------
        # Store and forward
        # -------------------------

        store_forward_y += (
            chunk["store_and_fwd_flag"] == "Y"
        ).sum()

        # -------------------------
        # Category distributions
        # -------------------------

        for value, count in chunk["RatecodeID"].value_counts(
            dropna=False
        ).items():

            rate_counts[value] = rate_counts.get(value, 0) + count

        for value, count in chunk["payment_type"].value_counts(
            dropna=False
        ).items():

            payment_counts[value] = payment_counts.get(value, 0) + count

        for value, count in chunk["trip_type"].value_counts(
            dropna=False
        ).items():

            trip_type_counts[value] = trip_type_counts.get(value, 0) + count

        for value, count in chunk["VendorID"].value_counts(
            dropna=False
        ).items():

            vendor_counts[value] = vendor_counts.get(value, 0) + count

        print(
            f"\rRows processed: {total_rows:,}",
            end=""
        )

    print("\nFinished.")

    all_results.append({
        "Year": year,
        "Rows": total_rows,
        "MinPickup": min_pickup,
        "MaxPickup": max_pickup,
        "MissingPassenger": missing_passenger,
        "MissingPickupZone": missing_pickup,
        "MissingDropoffZone": missing_dropoff,
        "ZeroDistance": zero_distance,
        "NegativeDistance": negative_distance,
        "ZeroFare": zero_fare,
        "NegativeFare": negative_fare,
        "NegativeTotal": negative_total,
        "StoreForward_Y": store_forward_y,
        "RateCodes": str(rate_counts),
        "PaymentTypes": str(payment_counts),
        "TripTypes": str(trip_type_counts),
        "Vendors": str(vendor_counts),
    })


# -----------------------------
# Create final profile report
# -----------------------------

profile = pd.DataFrame(all_results)

output_path = r"C:\Users\Asus\OneDrive\Desktop\Maven Taxi\Taxi_Profile_Pass1.csv"

profile.to_csv(output_path, index=False)

print("\n")
print("=" * 60)
print("PROFILE COMPLETE")
print("=" * 60)

print(profile.to_string(index=False))

print("\nReport saved to:")
print(output_path)