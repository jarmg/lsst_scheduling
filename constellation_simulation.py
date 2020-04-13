
from datetime import datetime

import numpy as np

import pymap3d as pm
from astropy import time, units
from poliastro import bodies, twobody
from poliastro.plotting import OrbitPlotter3D


class SatelliteConstellation():

    def __init__(self, planes, sats_per_plane, altitude, inclination):
        self.planes = planes
        self.sats_per_plane = sats_per_plane
        self.altitude = altitude
        self.inclination = inclination
        self.satellites = self.__build_constellation(planes, sats_per_plane, altitude, inclination)

    def __len__(self):
        return len(self.satellites)

    def __build_constellation(self, planes, sats_per_plane, altitude, inclination):
        inc = units.Quantity(inclination, units.deg)
        alt = units.Quantity(altitude, units.km)

        #TODO: implement interplane phasing
        raans = np.linspace(0, (360 - 360/planes), planes)
        arglats = np.linspace(0, (360 - 360/sats_per_plane), sats_per_plane)

        satellites = np.array([
            twobody.orbit.Orbit.circular(
                attractor=bodies.Earth,
                alt=alt,
                inc=inc,
                raan=units.Quantity(plane_raan, units.deg),
                arglat=units.Quantity(arglat, units.deg)
            )
            for plane_raan in raans
            for arglat in arglats
        ])
        return satellites

    def plot(self, sats_to_plot=None):
        if not sats_to_plot:
            sats_to_plot = self.planes
        s = np.arange(0, len(self), len(self)//sats_to_plot)

        op = OrbitPlotter3D()
        for sat in self.satellites[s]: f = op.plot(sat)
        return f

    def _is_satellite_in_frame(self, ra, dec, loc, fov, sat_pass, ts):
        ra_rng = (ra - fov, ra + fov)
        dec_rng = (dec - fov, dec + fov)

        lat, lon, alt = loc

        for i, t in enumerate(ts):
            dt = datetime.fromtimestamp(int(t.value))
            x, y, z = sat_pass[i]
            az, el, rng = pm.eci2aer(sat_pass[i], lat, lon, alt, dt)
            ra_sat, dec_sat = pm.azel2radec(az, el, lat, lon, dt)
            if ra_rng[0] <= ra_sat <= ra_rng[1]:
                if dec_rng[0] <= dec_sat <= dec_rng[1]:
                    return True
        return False

    def check_observation(self, ra, dec, loc, fov, obs_time, obs_len):
        '''
        params:
            az: center azimuth of observation
            el: center elevation of observation
            loc: ecef telescope location (x, y, z)
            obs_time: GPS(?) #FIXME: figure this out
            fov: radius of the field of view in degrees
            obs_len: length of exposure (seconds)

        returns:
            bool: whether a satellite will be in the view
            TODO: Other info?
        '''

        resolution = 5 #check every 5 seconds - this is a linear optimization

        # ts = np.array([time.Time(t, format='unix') for t in range(int(obs_time), int(obs_time + obs_len))])
        ts = units.Quantity(range(int(obs_time), int(obs_time + obs_len), resolution), units.s)

        # Propogate satellites to the time of observation
        self.satellites = np.array([s.propagate(ts[0]) for s in self.satellites])

        # Get positions throughout the exposure
        ss = np.array([
            twobody.propagation.mean_motion(
                k=bodies.Earth.k,
                r=s.r,
                v=s.v,
                tofs=ts
            )
            for s in self.satellites
        ])

        # Check if any satellites cross the observation
        return np.any([
            self._is_satellite_in_frame(ra, dec,  loc, fov, sat_pass, ts)
            for sat_pass in ss[:, 1, :]])
