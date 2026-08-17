import os
import glob
import json
import math
import xml.etree.ElementTree as ET
from datetime import datetime


def haversine(lat1, lon1, lat2, lon2):
    """Calculates horizontal distance between two coordinates in kilometers."""
    R = 6371.0
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


def calcola_dislivelli_wikiloc(elevations, window_size=9):
    """Smooths raw GPX elevation data and returns positive gain and negative loss."""
    clean_ele = [float(e) for e in elevations if e is not None]
    if len(clean_ele) < window_size:
        return 0, 0

    smoothed_ele = []
    half_window = window_size // 2
    n = len(clean_ele)

    for i in range(n):
        start = max(0, i - half_window)
        end = min(n, i + half_window + 1)
        smoothed_ele.append(sum(clean_ele[start:end]) / (end - start))

    gain, loss = 0.0, 0.0
    for i in range(1, len(smoothed_ele)):
        diff = smoothed_ele[i] - smoothed_ele[i - 1]
        if diff > 0:
            gain += diff
        elif diff < 0:
            loss += abs(diff)

    return int(round(gain)), int(round(loss))


def processa_gpx(file_path):
    """Parses GPX, calculates stats rounded to 1 decimal place, and builds GeoJSON Feature."""
    tree = ET.parse(file_path)
    root = tree.getroot()

    coords = []
    elevations = []
    timestamps = []
    total_dist_km = 0.0
    last_lat, last_lon = None, None

    for trkpt in root.findall('.//{*}trkpt'):
        lat = float(trkpt.attrib['lat'])
        lon = float(trkpt.attrib['lon'])
        coords.append([lon, lat])

        if last_lat is not None and last_lon is not None:
            total_dist_km += haversine(last_lat, last_lon, lat, lon)
        last_lat, last_lon = lat, lon

        ele_elem = trkpt.find('{*}ele')
        if ele_elem is not None and ele_elem.text:
            try:
                elevations.append(float(ele_elem.text))
            except ValueError:
                pass

        time_elem = trkpt.find('{*}time')
        if time_elem is not None and time_elem.text:
            try:
                ts = time_elem.text.strip().replace('Z', '+00:00')
                timestamps.append(datetime.fromisoformat(ts))
            except ValueError:
                pass

    # Limit distance to 1 figure after the dot
    km = round(total_dist_km, 1)
    dislivello_pos, dislivello_neg = calcola_dislivelli_wikiloc(elevations, window_size=9)

    # Recorded time or fallback estimation
    if len(timestamps) >= 2:
        elapsed = timestamps[-1] - timestamps[0]
        total_minutes = int(elapsed.total_seconds() / 60)
        hours = total_minutes // 60
        minutes = total_minutes % 60
        tempo_testo = f"{hours}h {minutes:02d}m"
        durata_cat = "Mezza Giornata" if total_minutes <= 240 else "Giornata Intera"
    else:
        est_hours = round((km / 4.0) + (dislivello_pos / 400.0), 1)
        tempo_testo = f"~{est_hours} ore"
        durata_cat = "Mezza Giornata" if est_hours <= 4.0 else "Giornata Intera"

    # CAI Effort Index limited to 1 figure after the dot
    effort_score = round(km + (dislivello_pos / 100.0), 1)

    if effort_score < 12:
        difficolta = "Facile"
    elif effort_score <= 22:
        difficolta = "Media"
    elif effort_score <= 32:
        difficolta = "Difficile"
    else:
        difficolta = "Molto Difficile"

    # Track name
    name_elem = root.find('.//{*}trk/{*}name')
    if name_elem is not None and name_elem.text:
        track_name = name_elem.text.strip()
    else:
        base = os.path.basename(file_path)
        track_name = os.path.splitext(base)[0].replace('_', ' ').replace('-', ' ').title()

    # Wikiloc link
    wikiloc_link = None
    link_elem = root.find('.//{*}link')
    if link_elem is not None and 'href' in link_elem.attrib:
        wikiloc_link = link_elem.attrib['href']

    return {
        "type": "Feature",
        "properties": {
            "name": track_name,
            "km": km,
            "dislivello": dislivello_pos,
            "dislivello_neg": dislivello_neg,
            "difficolta": difficolta,
            "sforzo": effort_score,
            "durata": durata_cat,
            "tempo_effettivo": tempo_testo,
            "link": wikiloc_link
        },
        "geometry": {
            "type": "LineString",
            "coordinates": coords,
        },
    }


def main():
    gpx_files = glob.glob('**/*.gpx', recursive=True)
    if not gpx_files:
        print("No .gpx files found!")
        return

    features = [processa_gpx(f) for f in gpx_files]
    
    with open("percorsi.geojson", "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f, ensure_ascii=False, indent=2)

    print(f"Generated percorsi.geojson for {len(features)} tracks.")


if __name__ == "__main__":
    main()
