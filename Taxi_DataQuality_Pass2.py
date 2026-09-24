import pandas as pd
import os

BASE = r"C:\Users\Asus\OneDrive\Desktop\Maven Taxi\taxi_trips"

FILES = {
    2017: os.path.join(BASE, "2017_taxi_trips.csv"),
    2018: os.path.join(BASE, "2018_taxi_trips.csv"),
    2019: os.path.join(BASE, "2019_taxi_trips.csv"),
    2020: os.path.join(BASE, "2020_taxi_trips.csv"),
}

results = []

for year, filepath in FILES.items():

    print("\n" + "=" * 65)
    print(f"PROCESSING {year}")
    print("=" * 65)

    total = 0

    missing_passenger = 0
    missing_pickup_zone = 0
    missing_dropoff_zone = 0

    zero_distance = 0
    negative_distance = 0

    zero_fare = 0
    negative_fare = 0
    negative_total = 0

    store_forward_y = 0

    negative_duration = 0
    zero_duration = 0
    over_24_hours = 0

    invalid_pickup_datetime = 0
    invalid_dropoff_datetime = 0

    # Correctly aggregate categorical values
    rate_counts = {}
    payment_counts = {}
    trip_type_counts = {}
    vendor_counts = {}

    for chunk in pd.read_csv(
        filepath,
        chunksize=200_000,
        low_memory=False
    ):

        total += len(chunk)

        # -------------------------
        # Datetime
        # -------------------------

        pickup = pd.to_datetime(
            chunk["lpep_pickup_datetime"],
            errors="coerce"
        )

        dropoff = pd.to_datetime(
            chunk["lpep_dropoff_datetime"],
            errors="coerce"
        )

        invalid_pickup_datetime += pickup.isna().sum()
        invalid_dropoff_datetime += dropoff.isna().sum()

        duration_minutes = (
            (dropoff - pickup).dt.total_seconds() / 60
        )

        negative_duration += (
            duration_minutes < 0
        ).sum()

        zero_duration += (
            duration_minutes == 0
        ).sum()

        over_24_hours += (
            duration_minutes > 1440
        ).sum()

        # -------------------------
        # Missing values
        # -------------------------

        missing_passenger += (
            chunk["passenger_count"].isna()
        ).sum()

        missing_pickup_zone += (
            chunk["PULocationID"].isna()
        ).sum()

        missing_dropoff_zone += (
            chunk["DOLocationID"].isna()
        ).sum()

        # -------------------------
        # Distance
        # -------------------------

        zero_distance += (
            chunk["trip_distance"] == 0
        ).sum()

        negative_distance += (
            chunk["trip_distance"] < 0
        ).sum()

        # -------------------------
        # Fare
        # -------------------------

        zero_fare += (
            chunk["fare_amount"] == 0
        ).sum()

        negative_fare += (
            chunk["fare_amount"] < 0
        ).sum()

        negative_total += (
            chunk["total_amount"] < 0
        ).sum()

        # -------------------------
        # Store & forward
        # -------------------------

        store_forward_y += (
            chunk["store_and_fwd_flag"] == "Y"
        ).sum()

        # -------------------------
        # Category counts
        # -------------------------

        for value, count in chunk["RatecodeID"].value_counts(
            dropna=False
        ).items():

            value = str(value)
            rate_counts[value] = rate_counts.get(value, 0) + int(count)

        for value, count in chunk["payment_type"].value_counts(
            dropna=False
        ).items():

            value = str(value)
            payment_counts[value] = payment_counts.get(value, 0) + int(count)

        for value, count in chunk["trip_type"].value_counts(
            dropna=False
        ).items():

            value = str(value)
            trip_type_counts[value] = trip_type_counts.get(value, 0) + int(count)

        for value, count in chunk["VendorID"].value_counts(
            dropna=False
        ).items():

            value = str(value)
            vendor_counts[value] = vendor_counts.get(value, 0) + int(count)

        print(
            f"\rRows processed: {total:,}",
            end=""
        )

    print("\nFinished.")

    def pct(value):
        return round(value / total * 100, 4) if total else 0

    results.append({

        "Year": year,
        "TotalRows": total,

        "MissingPassenger": missing_passenger,
        "MissingPassengerPct": pct(missing_passenger),

        "MissingPickupZone": missing_pickup_zone,
        "MissingPickupZonePct": pct(missing_pickup_zone),

        "MissingDropoffZone": missing_dropoff_zone,
        "MissingDropoffZonePct": pct(missing_dropoff_zone),

        "ZeroDistance": zero_distance,
        "ZeroDistancePct": pct(zero_distance),

        "NegativeDistance": negative_distance,
        "NegativeDistancePct": pct(negative_distance),

        "ZeroFare": zero_fare,
        "ZeroFarePct": pct(zero_fare),

        "NegativeFare": negative_fare,
        "NegativeFarePct": pct(negative_fare),

        "NegativeTotal": negative_total,
        "NegativeTotalPct": pct(negative_total),

        "StoreForwardY": store_forward_y,
        "StoreForwardYPct": pct(store_forward_y),

        "NegativeDuration": negative_duration,
        "NegativeDurationPct": pct(negative_duration),

        "ZeroDuration": zero_duration,
        "ZeroDurationPct": pct(zero_duration),

        "Over24Hours": over_24_hours,
        "Over24HoursPct": pct(over_24_hours),

        "InvalidPickupDatetime": invalid_pickup_datetime,
        "InvalidPickupDatetimePct": pct(invalid_pickup_datetime),

        "InvalidDropoffDatetime": invalid_dropoff_datetime,
        "InvalidDropoffDatetimePct": pct(invalid_dropoff_datetime),

        "RateCodes": str(rate_counts),
        "PaymentTypes": str(payment_counts),
        "TripTypes": str(trip_type_counts),
        "Vendors": str(vendor_counts)
    })


profile = pd.DataFrame(results)

output = r"C:\Users\Asus\OneDrive\Desktop\Maven Taxi\Taxi_DataQuality_Pass2.csv"

profile.to_csv(output, index=False)

print("\n" + "=" * 65)
print("DATA QUALITY PROFILE COMPLETE")
print("=" * 65)

print(profile.to_string(index=False))

print("\nSaved to:")
print(output)