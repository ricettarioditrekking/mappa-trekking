import os  # File system utilities to scan directory contents[cite: 1]
import json  # Library to generate and export the output GeoJSON file[cite: 1]
import xml.etree.ElementTree as ET  # Library to parse XML tags inside raw GPX files[cite: 1]

def calcola_distanza_e_semplifica(points, tolleranza=0.0001):
    """
    Simplifies an array of coordinate points [lon, lat] using the Ramer-Douglas-Peucker algorithm[cite: 1].
    Trims redundant track points to lighten the final payload without losing trail geometry[cite: 1].
    """
    if len(points) < 3:
        return points

    def dSq(p1, p2):
        # Calculate squared Euclidean distance between two points[cite: 1]
        return (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2

    def ramerDouglasPeucker(pts, epsilon):
        # Finds the point with the maximum perpendicular distance from the line segment[cite: 1]
        dmax = 0
        index = 0
        end = len(pts) - 1
        
        for i in range(1, end):
            x, y = pts[i]
            x1, y1 = pts[0]
            x2, y2 = pts[end]
            
            # Perpendicular distance formula[cite: 1]
            if x1 == x2 and y1 == y2:
                d = (x-x1)**2 + (y-y1)**2
            else:
                num = abs((x2-x1)*(y1-y) - (x1-x)*(y2-y1))
                den = ((x2-x1)**2 + (y2-y1)**2)**0.5
                d = num/den if den != 0 else 0
                
            if d > dmax:
                index = i
                dmax = d
                
        # Recursively split and simplify if max distance exceeds tolerance threshold[cite: 1]
        if dmax > epsilon:
            recResults1 = ramerDouglasPeucker(pts[:index+1], epsilon)
            recResults2 = ramerDouglasPeucker(pts[index:], epsilon)
            return recResults1[:-1] + recResults2
        else:
            return [pts[0], pts[end]]

    return ramerDouglasPeucker(points, tolleranza)

def elabora():
    """
    Main processing loop: reads raw GPX files from /tracce, extracts metrics,
    simplifies coordinates, and writes everything to percorsi.geojson[cite: 1].
    """
    features = []
    folder = "tracce"
    
    # Exit if the input tracks folder does not exist[cite: 1]
    if not os.path.exists(folder):
        return

    # Loop through every file inside the /tracce folder[cite: 1]
    for file in os.listdir(folder):
        if file.endswith(".gpx"):
            path = os.path.join(folder, file)
            try:
                # Parse XML tree from GPX file[cite: 1]
                tree = ET.parse(path)
                root = tree.getroot()
                points = []
                elevations = []

                # Extract longitude, latitude, and elevation from XML track points[cite: 1]
                for trkpt in root.findall('.//{*}trkpt'):
                    lon = float(trkpt.attrib['lon'])
                    lat = float(trkpt.attrib['lat'])
                    points.append([lon, lat])
                    
                    ele = trkpt.find('{*}ele')
                    if ele is not None:
                        elevations.append(float(ele.text))

                # Skip empty GPX files[cite: 1]
                if not points:
                    continue

                # Run Ramer-Douglas-Peucker simplification on track coordinates[cite: 1]
                points_semplificati = calcola_distanza_e_semplifica(points)

                # Calculate cumulative positive elevation gain (ascent)[cite: 1]
                salita = 0
                for i in range(1, len(elevations)):
                    diff = elevations[i] - elevations[i-1]
                    if diff > 0:
                        salita += diff

                # Approximate total track distance in kilometers[cite: 1]
                distanza_km = 0
                for i in range(1, len(points)):
                    distanza_km += ((points[i][0]-points[i-1][0])**2 + (points[i][1]-points[i-1][1])**2)**0.5 * 111

                distanza_km = round(distanza_km, 1)
                dislivello = round(salita)

                # Assign difficulty categories based on total elevation gain[cite: 1]
                difficolta = "Facile"
                if 400 < dislivello <= 800:
                    difficolta = "Media"
                elif dislivello > 800:
                    difficolta = "Difficile"

                # Assign duration tags based on overall distance[cite: 1]
                durata = "Mezza Giornata" if distanza_km <= 10 else "Giornata Intera"
                
                # Convert filename into a clean, capitalized track title[cite: 1]
                titolo = file.replace(".gpx", "").replace("_", " ").replace("-", " ").title()

                # Build GeoJSON feature payload[cite: 1]
                feature = {
                    "type": "Feature",
                    "properties": {
                        "name": titolo,
                        "km": max(0.5, distanza_km),
                        "dislivello": dislivello,
                        "difficolta": difficolta,
                        "durata": durata
                    },
                    "geometry": {
                        "type": "LineString",
                        "coordinates": points_semplificati
                    }
                }
                features.append(feature)
            except Exception as e:
                print(f"Errore nel file {file}: {e}")

    # Combine features into a FeatureCollection and save to percorsi.geojson[cite: 1]
    geojson = {"type": "FeatureCollection", "features": features}
    with open("percorsi.geojson", "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False)

if __name__ == "__main__":
    elabora()
