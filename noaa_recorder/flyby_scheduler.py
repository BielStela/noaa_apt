from datetime import datetime
from pathlib import Path
from threading import Timer

import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.date import DateTrigger
from orbit_predictor.sources import NoradTLESource

from autorec_noaa import get_noaa_img
from config import BCN, MAX_ELEV_GT, NOAA_IDS


def get_noaa_tle():
    tle_file = Path("noaa.tle")
    req = requests.get("https://www.celestrak.com/NORAD/elements/noaa.txt")
    if tle_file.exists():
        assert req.status_code == 200, f"Failed to download tle ({req.status_code})"
        with open("../noaa.tle", "r", newline="\n") as f:
            tle_is_updated = f.read() == req.text
        if not tle_is_updated:
            days_since_last_update = int(tle_file.stat() / (1e3 * 3600 * 24))
            with open("../noaa.tle", "w", newline="\n") as f:
                f.writelines(req.text)
            print(f"TLE has been updated. It was {days_since_last_update} days old.")
    else:
        assert req.status_code == 200, f"Failed to download tle ({req.status_code})"
        with open("../noaa.tle", "w", newline="\n") as f:
            f.writelines(req.text)


def main():
    while True:
        get_noaa_tle()
        source = NoradTLESource.from_file("../noaa.tle")
        next_passes = []
        for noaa_id in NOAA_IDS:
            predictor = source.get_predictor(noaa_id)
            next_pass = predictor.get_next_pass(BCN, max_elevation_gt=MAX_ELEV_GT)
            next_passes.append(next_pass)
        # may contain currently happening passes so filter out by aos and select the next
        next_pass = sorted(
            filter(lambda x: x.aos > datetime.utcnow(), next_passes),
            key=lambda n: n.aos,
        )[0]

        print(
            f"Going to record {next_pass.sate_id} flyby:"
            f"\n\tAOS: {next_pass.aos}"
            f"\n\tLOS: {next_pass.los}"
            f"\n\tDURATION: {next_pass.duration_s / 60 :.2f} min"
        )

        # sched = BlockingScheduler()
        # date_trigger = DateTrigger(next_pass.aos)
        # sched.add_job(
        #     get_noaa_img, date_trigger, [next_pass, sched], id="recording_noaa"
        # )
        # sched.start()

        t_to_flyby = next_pass.aos - datetime.utcnow()

        timer = Timer(t_to_flyby.seconds, get_noaa_img, [next_pass])
        timer.start()
        print(f"Image adquisition will start in {t_to_flyby.seconds} seconds")
        timer.join()


if __name__ == "__main__":
    main()
