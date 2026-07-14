import streamlit as st
import xml.etree.ElementTree as ET
import tempfile
import os
import math
from datetime import datetime, timedelta
import requests
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

# ===== CONFIGURATION =====
DEFAULT_MAX_SPEED_KMH = 35.0
MAX_WAIT_MINUTES = 10
INTERPOLATE = True
INTERVAL_SEC = 1
USE_OSRM = True
OSRM_URL = 'http://router.project-osrm.org/route/v1/'
MAX_GAP_M = 500.0
MIN_CLUSTER_POINTS = 3

st.set_page_config(
    page_title="GPX Cleaner",
    page_icon="🧹",
    layout="wide"
)

# ===== ACTIVITY TYPE MAPPING =====
ACTIVITY_PROFILES = {
    'walking': 'foot',
    'running': 'foot',
    'hiking': 'foot',
    'cycling': 'bike',
    'mountain_biking': 'bike',
    'biking': 'bike',
    'driving': 'car',
    'car': 'car',
}

# ===== HELPER FUNCTIONS =====

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def get_activity_type_from_gpx(root, ns):
    """Extract activity type from GPX file"""
    trk = root.find('.//gpx:trk', ns)
    if trk is not None:
        type_elem = trk.find('gpx:type', ns)
        if type_elem is not None and type_elem.text:
            return type_elem.text.lower().strip()
        
        name_elem = trk.find('gpx:name', ns)
        if name_elem is not None and name_elem.text:
            name_lower = name_elem.text.lower()
            for activity in ['walk', 'run', 'hike', 'bike', 'cycle', 'drive', 'car']:
                if activity in name_lower:
                    if activity in ['drive', 'car']:
                        return 'driving'
                    return activity + 'ing'
    
    extensions = root.findall('.//gpx:extensions', ns)
    for ext in extensions:
        for child in ext:
            if 'Track' in child.tag and 'Activity' in child.tag:
                if child.text:
                    return child.text.lower()
    
    return None

def get_osrm_profile_from_activity(activity_type):
    """Map activity type to OSRM profile"""
    if activity_type is None:
        return 'bike'
    
    activity_lower = activity_type.lower()
    
    for key, profile in ACTIVITY_PROFILES.items():
        if key in activity_lower:
            return profile
    
    if 'walk' in activity_lower or 'hike' in activity_lower:
        return 'foot'
    elif 'run' in activity_lower or 'jog' in activity_lower:
        return 'foot'
    elif 'bike' in activity_lower or 'cycle' in activity_lower or 'mtb' in activity_lower:
        return 'bike'
    elif 'car' in activity_lower or 'drive' in activity_lower:
        return 'car'
    
    return 'bike'

def get_osrm_route(lat1, lon1, lat2, lon2, profile='bike'):
    url = f"{OSRM_URL}{profile}/{lon1},{lat1};{lon2},{lat2}"
    params = {'overview': 'full', 'geometries': 'geojson'}
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            return None, None
        
        data = resp.json()
        if not data.get('routes'):
            return None, None
        
        route = data['routes'][0]
        distance = route['distance']
        coords = route['geometry']['coordinates']
        points = [(lat, lon) for lon, lat in coords]
        
        return points, distance
    
    except Exception as e:
        st.warning(f"OSRM error: {e}")
        return None, None

def reverse_geocode(lat, lon):
    """Get place name from coordinates using Nominatim"""
    try:
        geolocator = Nominatim(user_agent="gpx-cleaner-app")
        location = geolocator.reverse(f"{lat}, {lon}", timeout=5)
        if location and location.address:
            address = location.raw.get('address', {})
            
            for key in ['city', 'town', 'village', 'hamlet', 'suburb', 'neighbourhood', 'state_district', 'state']:
                if key in address and address[key]:
                    return address[key]
            
            return location.address.split(',')[0]
        
        return None
    except (GeocoderTimedOut, GeocoderUnavailable, Exception):
        return None

def get_place_name(lat, lon):
    """Get place name with fallback to coordinates"""
    try:
        name = reverse_geocode(lat, lon)
        if name:
            return name
    except:
        pass
    
    return f"{lat:.4f}, {lon:.4f}"

def interpolate_points_linear(p1, p2, ns, interval_sec=1):
    lat1, lon1 = float(p1.get('lat')), float(p1.get('lon'))
    lat2, lon2 = float(p2.get('lat')), float(p2.get('lon'))
    
    t1 = p1.find('gpx:time', ns)
    t2 = p2.find('gpx:time', ns)
    
    if t1 is None or t2 is None or not t1.text or not t2.text:
        return [p2]
    
    try:
        dt1 = datetime.fromisoformat(t1.text.replace('Z', '+00:00'))
        dt2 = datetime.fromisoformat(t2.text.replace('Z', '+00:00'))
    except:
        return [p2]
    
    total_sec = (dt2 - dt1).total_seconds()
    if total_sec <= 0:
        return [p2]
    
    num_steps = max(1, int(total_sec / interval_sec))
    
    points = []
    for step in range(1, num_steps + 1):
        frac = step / num_steps
        lat = lat1 + (lat2 - lat1) * frac
        lon = lon1 + (lon2 - lon1) * frac
        
        new_pt = ET.Element('{http://www.topografix.com/GPX/1/1}trkpt')
        new_pt.set('lat', str(lat))
        new_pt.set('lon', str(lon))
        
        new_time = dt1 + timedelta(seconds=step * interval_sec)
        if new_time > dt2:
            new_time = dt2
        
        time_elem = ET.Element('{http://www.topografix.com/GPX/1/1}time')
        time_elem.text = new_time.isoformat().replace('+00:00', 'Z')
        new_pt.append(time_elem)
        
        for child in p2:
            if child.tag != '{http://www.topografix.com/GPX/1/1}time':
                new_pt.append(child)
        
        points.append(new_pt)
    
    return points

def interpolate_points_osrm(p1, p2, ns, interval_sec=1, profile='bike'):
    lat1, lon1 = float(p1.get('lat')), float(p1.get('lon'))
    lat2, lon2 = float(p2.get('lat')), float(p2.get('lon'))
    
    t1 = p1.find('gpx:time', ns)
    t2 = p2.find('gpx:time', ns)
    
    if t1 is None or t2 is None or not t1.text or not t2.text:
        return interpolate_points_linear(p1, p2, ns, interval_sec)
    
    try:
        dt1 = datetime.fromisoformat(t1.text.replace('Z', '+00:00'))
        dt2 = datetime.fromisoformat(t2.text.replace('Z', '+00:00'))
    except:
        return interpolate_points_linear(p1, p2, ns, interval_sec)
    
    total_sec = (dt2 - dt1).total_seconds()
    if total_sec <= 0:
        return interpolate_points_linear(p1, p2, ns, interval_sec)
    
    osrm_points, osrm_dist = get_osrm_route(lat1, lon1, lat2, lon2, profile)
    
    if osrm_points is None or len(osrm_points) < 2:
        return interpolate_points_linear(p1, p2, ns, interval_sec)
    
    num_steps = max(1, int(total_sec / interval_sec))
    
    points = []
    if len(osrm_points) <= 2:
        for step in range(1, num_steps + 1):
            frac = step / num_steps
            lat = osrm_points[0][0] + (osrm_points[-1][0] - osrm_points[0][0]) * frac
            lon = osrm_points[0][1] + (osrm_points[-1][1] - osrm_points[0][1]) * frac
            
            new_pt = ET.Element('{http://www.topografix.com/GPX/1/1}trkpt')
            new_pt.set('lat', str(lat))
            new_pt.set('lon', str(lon))
            
            new_time = dt1 + timedelta(seconds=step * interval_sec)
            if new_time > dt2:
                new_time = dt2
            
            time_elem = ET.Element('{http://www.topografix.com/GPX/1/1}time')
            time_elem.text = new_time.isoformat().replace('+00:00', 'Z')
            new_pt.append(time_elem)
            
            for child in p2:
                if child.tag != '{http://www.topografix.com/GPX/1/1}time':
                    new_pt.append(child)
            
            points.append(new_pt)
    else:
        total_osrm_segments = len(osrm_points) - 1
        steps_per_segment = max(1, num_steps // total_osrm_segments)
        
        for i in range(len(osrm_points) - 1):
            lat1_o, lon1_o = osrm_points[i]
            lat2_o, lon2_o = osrm_points[i + 1]
            
            for j in range(steps_per_segment):
                frac = j / steps_per_segment
                lat = lat1_o + (lat2_o - lat1_o) * frac
                lon = lon1_o + (lon2_o - lon1_o) * frac
                
                new_pt = ET.Element('{http://www.topografix.com/GPX/1/1}trkpt')
                new_pt.set('lat', str(lat))
                new_pt.set('lon', str(lon))
                
                time_pos = (i * steps_per_segment + j) / (total_osrm_segments * steps_per_segment)
                new_time = dt1 + timedelta(seconds=time_pos * total_sec)
                if new_time > dt2:
                    new_time = dt2
                
                time_elem = ET.Element('{http://www.topografix.com/GPX/1/1}time')
                time_elem.text = new_time.isoformat().replace('+00:00', 'Z')
                new_pt.append(time_elem)
                
                for child in p2:
                    if child.tag != '{http://www.topografix.com/GPX/1/1}time':
                        new_pt.append(child)
                
                points.append(new_pt)
        
        points.append(p2)
    
    return points

def interpolate_points(p1, p2, ns, interval_sec=1, profile='bike'):
    if USE_OSRM:
        return interpolate_points_osrm(p1, p2, ns, interval_sec, profile)
    else:
        return interpolate_points_linear(p1, p2, ns, interval_sec)

def get_time(point, ns):
    t = point.find('gpx:time', ns)
    if t is not None and t.text:
        try:
            return datetime.fromisoformat(t.text.replace('Z', '+00:00'))
        except:
            pass
    return None

def create_point(lat, lon, time, ns, template=None):
    """Create a new GPX point with the given coordinates and time"""
    new_pt = ET.Element('{http://www.topografix.com/GPX/1/1}trkpt')
    new_pt.set('lat', str(lat))
    new_pt.set('lon', str(lon))
    
    time_elem = ET.Element('{http://www.topografix.com/GPX/1/1}time')
    time_elem.text = time.isoformat().replace('+00:00', 'Z')
    new_pt.append(time_elem)
    
    if template is not None:
        for child in template:
            if child.tag != '{http://www.topografix.com/GPX/1/1}time':
                new_pt.append(child)
    
    return new_pt

def fix_loop_endpoints(cluster_points, first_point, last_point, ns, osrm_profile, max_speed_kmh, interval_sec=1):
    """
    Fix endpoints for a loop route.
    If one endpoint is bad and the other is good, use the good one to fix the bad one.
    """
    if len(cluster_points) < 2:
        return cluster_points, False, False
    
    has_time = get_time(first_point, ns) is not None and get_time(last_point, ns) is not None
    
    if not has_time:
        return cluster_points, False, False
    
    start_fixed = False
    end_fixed = False
    
    cluster_start = cluster_points[0]
    cluster_end = cluster_points[-1]
    
    dist_start = haversine(
        float(first_point.get('lat')), float(first_point.get('lon')),
        float(cluster_start.get('lat')), float(cluster_start.get('lon'))
    )
    
    dist_end = haversine(
        float(last_point.get('lat')), float(last_point.get('lon')),
        float(cluster_end.get('lat')), float(cluster_end.get('lon'))
    )
    
    threshold = 500.0
    
    start_is_bad = dist_start > threshold
    end_is_bad = dist_end > threshold
    
    # Case 1: Start is bad, end is good -> use end for start
    if start_is_bad and not end_is_bad:
        st.info(f"Loop: Start is bad ({dist_start:.0f}m from cluster). Using end point as reference...")
        
        t_cluster_start = get_time(cluster_start, ns)
        t_first = get_time(first_point, ns)
        t_last = get_time(last_point, ns)
        
        if t_cluster_start and t_first and t_last and t_first < t_cluster_start:
            end_lat = float(last_point.get('lat'))
            end_lon = float(last_point.get('lon'))
            
            start_fix_point = create_point(end_lat, end_lon, t_first, ns, cluster_start)
            interp = interpolate_points(start_fix_point, cluster_start, ns, interval_sec, osrm_profile)
            cluster_points = interp + cluster_points[1:]
            start_fixed = True
    
    # Case 2: End is bad, start is good -> use start for end
    elif end_is_bad and not start_is_bad:
        st.info(f"Loop: End is bad ({dist_end:.0f}m from cluster). Using start point as reference...")
        
        t_cluster_end = get_time(cluster_end, ns)
        t_last = get_time(last_point, ns)
        t_first = get_time(first_point, ns)
        
        if t_cluster_end and t_last and t_first and t_cluster_end < t_last:
            start_lat = float(first_point.get('lat'))
            start_lon = float(first_point.get('lon'))
            
            end_fix_point = create_point(start_lat, start_lon, t_last, ns, cluster_end)
            interp = interpolate_points(cluster_end, end_fix_point, ns, interval_sec, osrm_profile)
            cluster_points = cluster_points[:-1] + interp
            end_fixed = True
    
    # Case 3: Both are bad
    elif start_is_bad and end_is_bad:
        st.warning("Both start and end points are bad. Cannot fix loop without at least one good endpoint.")
    
    return cluster_points, start_fixed, end_fixed

def calculate_cluster_stats(cluster, ns):
    if len(cluster) < 2:
        return {'distance': 0, 'time': 0, 'speed': 0, 'points': len(cluster)}
    
    has_time = get_time(cluster[0], ns) is not None
    
    distance = sum(haversine(
        float(cluster[i].get('lat')), float(cluster[i].get('lon')),
        float(cluster[i+1].get('lat')), float(cluster[i+1].get('lon'))
    ) for i in range(len(cluster)-1))
    
    time_seconds = 0
    if has_time:
        t1 = get_time(cluster[0], ns)
        t2 = get_time(cluster[-1], ns)
        if t1 and t2:
            time_seconds = (t2 - t1).total_seconds()
    
    speed = 0
    if time_seconds > 0:
        speed = (distance / time_seconds) * 3.6
    
    avg_lat = sum(float(p.get('lat')) for p in cluster) / len(cluster)
    avg_lon = sum(float(p.get('lon')) for p in cluster) / len(cluster)
    
    return {
        'distance': distance,
        'time': time_seconds,
        'speed': speed,
        'points': len(cluster),
        'avg_lat': avg_lat,
        'avg_lon': avg_lon
    }

def cluster_points(points, ns, max_speed_kmh):
    if len(points) == 0:
        return []
    
    clusters = []
    cluster_last_time = []
    cluster_active = []
    
    first_cluster = [points[0]]
    clusters.append(first_cluster)
    cluster_last_time.append(get_time(points[0], ns))
    cluster_active.append(True)
    
    has_time = get_time(points[0], ns) is not None
    
    for i in range(1, len(points)):
        current = points[i]
        current_time = get_time(current, ns) if has_time else None
        
        best_cluster_idx = -1
        best_distance = float('inf')
        
        for idx, cluster in enumerate(clusters):
            if not cluster_active[idx]:
                continue
            
            last_point = cluster[-1]
            last_time = cluster_last_time[idx]
            
            dist = haversine(
                float(last_point.get('lat')), float(last_point.get('lon')),
                float(current.get('lat')), float(current.get('lon'))
            )
            
            max_dist = MAX_GAP_M
            if has_time and current_time and last_time:
                dt = (current_time - last_time).total_seconds()
                if dt > 0:
                    max_dist = (max_speed_kmh / 3.6) * dt * 1.5
            
            if dist <= max_dist:
                if dist < best_distance:
                    best_distance = dist
                    best_cluster_idx = idx
        
        if best_cluster_idx >= 0:
            clusters[best_cluster_idx].append(current)
            cluster_last_time[best_cluster_idx] = current_time
            
            for idx in range(len(clusters)):
                if not cluster_active[idx] and idx != best_cluster_idx:
                    last_point = clusters[idx][-1]
                    dist = haversine(
                        float(last_point.get('lat')), float(last_point.get('lon')),
                        float(current.get('lat')), float(current.get('lon'))
                    )
                    if has_time and current_time and cluster_last_time[idx]:
                        dt = (current_time - cluster_last_time[idx]).total_seconds()
                        max_dist = (max_speed_kmh / 3.6) * dt * 1.5
                        if dist <= max_dist:
                            cluster_active[idx] = True
        else:
            new_cluster = [current]
            clusters.append(new_cluster)
            cluster_last_time.append(current_time)
            cluster_active.append(True)
            
            for idx in range(len(clusters) - 1):
                if cluster_active[idx] and cluster_last_time[idx]:
                    if has_time and current_time:
                        dt = (current_time - cluster_last_time[idx]).total_seconds()
                        if dt > MAX_WAIT_MINUTES * 60:
                            cluster_active[idx] = False
    
    return clusters

def build_gpx(points, output_path):
    ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}
    ET.register_namespace('', ns['gpx'])
    
    root = ET.Element('{http://www.topografix.com/GPX/1/1}gpx')
    root.set('version', '1.1')
    root.set('creator', 'GPX Cleaner')
    
    trk = ET.SubElement(root, '{http://www.topografix.com/GPX/1/1}trk')
    trkseg = ET.SubElement(trk, '{http://www.topografix.com/GPX/1/1}trkseg')
    
    for p in points:
        trkseg.append(p)
    
    tree = ET.ElementTree(root)
    tree.write(output_path, encoding='utf-8', xml_declaration=True)

# ===== STREAMLIT UI =====

st.title("GPX Cleaner")
st.markdown("Remove GPS spoofing and jamming artifacts from your GPX tracks")

with st.expander("How it works"):
    st.markdown("""
    1. **Upload** your GPX file
    2. **Detect** parallel trajectories (clusters)
    3. **Select** the correct one
    4. **Download** the cleaned GPX
    
    This tool automatically finds multiple routes in your GPX file caused by GPS spoofing or jamming,
    shows you statistics for each, and lets you choose the real one.
    """)

uploaded_file = st.file_uploader("Choose a GPX file", type=['gpx'])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix='.gpx') as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name
    
    ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}
    
    try:
        tree = ET.parse(tmp_path)
        root = tree.getroot()
        
        trk = root.find('.//gpx:trk', ns)
        if trk is None:
            st.error("No track found in GPX file")
            os.unlink(tmp_path)
            st.stop()
        
        trkseg = trk.find('.//gpx:trkseg', ns)
        if trkseg is None:
            st.error("No track segment found in GPX file")
            os.unlink(tmp_path)
            st.stop()
        
        points = trkseg.findall('gpx:trkpt', ns)
        if len(points) < 3:
            st.error("Too few points in GPX file")
            os.unlink(tmp_path)
            st.stop()
        
        first_point = points[0]
        last_point = points[-1]
        
        # Try to detect activity type from GPX
        activity_type = get_activity_type_from_gpx(root, ns)
        
        if activity_type is None:
            st.info("Activity type not found in GPX file. Please select your activity:")
            activity_type = st.selectbox(
                "Select activity type:",
                options=['Walking', 'Running', 'Hiking', 'Cycling', 'Mountain Biking', 'Driving', 'Other'],
                index=3
            ).lower()
            
            if activity_type == 'other':
                activity_type = st.text_input("Enter activity type:").lower()
                if not activity_type:
                    activity_type = 'cycling'
        
        osrm_profile = get_osrm_profile_from_activity(activity_type)
        
        st.success(f"Activity: **{activity_type.capitalize()}** → OSRM: **{osrm_profile}**")
        
        # ===== ADVANCED SETTINGS (collapsed by default) =====
        with st.expander("Advanced settings"):
            st.markdown("Adjust these and click **Re-analyze** to update clusters.")
            
            is_loop = st.checkbox(
                "This is a loop route (start and end should be at the same location)",
                value=False,
                key="is_loop_checkbox",
                help="If the route is a loop and one endpoint is bad, the app will use the good endpoint to fix the bad one."
            )
            
            max_speed_kmh = st.slider(
                "Max speed (km/h)",
                min_value=10.0,
                max_value=300.0,
                value=DEFAULT_MAX_SPEED_KMH,
                step=0.1,
                format="%.1f",
                key="max_speed_slider",
                help="Maximum speed used for clustering. Higher values = more points merged into one cluster."
            )
            
            # Re-analyze button
            reanalyze = st.button("🔄 Re-analyze", use_container_width=True, key="reanalyze_button")
        
        # Check if we need to re-analyze
        if reanalyze or 'cluster_data' not in st.session_state:
            with st.spinner("Analyzing track..."):
                clusters = cluster_points(points, ns, max_speed_kmh)
                filtered_clusters = [c for c in clusters if len(c) >= MIN_CLUSTER_POINTS]
                
                if len(filtered_clusters) == 0:
                    st.error("No valid clusters found")
                    os.unlink(tmp_path)
                    st.stop()
                
                # Sort clusters by points count (descending)
                filtered_clusters.sort(key=len, reverse=True)
                
                cluster_data = []
                for i, cluster in enumerate(filtered_clusters):
                    stats = calculate_cluster_stats(cluster, ns)
                    place = get_place_name(stats['avg_lat'], stats['avg_lon'])
                    is_largest = (i == 0)
                    cluster_data.append({
                        'index': i,
                        'cluster': cluster,
                        'stats': stats,
                        'place': place,
                        'is_largest': is_largest
                    })
                
                st.session_state['cluster_data'] = cluster_data
                st.session_state['max_speed_kmh'] = max_speed_kmh
        
        # Display clusters from session state
        if 'cluster_data' in st.session_state:
            cluster_data = st.session_state['cluster_data']
            
            st.subheader(f"Found {len(cluster_data)} clusters (sorted by points)")
            
            for data in cluster_data:
                stats = data['stats']
                place = data['place']
                is_largest = data['is_largest']
                
                if is_largest:
                    with st.container():
                        st.markdown("---")
                        st.markdown("**⭐ RECOMMENDED (most points)**")
                        st.markdown(f"**Cluster {data['index']+1}: {place}** ({stats['points']} points)")
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("Points", stats['points'])
                        col2.metric("Distance", f"{stats['distance']/1000:.2f} km")
                        col3.metric("Duration", f"{stats['time']/60:.1f} min")
                        col4.metric("Avg Speed", f"{stats['speed']:.1f} km/h")
                        st.markdown("---")
                else:
                    with st.expander(f"Cluster {data['index']+1}: {place} ({stats['points']} points)"):
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("Points", stats['points'])
                        col2.metric("Distance", f"{stats['distance']/1000:.2f} km")
                        col3.metric("Duration", f"{stats['time']/60:.1f} min")
                        col4.metric("Avg Speed", f"{stats['speed']:.1f} km/h")
            
            selected_index = st.radio(
                "Select the cluster to save:",
                options=range(len(cluster_data)),
                format_func=lambda i: f"Cluster {i+1}: {cluster_data[i]['place']} ({cluster_data[i]['stats']['points']} points, {cluster_data[i]['stats']['distance']/1000:.2f} km)"
            )
            
            # === PROCESS BUTTON ===
            if st.button("Process", type="primary", use_container_width=True, key="process_button"):
                with st.spinner("Processing track..."):
                    clean_points = cluster_data[selected_index]['cluster']
                    
                    start_fixed = False
                    end_fixed = False
                    
                    # Use current is_loop from the checkbox
                    if is_loop:
                        clean_points, start_fixed, end_fixed = fix_loop_endpoints(
                            clean_points, first_point, last_point, ns, osrm_profile, max_speed_kmh, INTERVAL_SEC
                        )
                    
                    # Interpolate gaps
                    if INTERPOLATE:
                        has_time = get_time(clean_points[0], ns) is not None
                        if has_time and len(clean_points) > 1:
                            interpolated = [clean_points[0]]
                            
                            for i in range(1, len(clean_points)):
                                p1 = clean_points[i-1]
                                p2 = clean_points[i]
                                
                                t1 = get_time(p1, ns)
                                t2 = get_time(p2, ns)
                                
                                if t1 is None or t2 is None:
                                    interpolated.append(p2)
                                    continue
                                
                                dt = (t2 - t1).total_seconds()
                                if dt <= 0:
                                    interpolated.append(p2)
                                    continue
                                
                                dist = haversine(
                                    float(p1.get('lat')), float(p1.get('lon')),
                                    float(p2.get('lat')), float(p2.get('lon'))
                                )
                                
                                max_dist = (max_speed_kmh / 3.6) * dt
                                
                                if dist > max_dist * 1.5:
                                    interp = interpolate_points(p1, p2, ns, INTERVAL_SEC, osrm_profile)
                                    interpolated.extend(interp)
                                else:
                                    interpolated.append(p2)
                            
                            clean_points = interpolated
                    
                    st.session_state['processed_points'] = clean_points
                    st.session_state['start_fixed'] = start_fixed
                    st.session_state['end_fixed'] = end_fixed
                    st.session_state['processed'] = True
                    
                    if start_fixed:
                        st.success("Start point fixed using end point as reference")
                    if end_fixed:
                        st.success("End point fixed using start point as reference")
                    
                    st.success("Track processed successfully! Use the download button below.")
            
            # === DOWNLOAD BUTTON (appears only after processing) ===
            if st.session_state.get('processed', False):
                clean_points = st.session_state['processed_points']
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.gpx') as out:
                    build_gpx(clean_points, out.name)
                    
                    with open(out.name, 'rb') as f:
                        st.download_button(
                            label="Download GPX File",
                            data=f,
                            file_name="cleaned_track.gpx",
                            mime="application/gpx+xml",
                            use_container_width=True,
                            key="download_button"
                        )
    
    except Exception as e:
        st.error(f"Error processing file: {e}")
    
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)