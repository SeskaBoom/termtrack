import curses
from datetime import datetime, timedelta
from math import acos, atan2, cos, degrees, radians, sin

import ephem

from .satellite import earth_radius_at_latitude
from .utils.curses import closest_color
from .utils.text import format_seconds


class InfoPanel(list):
    pass


def draw_info(stdscr, satellite):
    height, width = stdscr.getmaxyx()
    width -= 1
    text_basic = InfoPanel()
    text_basic.append(satellite.name)
    text_basic.append("---")
    text_basic.append("Latitude:")
    text_basic.append("  {:.6f}°".format(satellite.latitude))
    text_basic.append("")
    text_basic.append("Longitude:")
    text_basic.append("  {:.6f}°".format(satellite.longitude))
    text_basic.append("")
    text_basic.append("Altitude:")
    text_basic.append("  {:,.2f}km".format(satellite.altitude / 1000))
    text_basic.append("")
    text_basic.append("Velocity:")
    text_basic.append("  {:,.2f}m/s".format(satellite.velocity))
    text_basic.append("")
    text_basic.append("Orbital period:")
    text_basic.append("  " + format_seconds(satellite.orbital_period.total_seconds()))
    text_basic.top = True
    text_basic.left = True

    text_apsides = InfoPanel()
    text_apsides.append("Apogee altitude:")
    text_apsides.append("  {:,.2f}km".format(satellite.apoapsis_altitude / 1000))
    text_apsides.append("")
    text_apsides.append("Perigee altitude:")
    text_apsides.append("  {:,.2f}km".format(satellite.periapsis_altitude / 1000))
    text_apsides.append("")
    text_apsides.append("Time to perigee:")
    text_apsides.append("  " + format_seconds(satellite.time_to_periapsis.total_seconds()))
    text_apsides.append("")
    text_apsides.append("Time since perigee:")
    text_apsides.append("  " + format_seconds(satellite.time_since_periapsis.total_seconds()))
    text_apsides.append("")
    text_apsides.append("Time to apogee:")
    text_apsides.append("  " + format_seconds(satellite.time_to_apoapsis.total_seconds()))
    text_apsides.append("")
    text_apsides.append("Time since apogee:")
    text_apsides.append("  " + format_seconds(satellite.time_since_apoapsis.total_seconds()))
    text_apsides.top = False
    text_apsides.left = False

    text_params = InfoPanel()
    text_params.append("Inclination:")
    text_params.append("  {:.4f}°".format(degrees(satellite.inclination)))
    text_params.append("")
    text_params.append("RA of asc node:")
    text_params.append("  {:.4f}°".format(degrees(satellite.right_ascension_of_ascending_node)))
    text_params.append("")
    text_params.append("Arg of periapsis:")
    text_params.append("  {:.4f}°".format(degrees(satellite.argument_of_periapsis)))
    text_params.append("")
    text_params.append("Eccentricity:")
    text_params.append("  {:.7f}".format(satellite.eccentricity))
    text_params.append("")
    text_params.append("Semi-major axis:")
    text_params.append("  {:,.2f}km".format(satellite.semi_major_axis / 1000))
    text_params.append("")
    text_params.append("Mean anomaly @epoch:")
    text_params.append("  {:.4f}°".format(degrees(satellite.mean_anomaly_at_epoch)))
    text_params.append("")
    text_params.append("Epoch:")
    text_params.append(satellite.epoch.strftime("  %Y-%m-%d %H:%M:%S"))
    text_params.top = False
    text_params.left = True

    panels = [text_params, text_apsides, text_basic]

    if satellite.observer_latitude is not None and satellite.observer_longitude is not None:
        text_observer = InfoPanel()
        text_observer.append("Observer")
        text_observer.append("---")
        text_observer.append("Latitude:")
        text_observer.append("  {:.6f}°".format(satellite.observer_latitude))
        text_observer.append("")
        text_observer.append("Longitude:")
        text_observer.append("  {:.6f}°".format(satellite.observer_longitude))
        text_observer.append("")
        text_observer.append("Azimuth:")
        text_observer.append("  {:.2f}°".format(degrees(satellite.observer_azimuth)))
        text_observer.append("")
        text_observer.append("Altitude:")
        text_observer.append("  {:.2f}°".format(degrees(satellite.observer_altitude)))
        text_observer.top = True
        text_observer.left = False
        panels.append(text_observer)

    for text in panels:
        longest_line = max(map(len, text))

        text.padded_lines = []
        for line in text:
            if line == "---":
                text.padded_lines.append("┣" + "─" * (longest_line+2) + "┫")
            else:
                text.padded_lines.append("┃ " + line.ljust(longest_line+1) + "┃")
        text.padded_lines.insert(0, "┏" + "─" * (longest_line+2) + "┓")
        text.padded_lines.append("┗" + "─" * (longest_line+2) + "┛")

        if text.left:
            text.x = 2
        else:
            text.x = width - len(text.padded_lines[0]) - 1
        if text.top:
            text.y = 1
        else:
            text.y = height - len(text.padded_lines) - 1

        y = text.y
        for line in text.padded_lines:
            try:
                stdscr.addstr(y, text.x, line)
            except curses.error:
                # ignore attempt to draw outside screen
                pass
            y += 1


def draw_map(stdscr, body, night=True, topo=True):
    start = datetime.now()
    height, width = stdscr.getmaxyx()
    width -= 1

    if body.height != height or body.width != width:
        body = body.__class__(width, height)
        progress_str = "0.0"
        start = datetime.now()
        for progress in body.prepare_map():
            if progress_str != "{:.2f}".format(progress):
                progress_str = "{:.2f}".format(progress)
                elapsed_time = datetime.now() - start
                eta = (elapsed_time / max(progress, 0.01)) * (100 - progress)
                stdscr.erase()
                stdscr.addstr(0, 0, "Rendering map (ETA {}, {}%)...".format(
                    format_seconds(eta.total_seconds()),
                    progress_str,
                ))
                stdscr.refresh()

    for x in range(width):
        for y in range(height):
            if night:
                sun = ephem.Sun()
                obs = ephem.Observer()
                obs.pressure = 0
                lat, lon = body.to_latlon(x, y)
                obs.lat = "{:.8f}".format(lat)
                obs.lon = "{:.8f}".format(lon)
                sun.compute(obs)
                # astronomical twilight starts at -18°
                # -0.3141592 = radians(-18)
                night_factor = max(min(sun.alt, 0), -0.3141592) / -0.3141592
            else:
                night_factor = 0

            if body.map[x][y][3] is None:
                stdscr.addstr(y, x, " ", curses.color_pair(1))
            else:
                if topo is True:
                    r, g, b, color = body.map[x][y]
                else:
                    r, g, b, color = 0, 249, 114, 48
                if night_factor > -0.001:
                    night_r = 0
                    night_g = g * 0.2
                    night_b = min(b + 40, 255)
                    effective_r = ((1 - night_factor) * r) + (night_factor * night_r)
                    effective_g = ((1 - night_factor) * g) + (night_factor * night_g)
                    effective_b = ((1 - night_factor) * b) + (night_factor * night_b)
                    color = closest_color(effective_r, effective_g, effective_b)
                stdscr.addstr(y, x, "•", curses.color_pair(color))

    return body


def draw_orbits(stdscr, body, satellite, orbit_ascdesc=False, orbits=0, orbit_resolution="/70"):
    orbit_offset = timedelta()
    if orbit_resolution.startswith("/"):
        orbit_increment = satellite.orbital_period / int(orbit_resolution[1:])
    else:
        orbit_increment = timedelta(minutes=float(orbit_resolution))

    satellite.compute()
    previous_altitude = satellite.altitude

    while orbit_offset < satellite.orbital_period * orbits:
        orbit_offset += orbit_increment
        satellite.compute(plus_seconds=orbit_offset.total_seconds())

        if orbit_ascdesc:
            if satellite.altitude - previous_altitude >= 0:
                char = "+"
            else:
                char = "-"
            previous_altitude = satellite.altitude
        else:
            char = "•"

        try:
            x, y = body.from_latlon(satellite.latitude, satellite.longitude)
            stdscr.addstr(y, x, char, curses.color_pair(167))
        except ValueError:
            pass

    # reset values to current
    satellite.compute()


def draw_apsides(stdscr, body, satellite):
    try:
        x, y = body.from_latlon(satellite.apoapsis_latitude, satellite.apoapsis_longitude)
        stdscr.addstr(y, x, "A", curses.color_pair(167))
    except ValueError:
        pass
    try:
        x, y = body.from_latlon(satellite.periapsis_latitude, satellite.periapsis_longitude)
        stdscr.addstr(y, x, "P", curses.color_pair(167))
    except ValueError:
        pass


def draw_footprint(stdscr, body, satellite):
    height, width = stdscr.getmaxyx()
    earth_radius = earth_radius_at_latitude(satellite.latitude)
    horizon_radius = acos(earth_radius / (earth_radius + satellite.altitude))
    sat_lat = radians(satellite.latitude)
    sat_lon = radians(satellite.longitude)
    for horizon_lat, horizon_lon in cartesian_rotation(
        sat_lat,
        sat_lon,
        horizon_radius,
        steps=int(width * 1.5),  # somewhat arbitrary
    ):
        x, y = body.from_latlon(horizon_lat, horizon_lon)
        stdscr.addstr(y, x, "•", curses.color_pair(239))


def cartesian_rotation(lat, lon, r, steps=128):
    """
    Internally converts to Cartesian coordinates and applies a rotation
    matrix to yield a number of points (equal to steps) on the small
    circle described by the given latlon and radius (the latter being an
    angle as well).

    Taken almost verbatim from github.com/vain/asciiworld.
    """
    # Get latitude of one point on the small circle. We can easily do
    # this by adjusting the latitude but we have to avoid pushing over a
    # pole.
    if lat > 0:
        slat = degrees(lat) - degrees(r)
    else:
        slat = degrees(lat) + degrees(r)

    # Geographic coordinates to spherical coordinates.
    s_theta = -lat + radians(90)
    s_phi = lon

    # Cartesian coordinates of rotation axis.
    rx = sin(s_theta) * cos(s_phi)
    ry = sin(s_theta) * sin(s_phi)
    rz = cos(s_theta)

    # Rotation matrix around r{x,y,z} by alpha.
    alpha = radians(360.0 / steps)

    M = []
    M.append(rx**2 * (1 - cos(alpha)) + cos(alpha))
    M.append(ry * rx * (1 - cos(alpha)) + rz * sin(alpha))
    M.append(rz * rx * (1 - cos(alpha)) - ry * sin(alpha))

    M.append(rx * ry * (1 - cos(alpha)) - rz * sin(alpha))
    M.append(ry**2 * (1 - cos(alpha)) + cos(alpha))
    M.append(rz * ry * (1 - cos(alpha)) + rx * sin(alpha))

    M.append(rx * rz * (1 - cos(alpha)) + ry * sin(alpha))
    M.append(ry * rz * (1 - cos(alpha)) - rx * sin(alpha))
    M.append(rz**2 * (1 - cos(alpha)) + cos(alpha))

    # Cartesian coordinates of initial vector.
    s_theta = radians(-slat) + radians(90)
    s_phi = lon
    px = sin(s_theta) * cos(s_phi)
    py = sin(s_theta) * sin(s_phi)
    pz = cos(s_theta)

    for i in range(steps):
        # Rotate p{x,y,z}.
        p2x = px * M[0] + py * M[3] + pz * M[6]
        p2y = px * M[1] + py * M[4] + pz * M[7]
        p2z = px * M[2] + py * M[5] + pz * M[8]

        # For acos(), force p2z back into [-1, 1] which *might* happen
        # due to precision errors.
        p2z_fixed = max(-1, min(1, p2z))

        # Convert back to spherical coordinates and then geographic
        # coordinates.
        s_theta = acos(p2z_fixed)
        s_phi = atan2(p2y, p2x)

        lat = degrees(radians(90) - s_theta)
        lon = degrees(s_phi)

        # Use rotated p{x,y,z} as basis for next rotation.
        px = p2x
        py = p2y
        pz = p2z

        yield lat, lon


def draw_satellite(stdscr, body, satellite):
    try:
        x, y = body.from_latlon(satellite.latitude, satellite.longitude)
        stdscr.addstr(y, x, "X", curses.color_pair(16))
    except ValueError:
        pass


def draw_satellite_crosshair(stdscr, body, satellite):
    try:
        x, y = body.from_latlon(satellite.latitude, satellite.longitude)
    except ValueError:
        return
    for i in range(body.width-1):
        if body.map[i][y][3] is None:
            stdscr.addstr(y, i, "─", curses.color_pair(235))
    for i in range(body.height):
        if body.map[x][i][3] is None:
            stdscr.addstr(i, x, "|", curses.color_pair(235))


def draw_location(stdscr, body, lat, lon):
    x, y = body.from_latlon(lat, lon)
    stdscr.addstr(y, x, "•", curses.color_pair(2))
