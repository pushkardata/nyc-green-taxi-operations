/* ============================================================
   MAVEN TAXI — BUSINESS ANALYSIS
   Business Problem:
   Taxi Demand & Fleet Capacity Intelligence

   Objective:
   Analyze historical taxi demand across time and geography
   to support weekly fleet capacity planning.
   ============================================================ */


/* ============================================================
   SECTION 1 — HISTORICAL DEMAND TREND

   Business Question:
   How has green taxi trip volume changed from 2017–2020?

   Why are we executing this analysis?
   Before examining detailed demand patterns, we need to establish
   the overall historical direction and scale of taxi demand.

   KPI:
   Total Trips by Year
   ============================================================ */

SELECT
    SourceYear,
    COUNT(*) AS total_trips
FROM fact_taxi_trip
GROUP BY SourceYear
ORDER BY SourceYear;

/* ============================================================
   SECTION 2 — YEAR-OVER-YEAR DEMAND CHANGE

   Business Question:
   How much did green taxi trip volume change compared with
   the previous year?

   Why are we executing this analysis?
   Section 1 showed us the overall annual trip volumes.
   However, absolute trip counts alone do not tell us how
   significant the change was from one year to the next.

   Measuring the year-over-year (YoY) percentage change allows
   us to quantify the magnitude of annual demand movement.

   KPI:
   - Total Trips
   - Year-over-Year Trip Volume Change (%)

   Analytical Purpose:
   Determine whether changes in historical demand were relatively
   stable or whether some years experienced substantially larger
   changes than others.

   Important:
   This analysis describes historical demand movement only.
   It does not yet explain why the changes occurred.
   ============================================================ */
   WITH yearly_trips AS (
    SELECT
        SourceYear,
        COUNT(*) AS total_trips
    FROM fact_taxi_trip
    GROUP BY SourceYear
)
SELECT
    SourceYear,
    total_trips,
    LAG(total_trips) OVER (ORDER BY SourceYear) AS previous_year_trips,
    ROUND(
        (total_trips - LAG(total_trips) OVER (ORDER BY SourceYear))
        * 100.0
        / LAG(total_trips) OVER (ORDER BY SourceYear),
        2
    ) AS yoy_change_pct
FROM yearly_trips
ORDER BY SourceYear;

/* ============================================================
   SECTION 3 — DEMAND BY DAY OF WEEK

   Business Question:
   Which days of the week historically generate the highest
   and lowest green taxi trip volumes?

   Why are we executing this analysis?
   Section 1 established the overall historical demand trend,
   and Section 2 quantified the year-over-year changes.

   However, annual demand does not tell us when that demand
   occurs.

   For fleet capacity planning, the dispatcher needs to
   understand whether demand is distributed evenly across
   the week or concentrated on particular days.

   KPI:
   - Total Trips by Day of Week
   - Average Trips per Day of Week

   Analytical Purpose:
   Identify recurring weekly demand patterns that may have
   implications for fleet capacity planning.

   Important:
   This analysis describes historical demand patterns.
   It does not yet determine the required fleet size or
   explain why demand differs between days.
   ============================================================ */
   SELECT
    c.DayOfWeek,
    c.DayName,
    COUNT(*) AS total_trips,
    ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT DATE(t.lpep_pickup_datetime)), 0) AS average_trips_per_day
FROM fact_taxi_trip t
JOIN dim_calendar c
    ON DATE(t.lpep_pickup_datetime) = c.Date
GROUP BY
    c.DayOfWeek,
    c.DayName
ORDER BY
    c.DayOfWeek;

/* ============================================================
   SECTION 4 — DEMAND BY HOUR

   Business Question:
   Which hours of the day historically experience the highest
   and lowest green taxi trip volumes?

   Why are we executing this analysis?
   Section 3 showed that taxi demand varies by day of the week.
   However, daily totals do not show how demand is distributed
   throughout the day.

   For fleet capacity planning, understanding hourly demand is
   important because a high-demand day may still contain specific
   periods when additional fleet capacity is more relevant.

   KPI:
   - Total Trips by Hour
   - Average Trips per Hour

   Analytical Purpose:
   Identify recurring intraday demand patterns and determine
   whether taxi demand is concentrated during particular hours.

   Important:
   This analysis describes historical hourly demand.
   It does not yet determine the required fleet capacity or
   explain why demand is higher during particular hours.
   ============================================================ */
   SELECT EXTRACT(HOUR FROM t.lpep_pickup_datetime)::INTEGER AS pickup_hour, COUNT(*) AS total_trips, ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT DATE(t.lpep_pickup_datetime)), 0) AS average_trips_per_hour FROM fact_taxi_trip t GROUP BY EXTRACT(HOUR FROM t.lpep_pickup_datetime) ORDER BY pickup_hour;

/* ============================================================
   SECTION 5 — DAY × HOUR DEMAND

   Business Question:
   Which combinations of day of week and hour of day
   historically experience the highest and lowest demand?

   Why are we executing this analysis?
   Sections 3 and 4 established that demand varies by both
   day of week and hour of day.

   However, analyzing these dimensions independently can hide
   important operational patterns.

   For example, the busiest hour overall may not be equally
   busy on every day of the week.

   Combining day and hour allows us to identify specific
   recurring periods of higher or lower historical demand.

   KPI:
   - Total Trips
   - Average Trips per Day for each Day × Hour combination

   Analytical Purpose:
   Identify specific recurring day/time periods where historical
   demand is concentrated, providing a more detailed view of
   when fleet capacity may need to be planned.

   Important:
   This analysis describes historical demand concentration.
   It does not yet determine the required number of vehicles
   or establish a causal explanation for the observed pattern.
   ============================================================ */
SELECT c.DayOfWeek, c.DayName, EXTRACT(HOUR FROM t.lpep_pickup_datetime)::INTEGER AS pickup_hour, COUNT(*) AS total_trips, ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT DATE(t.lpep_pickup_datetime)), 0) AS average_trips_per_day FROM fact_taxi_trip t JOIN dim_calendar c ON DATE(t.lpep_pickup_datetime) = c.Date GROUP BY c.DayOfWeek, c.DayName, EXTRACT(HOUR FROM t.lpep_pickup_datetime) ORDER BY c.DayOfWeek, pickup_hour;

/* ============================================================
   SECTION 6 — PICKUP DEMAND BY BOROUGH

   Business Question:
   Which NYC boroughs generate the highest volume of green taxi
   pickup demand?

   Why are we executing this analysis?
   Sections 3–5 showed when demand is concentrated across the
   week and throughout the day.

   The next business question is where that demand originates.

   For a dispatcher responsible for fleet planning and
   logistics, understanding the geographic concentration of
   pickup demand can help identify areas where taxi demand is
   historically higher.

   KPI:
   - Total Trips by Pickup Borough
   - Average Trips per Day by Pickup Borough
   - Share of Total Trips (%)

   Analytical Purpose:
   Measure the geographic distribution of historical pickup
   demand and determine whether demand is concentrated in
   particular NYC boroughs.

   Data Treatment:
   EWR (Newark Airport) is retained in the analytical dataset
   but is not treated as an NYC borough.

   LocationIDs 264 and 265 are classified as Unknown in the
   taxi-zone dimension. They are retained in the dataset but
   excluded from the borough comparison because they cannot
   be assigned to an NYC borough.

   Important:
   This analysis describes where trips originated.
   It does not yet analyze destination patterns, routes, or
   explain why demand differs between boroughs.
   ============================================================ */
SELECT
    z.Borough AS pickup_borough,
    COUNT(*) AS total_trips,
    ROUND(
        COUNT(*) * 1.0
        / COUNT(DISTINCT DATE(t.lpep_pickup_datetime)),
        0
    ) AS average_trips_per_day,
    ROUND(
        COUNT(*) * 100.0
        / SUM(COUNT(*)) OVER (),
        2
    ) AS trip_share_pct
FROM fact_taxi_trip t
JOIN dim_taxi_zone z
    ON t.PULocationID = z.LocationID
WHERE z.Borough IN (
    'Manhattan',
    'Brooklyn',
    'Queens',
    'Bronx',
    'Staten Island'
)
GROUP BY
    z.Borough
ORDER BY
    total_trips DESC;

	/* ============================================================
   SECTION 7 — WITHIN-BOROUGH VS. CROSS-BOROUGH TRIPS

   Business Question:
   Do taxi trips generally remain within the same borough,
   or do they travel between different NYC boroughs?

   Why are we executing this analysis?
   Section 6 showed that pickup demand is concentrated mainly
   in Manhattan, Brooklyn, and Queens.

   However, pickup concentration alone does not tell us how
   vehicles move through the network.

   A trip can:
   - Start and end in the same borough, or
   - Start in one borough and end in another.

   Understanding this distinction helps us assess whether
   demand is primarily local or involves movement between
   geographic demand areas.

   KPI:
   - Total Trips
   - Share of Trips (%)
   - Within-Borough Trips
   - Cross-Borough Trips

   Analytical Purpose:
   Determine the historical proportion of trips that remain
   within the pickup borough versus trips that cross borough
   boundaries.

   Data Treatment:
   Only trips where both pickup and dropoff locations can be
   assigned to one of the five NYC boroughs are included in
   this comparison.

   EWR and Unknown locations are excluded from this specific
   analysis because they cannot be classified as one of the
   five NYC boroughs.

   Important:
   This analysis describes historical trip movement.
   It does not yet identify specific routes or explain why
   passengers travel between boroughs.
   ============================================================ */
SELECT
    CASE
        WHEN pickup.Borough = dropoff.Borough
            THEN 'Within-Borough'
        ELSE 'Cross-Borough'
    END AS trip_type,
    COUNT(*) AS total_trips,
    ROUND(
        COUNT(*) * 100.0
        / SUM(COUNT(*)) OVER (),
        2
    ) AS trip_share_pct
FROM fact_taxi_trip t
JOIN dim_taxi_zone pickup
    ON t.PULocationID = pickup.LocationID
JOIN dim_taxi_zone dropoff
    ON t.DOLocationID = dropoff.LocationID
WHERE pickup.Borough IN (
    'Manhattan',
    'Brooklyn',
    'Queens',
    'Bronx',
    'Staten Island'
)
AND dropoff.Borough IN (
    'Manhattan',
    'Brooklyn',
    'Queens',
    'Bronx',
    'Staten Island'
)
GROUP BY
    CASE
        WHEN pickup.Borough = dropoff.Borough
            THEN 'Within-Borough'
        ELSE 'Cross-Borough'
    END
ORDER BY
    total_trips DESC;

	/* ============================================================
   SECTION 8 — BOROUGH-TO-BOROUGH ROUTES
   ============================================================

   BUSINESS QUESTION:
   Which borough-to-borough routes generate the most
   cross-borough green taxi trips?

   WHY ARE WE EXECUTING THIS ANALYSIS?
   Section 7 showed that 14.07% of valid five-borough trips
   cross borough boundaries. We now need to determine whether
   this cross-borough demand is concentrated in particular
   origin-destination pairs.

   KPI:
   - Total cross-borough trips
   - Share of all cross-borough trips (%)

   ANALYTICAL PURPOSE:
   Identify the main historical cross-borough travel routes
   that may be relevant for geographic fleet planning.

   DATA TREATMENT:
   - Pickup and dropoff must both belong to one of the five
     NYC boroughs.
   - EWR and Unknown are excluded because they are not one
     of the five NYC boroughs.
   - Same-borough trips are excluded.
   - Route share is calculated against ALL cross-borough
     trips, so route shares should sum to approximately 100%.

   IMPORTANT LIMITATION:
   This identifies historical route concentration. It does
   not explain why these routes are busy or determine the
   required fleet capacity for each route.
   ============================================================ */
WITH cross_borough_trips AS (
    SELECT
        pickup.Borough AS pickup_borough,
        dropoff.Borough AS dropoff_borough
    FROM fact_taxi_trip t
    JOIN dim_taxi_zone pickup
        ON t.PULocationID = pickup.LocationID
    JOIN dim_taxi_zone dropoff
        ON t.DOLocationID = dropoff.LocationID
    WHERE pickup.Borough IN (
        'Manhattan',
        'Brooklyn',
        'Queens',
        'Bronx',
        'Staten Island'
    )
    AND dropoff.Borough IN (
        'Manhattan',
        'Brooklyn',
        'Queens',
        'Bronx',
        'Staten Island'
    )
    AND pickup.Borough <> dropoff.Borough
)

SELECT
    pickup_borough,
    dropoff_borough,
    COUNT(*) AS total_trips,
    ROUND(
        COUNT(*) * 100.0
        / SUM(COUNT(*)) OVER (),
        2
    ) AS route_share_pct
FROM cross_borough_trips
GROUP BY
    pickup_borough,
    dropoff_borough
ORDER BY
    total_trips DESC;

/* ============================================================
   SECTION 9 — DEMAND CONCENTRATION & FLEET CAPACITY
   ============================================================

   BUSINESS QUESTION:
   How concentrated is historical taxi demand during the
   busiest recurring operating periods?

   WHY ARE WE EXECUTING THIS ANALYSIS?
   Sections 3–5 showed that demand varies by day and hour.
   Section 5 also identified specific day × hour combinations
   with substantially different demand levels.

   For fleet planning, we need to quantify how much demand
   occurs during the highest-volume operating periods.

   KPI:
   - Total trips by day × hour
   - Average trips per occurrence of that day × hour
   - Share of total trips

   ANALYTICAL PURPOSE:
   Measure demand concentration across recurring weekly
   operating periods.

   DATA TREATMENT:
   - Uses the same cleaned analytical population as previous
     sections.
   - Day of week is obtained from dim_calendar.
   - Historical demand is measured using observed trip volume.

   IMPORTANT LIMITATION:
   Trip demand does not directly equal fleet capacity
   requirements. The dataset does not provide the number of
   available/on-duty taxis, utilization, wait times, or
   unmet demand. Therefore, this analysis measures demand
   concentration rather than calculating a required fleet size.
   ============================================================ */
WITH day_hour_demand AS (
    SELECT
        c.DayOfWeek,
        c.DayName,
        EXTRACT(HOUR FROM t.lpep_pickup_datetime)::INTEGER
            AS pickup_hour,
        COUNT(*) AS total_trips,
        COUNT(DISTINCT DATE(t.lpep_pickup_datetime))
            AS occurrence_days
    FROM fact_taxi_trip t
    JOIN dim_calendar c
        ON DATE(t.lpep_pickup_datetime) = c.Date
    GROUP BY
        c.DayOfWeek,
        c.DayName,
        EXTRACT(HOUR FROM t.lpep_pickup_datetime)
)

SELECT
    DayOfWeek,
    DayName,
    pickup_hour,
    total_trips,
    ROUND(
        total_trips * 1.0
        / occurrence_days,
        0
    ) AS average_trips_per_occurrence,
    ROUND(
        total_trips * 100.0
        / SUM(total_trips) OVER (),
        2
    ) AS trip_share_pct
FROM day_hour_demand
ORDER BY
    total_trips DESC;

/* ============================================================
   SECTION 10 — WEEKLY PLANNING METRICS
   ============================================================

   BUSINESS QUESTION:
   What does historical weekly green taxi demand look like,
   and how does demand change from one week to the next?

   WHY ARE WE EXECUTING THIS ANALYSIS?
   The previous sections identified when and where demand is
   concentrated. The Maven Taxi business problem also requires
   weekly planning metrics.

   CORE KPIs:
   - Total trips per week
   - Average fare per trip
   - Average distance per trip
   - Week-over-week trip-volume change (%)

   ANALYTICAL PURPOSE:
   Establish a consistent historical weekly baseline for
   operational planning and potential future forecasting.

   DATA TREATMENT:
   - Week is based on pickup date.
   - PostgreSQL weeks begin on Monday.
   - Only complete Monday-Sunday weeks are included.
   - Partial weeks at the beginning/end of the dataset are
     excluded so they do not distort week-over-week changes.
   - Average fare uses fare_amount.
   - Average distance uses trip_distance.

   IMPORTANT LIMITATIONS:
   - This is historical analysis, not a forecast.
   - Week-over-week changes do not explain their causes.
   - The dataset does not contain actual fleet availability,
     utilization, wait times, or unmet demand.
   ============================================================ */
WITH weekly_metrics AS (
    SELECT
        DATE_TRUNC(
            'week',
            t.lpep_pickup_datetime
        )::DATE AS week_start,

        COUNT(*) AS total_trips,

        COUNT(
            DISTINCT DATE(t.lpep_pickup_datetime)
        ) AS active_days,

        AVG(t.fare_amount) AS average_fare_per_trip,

        AVG(t.trip_distance) AS average_distance_per_trip

    FROM fact_taxi_trip t

    GROUP BY
        DATE_TRUNC(
            'week',
            t.lpep_pickup_datetime
        )::DATE
),

complete_weeks AS (
    SELECT
        week_start,
        total_trips,
        average_fare_per_trip,
        average_distance_per_trip
    FROM weekly_metrics
    WHERE active_days = 7
),

weekly_with_previous AS (
    SELECT
        week_start,
        total_trips,
        average_fare_per_trip,
        average_distance_per_trip,

        LAG(total_trips) OVER (
            ORDER BY week_start
        ) AS previous_week_trips

    FROM complete_weeks
)

SELECT
    week_start,
    total_trips,

    ROUND(
        average_fare_per_trip,
        2
    ) AS average_fare_per_trip,

    ROUND(
        average_distance_per_trip,
        2
    ) AS average_distance_per_trip,

    ROUND(
        (
            total_trips - previous_week_trips
        ) * 100.0
        / NULLIF(previous_week_trips, 0),
        2
    ) AS wow_trip_change_pct

FROM weekly_with_previous

ORDER BY
    week_start;

/* ============================================================
   SECTION 11 — WITHIN-BOROUGH TRIPS BY PICKUP BOROUGH
   ============================================================

   BUSINESS QUESTION:
   For each NYC borough, how many taxi trips stay within
   the same borough?

   WHY ARE WE EXECUTING THIS ANALYSIS?
   Maven's recommended analysis specifically asks:
   "For each borough, how many trips are expected to stay
   within the borough?"

   Section 7 established that 85.93% of valid five-borough
   trips are within-borough overall.

   This analysis breaks that result down by pickup borough
   to determine whether the within-borough pattern is
   consistent across the five boroughs.

   KPIs:
   - Total trips originating in each borough
   - Within-borough trips
   - Within-borough trip percentage

   DATA TREATMENT:
   - Pickup and dropoff must both belong to one of the five
     NYC boroughs.
   - EWR and Unknown are excluded.
   - Same-borough trips are classified as within-borough.
   ============================================================ */
SELECT
    pickup.Borough AS pickup_borough,

    COUNT(*) AS total_trips,

    COUNT(*) FILTER (
        WHERE pickup.Borough = dropoff.Borough
    ) AS within_borough_trips,

    ROUND(
        COUNT(*) FILTER (
            WHERE pickup.Borough = dropoff.Borough
        ) * 100.0
        / COUNT(*),
        2
    ) AS within_borough_pct

FROM fact_taxi_trip t

JOIN dim_taxi_zone pickup
    ON t.PULocationID = pickup.LocationID

JOIN dim_taxi_zone dropoff
    ON t.DOLocationID = dropoff.LocationID

WHERE pickup.Borough IN (
    'Manhattan',
    'Brooklyn',
    'Queens',
    'Bronx',
    'Staten Island'
)

AND dropoff.Borough IN (
    'Manhattan',
    'Brooklyn',
    'Queens',
    'Bronx',
    'Staten Island'
)

GROUP BY
    pickup.Borough

ORDER BY
    within_borough_pct DESC;