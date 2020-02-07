####
#Predict starlink passes using Celestrak TLE data 
####

import json
import logging
import time
import os
import shutil

import pandas as pd
import numpy as np
import predict
import requests
from datetime import date

# space-track sucked
data_url = "https://www.celestrak.com/NORAD/elements/starlink.txt"

#TODO: Centralize configs for both email and pass locations

#NOTE: Predict uses west longitude
telescopes = {"ctio": (-30.169, 70.804, 2200)}

logging.basicConfig(level=logging.INFO)


def get_celestrack_data():
    tles = []
    r = requests.get(data_url)
    r.raise_for_status()
    lines = r.iter_lines()

    while True:
        try:
            l1, l2, l3 = lines.next().strip(), lines.next(), lines.next()
            if l3 == '':
                l3 = lines.next() #HACK: Extra newline in response which is solved by just getting next line if found
            tle = '\n'.join([l1, l2, l3])
            tles.append(tle)
        except StopIteration:
            return np.array(tles)


def get_pass_metrics(ground_pass):
    ''' Formats the pass data for terminal output. Expects a pandas DataFrame'''
    sat_name = ground_pass.tle[0]
    start, end, peak = ground_pass.at(ground_pass.start), ground_pass.at(ground_pass.end), ground_pass.peak()
    start_time = time.gmtime(ground_pass.start)
    peak_time = time.gmtime(peak['epoch'])
    end_time = time.gmtime(ground_pass.end)

    return {
        "sat_name": sat_name,
        "duration": int(ground_pass.duration()),
        "start_date": time.strftime("%x", start_time),
        "start_time_GMT": time.strftime("%X", start_time),
        "end_time_GMT": time.strftime("%X", end_time),
        "peak_time_GMT": time.strftime("%X", peak_time),
        "peak_azimuth": peak['azimuth'],
        "peak_elevation": peak['elevation'],
        "start_azimuth": start['azimuth'],
        "start_elevation": start['elevation'],
        "end_azimuth": end['azimuth'],
        "end_elevation": end['elevation']
    }


def get_sat_passes(tles, location, days_to_forecast):
    ''' location -> (lat, lon, alt): provides location of the telescope '''
    predictions = [predict.transits(tle, location, ending_after=time.time(), ending_before=(time.time() + days_to_forecast * (24*60*60))) for tle in tles]
    return predictions


def filter_visible_passes(satellites, min_duration=20, min_elevation=25):
    _is_valid_pass = lambda p: p.peak()['elevation'] > min_elevation and p.duration() > min_duration
    all_visible_passes = []
    for sat in satellites:
        try:
            passes = list(sat) # get passes from generator
        except predict.PredictException:
            continue
        visible_passes = [p.prune(lambda ts: p.at(ts)['visibility'] == 'V') for p in passes]
        all_visible_passes += visible_passes
    valid_passes = [ps for ps in all_visible_passes if _is_valid_pass(ps)]
    return valid_passes


def write_visible_passes(visible_passes, file_name, data_dir):
    pass_info = [get_pass_metrics(ps) for ps in visible_passes]
    columns = [
        "sat_name", "duration", "start_date", "start_time_GMT", "end_time_GMT", "peak_time_GMT", "peak_azimuth",
        "peak_elevation", "start_azimuth", "start_elevation", "end_azimuth", "end_elevation"
    ]
    df = pd.DataFrame(pass_info, columns=columns).sort_values(by='start_time_GMT')
    file_path = os.path.join(data_dir, file_name) 
    df.to_csv(file_path)
    print("Wrote {} passes to {}".format(len(df), file_name))
    return df


def main(data_dir='pass_output', days_to_forecast=4):
    logging.info("Run predictions")
    dt = date.today()
    tles = get_celestrack_data()

    for telescope, lla, in telescopes.items():
        logging.info("Finding passes for {} telescope at lat/lon/alt: {}, {}, {}".format(telescope, *lla))
        sat_passes = get_sat_passes(tles, lla, days_to_forecast)
        visible_passes = filter_visible_passes(sat_passes, min_duration=1, min_elevation=25)
        write_visible_passes(visible_passes, '{}_visible_passes_{}.csv'.format(telescope, dt), data_dir)




def satellite_obstruction(az, el, loc, fov, obs_time, obs_len):
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
    all_visible_passes = []

    az_rng = (az - fov, az + fov)
    el_rng = (el - fov, el + fov)

    tles = get_celestrack_data()
    sat_passes = [
        predict.transits(
            tle,
            loc,
            ending_after=obs_time,
            ending_before=(obs_time + obs_len) #FIXME: think about this more
        )
        for tle in tles
    ]
    for passes in sat_passes:
        
        try:
            ps = list(passes) #unpack generator
        except predict.PredictException:
            print("ISSUE!")
            continue
        
            
        visible_passes = [
            p.prune(
                lambda ts: (
                    p.at(ts)['visibility'] == 'V' and
                    az_rng[0] <= p.at(ts)['azimuth'] <= az_rng[1] and
                    el_rng[0] <= p.at(ts)['elevation'] <= el_rng[1] 
                )
            ) 
            for p in ps
        ]
    
        passes_in_observation = [p for p in visible_passes if p.duration() > 0]

        all_visible_passes += passes_in_observation

    return all_visible_passes
    
