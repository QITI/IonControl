#HamiltonianSim.py created 2023-02-13 12:02:51.304265

#sidebandCooling.py created 2022-09-07 17:34:32.160371

from scipy.constants import *
import numpy as np
import time
from enum import IntEnum
import json

import random
import shutil
import datetime

from spcm.util import make_time_series
import WaveformConstructor as wc
#import matplotlib.pyplot as plt

SAMPLING_RATE = 625 * mega

now = datetime.datetime.now()

data_dir = "Z:\\Data\\{0}\\{1:02}\\{2:02}\\".format(now.year, now.month, now.day)
time_tag = str(time.time())
time_tag_h = datetime.datetime.fromtimestamp(float(time_tag)).strftime('%Y%m%d_%H%M%S')

fname = data_dir+'awg_testing_{0}.py'.format(time_tag_h)

shutil.copyfile(r"Z:\Projects\Control System Files\IonControlFourRodTrapProject\FourRodTrap\config\Scripts\HamiltonianSim.py",
 fname)


generate_awg_files = True       # New AWG files will be created with the following parameters. 
#generate_awg_files = False                       # The previously stored files will be used. 

#global querying

microwave_pi_time = getGlobal("microwave_pi_time").m_as('us')


#parameters


#===============================================================================================================================
pi_time = 1.4

awg_microwave_time =0# microwave_pi_time # 0

sideband_cooling_time = 8000   #us
sideband_pumping_time = 20    #us, optical pumping time for the experiment 
pre_experiment_wait_time = 50 #us

amplitude_balance_factor = 1.0175 # rsb_rabi / bsb_rabi

frequency_carrier = 211.08199 #211.089993 #-0.001+0.00125#211.089985 #+10/mega#+0.005#211.71825  -0.628


#sideband_frequency = 212.244-frequency_carrier #1.033#1.0695 #1.08425 #for sideband cooling one ion (only really used for cooling)
sideband_frequency = 212.14 - frequency_carrier #for sideband cooling of two ions
#===============================================================================================================================

#generating red and blue sideband frequencies
frequency_sideBand_red = frequency_carrier - sideband_frequency #RSB frequency "center of forest" for CSBC
frequency_sideBand_blue = frequency_carrier + sideband_frequency #BSB frequency "center of forest"


sideBand_com_frequency = 212.2411 - frequency_carrier #for MS gate

frequency_sideBand_red_com = frequency_carrier - sideBand_com_frequency
frequency_sideBand_blue_com = frequency_carrier + sideBand_com_frequency

ms_detuning = 0.02 #this is the detuning from the com mode
freq_ms_rsb = frequency_sideBand_red_com - ms_detuning
freq_ms_bsb = frequency_sideBand_blue_com + ms_detuning


#tilt_mode_freqquency_offset = 0#-0.05 #offset from sideband_frequency to the lowest frequency tilt mode.  negative is towards carrier

#generating red and blue lowest frequency tilt mode
#frequency_sideBand_red_tilt  = frequency_sideBand_red - tilt_mode_freqquency_offset
#frequency_sideBand_blue_tilt = frequency_sideBand_blue + tilt_mode_freqquency_offset

#ms_detuning_from_tilt = -0.015#-0.015 #-0.01 #Molmer Sorenson detuning from the tilt mode.  negative is closer to carrier

#freq_ms_rsb = frequency_sideBand_red_tilt - ms_detuning_from_tilt 
#freq_ms_bsb = frequency_sideBand_blue_tilt + ms_detuning_from_tilt 

t_sideband = make_time_series(sideband_cooling_time * micro, SAMPLING_RATE)
v_sideband = 1*np.cos(2 * np.pi * (frequency_sideBand_red) * mega * t_sideband)
"""
t_sideband_main = make_time_series(sideband_cooling_time * micro*0.8, SAMPLING_RATE)
v_sideband_main = np.cos(2 * np.pi * (frequency_sideBand_red) * mega * t_sideband_main)

t_sideband_diagonal = make_time_series(sideband_cooling_time * micro*0.2, SAMPLING_RATE)
v_sideband_diagonal = np.cos(2 * np.pi * (frequency_sideBand_red_com) * mega * t_sideband_diagonal)

v_sideband = np.concatenate((t_sideband_main,v_sideband_diagonal))
"""
#v_sideband = 1*np.cos(2 * np.pi * (frequency_sideBand_red) * mega * t_sideband) #+ 0.5*np.sin(2 * np.pi * (frequency_sideBand_red+0.15) * mega * t_sideband)
    # + np.sin(2 * np.pi * (frequency_sideBand-0.06) * mega * t_sideband)#+ 0.5*np.sin(2 * np.pi * frequency_sideBand2 * mega * t_sideband) #+ \
    #0.5*np.cos(2 * np.pi * (frequency_sideBand+0.05) * mega * t_sideband)
#v_sideband = v_sideband/np.max(v_sideband)
#v_sideband = 1*np.cos(2 * np.pi * (frequency_sideBand_red) * mega * t_sideband) + 1*np.sin(2 * np.pi * (frequency_sideBand_red-0.8) * mega * t_sideband)
#v_sideband = v_sideband/np.max(v_sideband)
#t_sideband = make_time_series(sideband_cooling_time * micro, SAMPLING_RATE)

v_quiet = make_time_series((sideband_pumping_time + awg_microwave_time+pre_experiment_wait_time) * micro, SAMPLING_RATE) * 0


v_sideband = wc.to_int16(v_sideband)
v_quiet = wc.to_int16(v_quiet)

freq_list=[]
time_list = []
angle_list = []

waveform_series_collection = []

parameters = dict()

class ExpMode(IntEnum):
    CarrierFlop = 0
    FreqScan = 1
    MSTimeScan = 2
    RamanRamseyTimeScan = 3
    SBFlop = 4
    BB1Characterization = 5
    BB1CharacterizationTimeScan = 6
    BB1CharacterizationHalfPiScan = 7
    RamanRamseyFreqScan = 8
    DailyRamseyCalibration = 9
    
# Change the mode here

# ===========================================
mode = ExpMode.CarrierFlop
# ===========================================
parameters["mode"] = int(mode)
parameters["pi_time"] = pi_time
parameters["frequency_carrier"] = frequency_carrier
parameters["sideband_frequency"] = sideband_frequency
parameters["amplitude_balance_factor"] = amplitude_balance_factor

if mode == ExpMode.CarrierFlop:
    N = 201
    amplitude = 1
    raman_time = 50

    parameters["N"] = N
    parameters["amplitude"] = amplitude
    parameters["raman_time"] = raman_time

    for i, ti in enumerate(np.linspace(0, raman_time, N)):
        time_list.append(ti)
        waveform_series = wc.WaveformSeries(
            [ti * micro],
            [
                wc.CarrierFlopping(amplitude, 0, frequency_carrier * mega),
            ]
        )
        waveform_series_collection.append(waveform_series)
        
elif mode == ExpMode.SBFlop:
    N = 101
    raman_time = 800
    amplitude = 0.2#0.1
    flop_time = 0#2.65#pi_time
    SB_freq = frequency_sideBand_blue_com

    parameters["raman_time"] = raman_time
    parameters["amplitude"] = amplitude
    parameters["N"] = N
    parameters["flop_time"] = flop_time
    parameters["SB_freq"] = SB_freq
    
    for i, ti in enumerate(np.linspace(0, raman_time, N)):
        time_list.append(ti)
        waveform_series = wc.WaveformSeries(
            [flop_time*micro, ti * micro],
            [
                wc.CarrierFlopping(1, 0, frequency_carrier * mega),
                wc.CarrierFlopping(amplitude, 0, SB_freq * mega),
            ]
        )
        waveform_series_collection.append(waveform_series)

elif mode == ExpMode.FreqScan:
    
    frequency_center = frequency_sideBand_blue_com#-0.220#212.042 +0.06#frequency_sideBand_blue#frequency_sideBand_blue#-0.05
    
    amplitude = 0.05
    frequency_span = 0.1   #freq span in MHz
    raman_time = 150
    N = 201
    
    flop_time = 0 if frequency_center > frequency_carrier else pi_time
    
    parameters["frequency_center"] = frequency_center
    parameters["frequency_span"] = frequency_span
    parameters["amplitude"] = amplitude
    parameters["N"] = N
    parameters["flop_time"] = flop_time
    parameters["raman_time"] = raman_time


    for i, fi in enumerate(np.linspace(frequency_center - 0.5*frequency_span, frequency_center + 0.5*frequency_span, N, endpoint=True)):
        waveform_series = wc.WaveformSeries(
            [flop_time * micro, raman_time * micro],
            [
                wc.CarrierFlopping(1, 0, frequency_carrier * mega),
                wc.CarrierFlopping(amplitude, 0, fi * mega),
            ]
        )
        waveform_series_collection.append(waveform_series)
        
        freq_list.append(fi)

elif mode == ExpMode.MSTimeScan:
    N = 101
    raman_time = 10000
    amplitude = 0.01

    parameters["N"] = N
    parameters["amplitude"] = amplitude
    parameters["raman_time"] = raman_time

    for i, ti in enumerate(np.linspace(0, raman_time, N)):
        time_list.append(ti)
        waveform_series = wc.WaveformSeries(
            [ti * micro],
            [
                wc.MS(
                    amp_rsb=amplitude,
                    amp_bsb=amplitude * amplitude_balance_factor,
                    detuning=(sideBand_com_frequency+ms_detuning)*mega,
                    #detuning = 0.83 *mega,
                    phase_rsb=0,
                    phase_bsb=0,
                    carrier_freq=frequency_carrier*mega 
                )
            ]
        )
        waveform_series_collection.append(waveform_series)

elif mode == ExpMode.RamanRamseyTimeScan:
    N = 101
    raman_time = 20000
    amplitude = 0.15 # keep this below 0.15ish to not broaden the transition 

    By = 0.0005
    

    parameters["N"] = N
    parameters["amplitude"] = amplitude
    parameters["raman_time"] = raman_time
    parameters["By"] = By

    initial_pulse = wc.YSinglePulse(1, frequency_carrier * mega, pi_time=pi_time * micro).waveform_series(np.pi/2)
    final_pulse = wc.YSinglePulse(1, frequency_carrier * mega, pi_time=pi_time * micro).waveform_series(-np.pi/2)

    for i, ti in enumerate(np.linspace(0, raman_time, N)):
        time_list.append(ti)
        waveform_series = wc.WaveformSeries(
            [ti * micro],
            [
                #wc.Zero()
                wc.XX(
                    amplitude,
                    amplitude*1.0175,
                    (sideBand_com_frequency+ms_detuning)*mega,
                    frequency_carrier * mega
                )+wc.Y(By, frequency_carrier * mega)+wc.XFloquet(By*20,5*kilo,frequency_carrier * mega),
                #wc.Y(By, frequency_carrier * mega)
            ]
        )
        waveform_series = initial_pulse + waveform_series + final_pulse
        waveform_series_collection.append(waveform_series)

elif mode == ExpMode.RamanRamseyFreqScan:
    N = 101
    raman_time = 4000
    amplitude = 0.1
    frequency_span = 100/mega
    frequency_center = frequency_carrier
    

    parameters["N"] = N
    parameters["amplitude"] = amplitude
    parameters["raman_time"] = raman_time
    parameters["frequency_center"] = frequency_center
    parameters["frequency_span"] = frequency_span
    parameters["raman_time"] = raman_time



    for i, fi in enumerate(np.linspace(frequency_center - 0.5*frequency_span, frequency_center + 0.5*frequency_span, N, endpoint=True)):
        freq_list.append(fi)
        waveform_series = wc.WaveformSeries(
            [pi_time/2*micro, raman_time * micro, pi_time/2*micro],
            [
                wc.Y(1, fi*mega),
                #wc.Zero(),
                wc.YY(
                    amplitude,
                    amplitude,
                    (sideBand_com_frequency+ms_detuning)*mega,
                    fi*mega
                ),#+wc.Y(0.000, frequency_carrier)+wc.XFloquet(0.00,3*kilo,frequency_carrier),
                -wc.Y(1, fi*mega)
            ]
        )
        waveform_series_collection.append(waveform_series)

elif mode == ExpMode.BB1CharacterizationTimeScan:
    N = 41
    amplitude = 1
    raman_time = 20

    parameters["N"] = N
    parameters["amplitude"] = amplitude
    parameters["raman_time"] = raman_time

    initial_pulse = wc.XBB2(amplitude, frequency_carrier * mega, pi_time=pi_time * micro).waveform_series(np.pi/2)
  

    for i, ti in enumerate(np.linspace(0, raman_time, N)):
        time_list.append(ti)
        waveform_series = wc.WaveformSeries(
            [ti * micro],
            [
                wc.Y(amplitude, frequency_carrier * mega),
            ]
        )
        waveform_series_collection.append(initial_pulse + waveform_series)





elif mode == ExpMode.BB1Characterization:
    N = 21
    amplitude = 1
    raman_time = 100

    parameters["N"] = N
    parameters["amplitude"] = amplitude

    pre_flop = 8
    parameters["pre_flop"] = pre_flop


    composer = wc.XBB2(amplitude, frequency_carrier * mega, pi_time=pi_time * micro)

    for i, angle in enumerate(np.linspace(0, np.pi, N)):
        angle_list.append(angle)
        waveform_series = composer.waveform_series(angle)
        waveform_series_collection.append(composer.waveform_series(np.pi) * pre_flop + waveform_series)

elif mode == ExpMode.BB1CharacterizationHalfPiScan:
    N = 41
    amplitude = 1
    raman_time = 20

    parameters["N"] = N
    parameters["amplitude"] = amplitude
    parameters["raman_time"] = raman_time



    for i, ti in enumerate(np.linspace(0.5*pi_time, 1.5*pi_time, N)):
        time_list.append(ti)
        waveform_series = wc.XBB2(amplitude, frequency_carrier * mega, pi_time=ti * micro).waveform_series(np.pi/2)
        waveform_series_collection.append(waveform_series)


elif mode == ExpMode.DailyRamseyCalibration:
    N = 21
    raman_time = 50000
    #detuning = -2* 0.000025 #MHz from carrier
    
    detuning =0
    segments=1
    seg_time = 2000
    

    parameters["N"] = N
    parameters["raman_time"] = raman_time
    
    
    initial_pulse = wc.YSinglePulse(1, (frequency_carrier + detuning)* mega, pi_time=pi_time * micro).waveform_series(np.pi/2)
    final_pulse = wc.YSinglePulse(1, (frequency_carrier + detuning) * mega, pi_time=pi_time * micro).waveform_series(-np.pi/2)
    if segments == 1:
        for i, ti in enumerate(np.linspace(0, raman_time, N)):
            time_list.append(ti)
            waveform_series = wc.WaveformSeries(
                [ti * micro],
                [
                    wc.Zero()
                ]
            )
            waveform_series = initial_pulse + waveform_series + final_pulse
            waveform_series_collection.append(waveform_series)
    elif segments > 1:
        for seg_index in np.arange(segments+1):
            seg_start = seg_index*raman_time/segments
            for i, ti in enumerate(np.linspace(seg_start, seg_start+seg_time, N)):
                time_list.append(ti)
                
                waveform_series = wc.WaveformSeries(
                    [ti * micro],
                    [
                        wc.Zero()
                    ]
                )
                waveform_series = initial_pulse + waveform_series + final_pulse
                waveform_series_collection.append(waveform_series)

else:
    raise ValueError("Undefined Mode")

max_totaltime = 0


# Find the max length of the waveform
for ws in waveform_series_collection:
    assert isinstance(ws, wc.WaveformSeries)
    if(ws.total_time > max_totaltime):
        max_totaltime = ws.total_time

# Pad the waveform to the maximum length
for ws in waveform_series_collection:
    assert isinstance(ws, wc.WaveformSeries)
    ws.pad_to(max_totaltime)

# construct the waveform 
for i , vi in wc.WaveformFactory(waveform_series_collection, int(SAMPLING_RATE)).pipeline():
    print(i)
    v = np.concatenate((v_sideband, v_quiet, vi))
    
    assert v.dtype == np.int16
    np.save("D:\\awg_{}.npy".format(i), v)


awg_time = pre_experiment_wait_time +  max_totaltime/micro #total duration of AWG sequence AFTER SIDEBAND COOL, WEAK PUMP, AND MICROWAVE

#awg_time = sideband_pumping_time + awg_microwave_time + gap_time +  max_totaltime/micro #total duration of AWG sequence


setGlobal("awg_microwave_time", awg_microwave_time, 'us')

setGlobal("awg_time",awg_time,'us')
setGlobal("sideband_cooling_time",sideband_cooling_time,'us')
setGlobal("waveform_idx_num", len(waveform_series_collection),'')


setGlobal("use_external_trigger", 1,'')
setScan("scanWaveform")
startScan()
#setGlobal("sideband_cooling_time",0,'us')


tempData = getAllData()
pmt_counts_data = tempData['PMT Counts'][1]
time.sleep(0.5)

parameters["dataFileName"] = tempData["dataFileName"]
parameters["rawDataFileName"] = tempData["rawDataFileName"]

with open(fname + ".json", 'w') as f:
    f.write(json.dumps(parameters, indent=4))

if len(freq_list) > 0 :
    addPlot('Raman_freq_scan')
    createTrace('Raman_freq_scan', 'Raman_freq_scan', xUnit = 'MHz', xLabel='Freq')
    plotList(freq_list,pmt_counts_data,'Raman_freq_scan')

if len(time_list) > 0 :
    addPlot('Raman_time_scan')
    createTrace('Raman_time_scan', 'Raman_time_scan', xUnit = 'us', xLabel='time')
    plotList(time_list,pmt_counts_data,'Raman_time_scan')
    
if len(angle_list) > 0 :
    addPlot('Raman_angle_scan')
    createTrace('Raman_angle_scan', 'Raman_angle_scan', xUnit = 'rad', xLabel='angle')
    plotList(angle_list,pmt_counts_data,'Raman_angle_scan')


