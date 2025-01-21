import csv


def dms_to_decimal(dms_string):
    dms = dms_string.strip().split(",")
    degrees = float(dms[0])
    minutes = float(dms[1])
    seconds = float(dms[2])
    decimal = degrees + (minutes / 60) + (seconds / 3600)
    return decimal


def convert_lat_lon(lat_dms, lon_dms):
    lat_direction, lat_values = lat_dms.split(" ", 1)
    lon_direction, lon_values = lon_dms.split(" ", 1)

    lat_decimal = dms_to_decimal(lat_values.strip("()"))
    lon_decimal = dms_to_decimal(lon_values.strip("()"))

    if lat_direction == "S":
        lat_decimal = -lat_decimal
    if lon_direction == "W":
        lon_decimal = -lon_decimal

    return lat_decimal, lon_decimal


input_file = "latlong_exif_image_metadata.csv"
output_file = "latlong_exif_image_metadata_wdd.csv"


def run():
    with open(input_file, mode="r") as infile, open(output_file, mode="w", newline="") as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)

        header = next(reader)
        writer.writerow(header + ["Latitude (decimal)", "Longitude (decimal)"])

        for row in reader:
            lat_dms = row[2]  # Assuming column 3 is latitude DMS
            lon_dms = row[3]  # Assuming column 4 is longitude DMS
            latitude, longitude = convert_lat_lon(lat_dms, lon_dms)
            writer.writerow(row + [latitude, longitude])

    print(f"Conversion complete. Decimal degree columns added to {output_file}")
