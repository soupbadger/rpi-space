# iss_tracker.py

import pygame
import requests
import json
import time
import os

# --- Pygame Setup ---
pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
SCREEN_WIDTH, SCREEN_HEIGHT = screen.get_size()
pygame.display.set_caption("Real-Time ISS Tracker")
pygame.mouse.set_visible(False)

# Get script directory
script_dir = os.path.dirname(__file__)

# --- Load Images ---
try:
    world_map = pygame.image.load(os.path.join(script_dir, 'world_map.png'))
    world_map = pygame.transform.scale(world_map, (SCREEN_WIDTH, SCREEN_HEIGHT))
except pygame.error:
    print("Error: Could not load world_map.png")
    pygame.quit()
    exit()

try:
    iss_icon = pygame.image.load(os.path.join(script_dir, 'iss_icon.png')).convert_alpha()
    iss_icon = pygame.transform.scale(iss_icon, (40, 40))
except pygame.error:
    print("Warning: Could not load iss_icon.png, using red circle instead.")
    iss_icon = None

# --- Colors & Fonts ---
shape_color = (255, 0, 0)
coord_color = (0, 0, 0)
city_color = (0, 0, 0)
text_box_bg_color = (255, 255, 255, 128)
text_box_border_color = (0, 0, 0)
font = pygame.font.Font(None, 30)

# --- API Configuration ---
ISS_API_URL = "http://api.open-notify.org/iss-now.json"
GEOCODING_API_URL = "https://geocode.maps.co/reverse"
# --- API TOKEN HERE ---
GEOCODING_API_KEY = "YOUR_API_KEY"

# --- Variables ---
latitude, longitude = None, None
iss_x, iss_y = None, None
closest_city = "..."
notification_message = None
notification_timer = 0
NOTIFICATION_DURATION = 5  # seconds

last_update_time = 0
update_interval = 2
last_city_update_time = 0
city_update_interval = 10

# Track if we've ever successfully gotten ISS data
has_initial_data = False

# --- Functions ---
def get_iss_location():
    try:
        response = requests.get(ISS_API_URL, timeout=5)
        data = response.json()
        if data.get('message') == 'success':
            return float(data['iss_position']['latitude']), float(data['iss_position']['longitude'])
        else:
            return None, None
    except requests.RequestException:
        return None, None
    except (KeyError, json.JSONDecodeError):
        return None, None

def get_closest_city(lat, lon):
    try:
        params = {"lat": lat, "lon": lon, "api_key": GEOCODING_API_KEY}
        response = requests.get(GEOCODING_API_URL, params=params, timeout=10)
        data = response.json()
        if "address" in data and "city" in data["address"]:
            return data["address"]["city"]
        elif "display_name" in data:
            return data["display_name"].split(',')[0]
        else:
            return "Over Ocean or Unnamed Area"
    except requests.RequestException:
        return "API Error"
    except (KeyError, json.JSONDecodeError):
        return "Parsing Error"

def lat_lon_to_pixels(lat, lon):
    x = (lon + 180) * (SCREEN_WIDTH / 360)
    y = (90 - lat) * (SCREEN_HEIGHT / 180)
    return x, y

def render_notification(screen, message, font, color):
    """Draws a small top-right semi-transparent notification."""
    if not message:
        return
    lines = [message[i:i+40] for i in range(0, len(message), 40)]
    text_surfaces = [font.render(line, True, color) for line in lines]

    padding = 10
    total_height = sum(s.get_height() for s in text_surfaces) + padding * (len(text_surfaces) + 1)
    max_width = max(s.get_width() for s in text_surfaces)

    box_surface = pygame.Surface((max_width + 2 * padding, total_height), pygame.SRCALPHA)
    box_surface.fill((255, 255, 255, 180))  # Semi-transparent white
    pygame.draw.rect(box_surface, (0, 0, 0), box_surface.get_rect(), 2, 5)

    y_offset = padding
    for s in text_surfaces:
        box_surface.blit(s, (padding, y_offset))
        y_offset += s.get_height() + padding

    screen.blit(box_surface, (SCREEN_WIDTH - box_surface.get_width() - padding, padding))

# --- Main Loop ---
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False

    current_time = time.time()

    # --- Update ISS location ---
    if current_time - last_update_time > update_interval:
        new_lat, new_lon = get_iss_location()
        last_update_time = current_time
        
        if new_lat is None or new_lon is None:
            if notification_message is None:  # Only set once per error
                notification_message = "Network/API Error: Unable to fetch ISS location"
                notification_timer = current_time
            # Keep the last known coordinates if we had them
            # Don't set latitude/longitude to None if we already have data
        else:
            # Clear any error notification when we get successful data
            if notification_message and "Network/API Error" in notification_message:
                notification_message = None
            
            latitude, longitude = new_lat, new_lon
            iss_x, iss_y = lat_lon_to_pixels(latitude, longitude)
            has_initial_data = True

    # --- Update city info ---
    if latitude is not None and longitude is not None and current_time - last_city_update_time > city_update_interval:
        closest_city = get_closest_city(latitude, longitude)
        last_city_update_time = current_time

    # --- Clear notification after duration ---
    if notification_message and (current_time - notification_timer > NOTIFICATION_DURATION):
        notification_message = None

    # --- Drawing ---
    screen.blit(world_map, (0, 0))

    # Only show loading message if we've never gotten initial data
    if latitude is not None and longitude is not None:
        if iss_icon:
            icon_rect = iss_icon.get_rect(center=(int(iss_x), int(iss_y)))
            screen.blit(iss_icon, icon_rect)
        else:
            pygame.draw.circle(screen, shape_color, (int(iss_x), int(iss_y)), 15)

        coords_text = font.render(f"Lat: {latitude:.2f}, Lon: {longitude:.2f}", True, coord_color)
        city_text = font.render(f"Closest City: {closest_city}", True, city_color)
        time_text = font.render(f"Time: {time.strftime('%H:%M:%S')}", True, city_color)

        padding = 10
        box_width = max(coords_text.get_width(), city_text.get_width(), time_text.get_width()) + 2 * padding
        box_height = coords_text.get_height() + city_text.get_height() + time_text.get_height() + 3 * padding
        text_box_surface = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
        text_box_surface.fill(text_box_bg_color)
        pygame.draw.rect(text_box_surface, text_box_border_color, text_box_surface.get_rect(), 2, 5)
        text_box_surface.blit(coords_text, (padding, padding))
        text_box_surface.blit(city_text, (padding, padding + coords_text.get_height() + padding // 2))
        text_box_surface.blit(time_text, (padding, padding + coords_text.get_height() + city_text.get_height() + padding))
        screen.blit(text_box_surface, (SCREEN_WIDTH - box_width - padding, SCREEN_HEIGHT - box_height - padding))
    elif not has_initial_data:
        # Only show loading text if we haven't gotten any data yet (initial startup)
        loading_text = font.render("Fetching ISS location...", True, coord_color)
        screen.blit(loading_text, loading_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))

    # --- Render top-right notification ---
    render_notification(screen, notification_message, font, (255, 0, 0))

    pygame.display.flip()
    time.sleep(0.1)

pygame.quit()