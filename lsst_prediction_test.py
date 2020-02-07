import numpy as np

# import pass_prediction as pp
import constellation_simulation as sc
import pytest


@pytest.mark.skip(reason="version issue")
def test_predict():
    t = 1581051094.66090
    ret = pp.satellite_obstruction(
        az= 0 ,
        el= 0,
        loc=  (-30.169, 70.804, 2200),
        fov= 10,
        obs_time= t,
        obs_len= 300000
    )
    print(ret)

@pytest.mark.skip(reason="")
def test_constellation_sim():
    c = sc.SatelliteConstellation(planes=18, sats_per_plane=20, altitude=550, inclination=53)
    print(c)

@pytest.mark.skip(reason="don't show plot")
def test_plot():
    c = sc.SatelliteConstellation(planes=18, sats_per_plane=20, altitude=550, inclination=53)
    f = c.plot(sats_to_plot=5)
    f.show()

@pytest.mark.skip(reason="")
def test_observation_check():
     c = sc.SatelliteConstellation(planes=8, sats_per_plane=2, altitude=550, inclination=53)
     p = c.check_observation(
         ra=10,
         dec=10,
         loc=(-30.169, 70.804, 2200),
         fov=5,
         obs_time=1581066487.7915795,
         obs_len=30
     )
     print(p)


def test_observation_check():
    c = sc.SatelliteConstellation(planes=72, sats_per_plane=20, altitude=550, inclination=53)
    ra = np.random.rand(100) * 360
    dec = np.random.rand(100) * 90
    for ra, dec in zip(ra,dec):
        p = c.check_observation(
            ra=ra,
            dec=dec,
            loc=(-30.169, 70.804, 2200),
            fov=5,
            obs_time=1581066487.7915795,
            obs_len=30
        )
        print(p)    