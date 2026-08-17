import os
import glob
import json
import math
import xml.etree.ElementTree as ET


def haversine(lat1, lon1, lat2, lon2):
    """Calculates horizontal distance between two coordinates in kilometers."""
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def calcola_dislivello_wikiloc(elevations, window_size=9):
    """
    Smooths raw GPX elevation data with a moving average filter
    to remove GPS vertical noise, matching Wikiloc's display total.
    """
    clean_ele = [float(e) for e in elevations if e is not None]
    if len(clean_ele) < window_size:
        return 0

    smoothed_ele = []
    half_window = window_size // 2
    n = len(clean_ele)

    # 1. Apply moving average filter
    for i in range(n):
        start = max(0, i - half_window)
        end = min(n, i + half_window + 1)
        smoothed_ele.append(sum(clean_ele[start:end]) / (end - start))

    # 2. Accumulate positive elevation gains
    dislivello = 0.0
    for i in range(1, len(smoothed_ele)):
        diff = smoothed_ele[i] - smoothed_ele[i - 1]
        if diff > 0:
            dislivello += diff

    return int(round(dislivello))


def processa_gpx(file_path):
    """Parses a single GPX file and returns a GeoJSON Feature."""
    tree = ET.parse(file_path)
    root = tree.getroot()

    coords = []  # GeoJSON format: [longitude, latitude]
    elevations = []
    total_dist_km = 0.0

    last_lat, last_lon = None, None

    # Parse all track points safely, ignoring waypoints
    for trkpt in root.findall('.//{*}trkpt'):
        lat = float(trkpt.attrib['lat'])
        lon = float(trkpt.attrib['lon'])

        coords.append([lon, lat])

        # Distance calculation
        if last_lat is not None and last_lon is not None:
            total_dist_km += haversine(last_lat, last_lon, lat, lon)
        last_lat, last_lon = lat, lon

        # Elevation extraction
        ele_elem = trkpt.find('{*}ele')
        if ele_elem is not None and ele_elem.text:
            try:
                elevations.append(float(ele_elem.text))
            except ValueError:
                pass

    km = round(total_dist_km, 1)
    dislivello = calcola_dislivello_wikiloc(elevations, window_size=9)

    # Assign difficulty category
    if dislivello < 400:
        difficolta = "Facile"
    elif dislivello <= 800:
        difficolta = "Media"
    else:
        difficolta = "Difficile"

    # Assign duration category
    durata = "Mezza Giornata" if km <= 10 else "Giornata Intera"

    # Extract trail name from GPX metadata or fallback to file name
    name_elem = root.find('.//{*}trk/{*}name')
    if name_elem is not None and name_elem.text:
        track_name = name_elem.text.strip()
    else:
        base = os.path.basename(file_path)
        track_name = os.path.splitext(base)[0].replace('_', ' ').replace('-', ' ').title()

    return {
        "type": "Feature",
        "properties": {
            "name": track_name,
            "km": km,
            "dislivello": dislivello,
            "difficolta": difficolta,
            "durata": durata,
        },
        "geometry": {
            "type": "LineString",
            "coordinates": coords,
        },
    }


def main():
    # Find all GPX files recursively in the repository
    gpx_files = glob.glob('**/*.gpx', recursive=True)

    if not gpx_files:
        print("No .gpx files found in repository!")
        return

    features = []
    for filepath in gpx_files:
        try:
            feature = processa_gpx(filepath)
            features.append(feature)
            print(f"Processed: {filepath} -> {feature['properties']['name']} ({feature['properties']['dislivello']}m gain)")
        except Exception as e:
            print(f"Error processing {filepath}: {e}")

    geojson_data = {
        "type": "FeatureCollection",
        "features": features,
    }

    output_filename = "percorsi.geojson"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(geojson_data, f, ensure_ascii=False, indent=2)

    print(f"Successfully generated {output_filename} with {len(features)} tracks.")


if __name__ == "__main__":
    main()
