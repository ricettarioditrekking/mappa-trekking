import os
import glob
import json
import math
import xml.etree.ElementTree as ET
from datetime import datetime


def haversine(lat1, lon1, lat2, lon2):
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
    tree = ET.parse(file_path)
    root = tree.getroot()

    coords = []
    elevations = []
    raw_points = []
    total_dist_km = 0.0
    last_lat, last_lon = None, None

    # Estrazione punti e metadati di ogni trackpoint
    for trkpt in root.findall('.//{*}trkpt'):
        lat = float(trkpt.attrib['lat'])
        lon = float(trkpt.attrib['lon'])
        coords.append([lon, lat])

        if last_lat is not None and last_lon is not None:
            total_dist_km += haversine(last_lat, last_lon, lat, lon)
        last_lat, last_lon = lat, lon

        ele_elem = trkpt.find('{*}ele')
        ele_val = None
        if ele_elem is not None and ele_elem.text:
            try:
                ele_val = float(ele_elem.text)
            except ValueError:
                pass
        elevations.append(ele_val)

        time_elem = trkpt.find('{*}time')
        ts_val = None
        if time_elem is not None and time_elem.text:
            try:
                ts = time_elem.text.strip().replace('Z', '+00:00')
                ts_val = datetime.fromisoformat(ts)
            except ValueError:
                pass

        raw_points.append({'lat': lat, 'lon': lon, 'time': ts_val})

    km = round(total_dist_km, 1)
    dislivello_pos, dislivello_neg = calcola_dislivelli_wikiloc(elevations, window_size=9)

    # Filtraggio punti validi per calcolo tempi
    valid_time_pts = [p for p in raw_points if p['time'] is not None]

    data_trekking = "Non specificata"
    tempo_mov_str = "N/D"
    tempo_pausa_str = "N/D"

    if len(valid_time_pts) >= 2:
        start_time = valid_time_pts[0]['time']
        end_time = valid_time_pts[-1]['time']

        data_trekking = start_time.strftime("%d/%m/%Y")

        total_seconds = (end_time - start_time).total_seconds()
        total_minutes = int(total_seconds / 60)
        hours = total_minutes // 60
        minutes = total_minutes % 60
        tempo_testo = f"{hours}h {minutes:02d}m"
        durata_cat = "Mezza Giornata" if total_minutes <= 240 else "Giornata Intera"

        # Calcolo analitico Movimento vs Pausa
        mov_seconds = 0.0
        pause_seconds = 0.0

        for i in range(1, len(valid_time_pts)):
            pt1 = valid_time_pts[i - 1]
            pt2 = valid_time_pts[i]

            dt = (pt2['time'] - pt1['time']).total_seconds()
            if dt > 0:
                dist_km = haversine(pt1['lat'], pt1['lon'], pt2['lat'], pt2['lon'])
                speed_kmh = dist_km / (dt / 3600.0)

                # Soglia movimento: >= 0.8 km/h
                if speed_kmh >= 0.8:
                    mov_seconds += dt
                else:
                    pause_seconds += dt

        mov_m = int(mov_seconds // 60)
        tempo_mov_str = f"{mov_m // 60}h {mov_m % 60:02d}m"

        pau_m = int(pause_seconds // 60)
        tempo_pausa_str = f"{pau_m // 60}h {pau_m % 60:02d}m"

    else:
        est_hours = round((km / 4.0) + (dislivello_pos / 400.0), 1)
        tempo_testo = f"~{est_hours} ore"
        durata_cat = "Mezza Giornata" if est_hours <= 4.0 else "Giornata Intera"

    effort_score = round(km + 2*(dislivello_pos / 100.0), 1)

    if effort_score < 12:
        difficolta = "Facile"
    elif effort_score <= 22:
        difficolta = "Media"
    elif effort_score <= 32:
        difficolta = "Difficile"
    else:
        difficolta = "Molto Difficile"

    # Nome traccia
    name_elem = root.find('.//{*}trk/{*}name')
    if name_elem is not None and name_elem.text:
        track_name = name_elem.text.strip()
    else:
        base = os.path.basename(file_path)
        track_name = os.path.splitext(base)[0].replace('_', ' ').replace('-', ' ').title()
    
    # Estrazione della descrizione
    desc_elem = root.find('.//{*}trk/{*}desc')
    track_desc = ""
    if desc_elem is not None and desc_elem.text:
        track_desc = desc_elem.text.strip()
        
    # Link Wikiloc
    wikiloc_link = None
    link_elem = root.find('.//{*}link')
    if link_elem is not None and 'href' in link_elem.attrib:
        wikiloc_link = link_elem.attrib['href']

    # Controllo immagine associata
    base_path = os.path.splitext(file_path)[0]
    image_url = None
    for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']:
        candidate = base_path + ext
        if os.path.exists(candidate):
            image_url = candidate.replace('\\', '/')
            break

    # Riconoscimento dello STATO (fatta / non_fatta)
    normalized_path = file_path.replace('\\', '/').lower()
    if '/fatte/' in normalized_path or normalized_path.startswith('fatte/'):
        stato = "fatta"
    elif '/non_fatte/' in normalized_path or normalized_path.startswith('non_fatte/'):
        stato = "non_fatta"
    else:
        stato = "non_fatta"

    return {
        "type": "Feature",
        "properties": {
            "name": track_name,
            "descrizione": track_desc,
            "km": km,
            "dislivello": dislivello_pos,
            "dislivello_neg": dislivello_neg,
            "difficolta": difficolta,
            "sforzo": effort_score,
            "durata": durata_cat,
            "tempo_effettivo": tempo_testo,
            "tempo_movimento": tempo_mov_str,
            "tempo_pausa": tempo_pausa_str,
            "data_trekking": data_trekking,
            "stato": stato,
            "file_location": file_path.replace('\\', '/'),
            "link": wikiloc_link,
            "image_url": image_url
        },
        "geometry": {
            "type": "LineString",
            "coordinates": coords,
        },
    }


def main():
    gpx_files = glob.glob('**/*.gpx', recursive=True)
    if not gpx_files:
        print("Nessun file .gpx trovato!")
        return

    features = [processa_gpx(f) for f in gpx_files]

    with open("percorsi.geojson", "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f, ensure_ascii=False, indent=2)

    print(f"Generato percorsi.geojson per {len(features)} percorsi.")


if __name__ == "__main__":
    main()
