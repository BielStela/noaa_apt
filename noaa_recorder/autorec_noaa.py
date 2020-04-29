import asyncio
import subprocess
import time
from datetime import datetime
from typing import List

import numpy as np
import scipy.signal as signal
from rtlsdr import RtlSdr
from scipy.io import wavfile

from config import DOWNLINK_FREQS


async def streaming(sdr: RtlSdr, time_s: int) -> List[np.ndarray]:
    all_samples = []
    t_before = time.time()
    print("recording samples...")
    async for samples in sdr.stream():
        all_samples.append(samples)
        if time.time() - t_before >= time_s:
            break
    # clean device
    await sdr.stop()
    sdr.close()
    return all_samples


def get_demodulated_samples(freq: float, time_s: int) -> np.ndarray:
    sdr = RtlSdr()
    sat_freq = freq * 1e6  # freqs are MHz
    sdr.gain = 15
    freq_offset = 250000  # avoid DC spike at center frequency
    sdr.center_freq = sat_freq - freq_offset
    sdr.sample_rate = 1140000
    time.sleep(0.1)  # a bit of time so the SDR device can pickup the config

    samples = asyncio.run(streaming(sdr, time_s))
    # samples = loop.run_until_complete(streaming(sdr, time_s))
    # convert samples to flat np array
    samples = np.array(samples).ravel().astype("complex64")
    # center samples
    fc1 = np.exp(-1.0j * 2.0 * np.pi * freq_offset / sat_freq * np.arange(len(samples)))
    shifted_samples = samples * fc1

    # An APT broadcast signal has a bandwidth of around 40kHz
    freq_bw = 40000
    dec_rate = int(sat_freq / freq_bw)
    decimated_samples = signal.decimate(shifted_samples, dec_rate)
    # Calculate the new sampling rate
    fs_y = sat_freq / dec_rate

    # polar discriminator
    y = decimated_samples[1:] * np.conj(decimated_samples[:-1])
    demodulated_samples = np.angle(y)

    d = fs_y * 75e-6  # Calculate the # of samples to hit the -3dB point
    x = np.exp(-1 / d)  # Calculate the decay between each sample
    b = [1 - x]  # Create the filter coefficients
    a = [1, -x]
    x6 = signal.lfilter(b, a, demodulated_samples)

    # Find a decimation rate to achieve audio sampling rate between 44-48 kHz
    audio_freq = 44100.0
    dec_audio = int(fs_y / audio_freq)
    # audio_samp_rate = fs_y / dec_audio

    x7 = signal.decimate(x6, dec_audio)
    # Scale audio to adjust volume
    x7 *= 10000 / np.max(np.abs(x7))
    return x7.astype("int16")


def signal_to_img(sat_name: str, samples: np.ndarray):
    # save wave file
    f_name = f'{sat_name.replace(" ", "_")}_{datetime.now()}'
    wavfile.write(f"../audios/{f_name}.wav", 44100, samples)
    # call noaa-apt to convert audio signal to image.
    subprocess.run(
        ["~/bin/noaa-apt", f"-o ../images/{f_name}.png", f"../audios/{f_name}.wav"],
        shell=True,
        check=True,
    )


def get_noaa_img(next_pass):
    sat_name = next_pass.sate_id
    sat_freq = DOWNLINK_FREQS[sat_name]
    samples = get_demodulated_samples(sat_freq, next_pass.duration_s)
    signal_to_img(sat_name, samples)
