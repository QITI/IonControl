# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from collections import OrderedDict

import logging
import numpy

from modules.quantity import Q
from .ExternalParameterBase import ExternalParameterBase
from ProjectConfig.Project import getProject
from uiModules.ImportErrorPopup import importErrorPopup
from .qtHelper import qtHelper
import time

project = getProject()
visaEnabled = project.isEnabled('hardware', 'VISA')
from PyQt5 import QtCore

if visaEnabled:
    try:
        import visa
    except ImportError:  # popup on failed import of enabled visa
        importErrorPopup('VISA')

SRS_DS345_Enabled = project.isEnabled('hardware', 'QITI SRS DS345 Function Generator')

if SRS_DS345_Enabled:
    from QITI_communicate_instruments.srs.ds345 import DS345


    class SRS_DS345_FunctionGenerator(ExternalParameterBase):
        '''
        Communicate with the SRS DS345 function generator.
        
        instrument(str) -> name of the instrument should match with the name given on the initial project config
        
        '''
        className = 'QITI SRS DS345 Function Generator'''
        _outputChannels = OrderedDict([('Frequency', 'kHz'),
                                       ('Amplitude(Vpp)', 'V'),
                                       ('Offset', 'V'),
                                       ('Function', '')])
        # _inputChannels = OrderedDict([('Frequency','kHz'),
        # ('Amplitude(Vpp)','V'),
        # ('Offset','V'),
        # ('Function','')])
        _outputLookup = {'Frequency': ('frequency', 'Hz'),
                         'Amplitude(Vpp)': ('amplitude', 'V'),
                         'Offset': ('offset', 'V'),
                         'Function': ('function', '')}

        def __init__(self, name, config, globalDict, instrument):
            logger = logging.getLogger(__name__)
            ExternalParameterBase.__init__(self, name, config, globalDict)
            project = getProject()
            instrument_list = project.hardware.get('QITI SRS DS345 Function Generator')
            instrument = instrument_list[instrument]
            ip_addr = instrument.get('Prologix IP')
            gpib_addr = instrument.get('GPIB Addr')
            self.DS345 = DS345(ip_addr, gpib_addr)
            logger.info("Trying to connect to the DS345 Function generator {0},{1}".format(ip_addr, gpib_addr))
            self.DS345.connect()
            self.initializeChannelsToExternals()
            self.qtHelper = qtHelper()
            self.newData = self.qtHelper.newData

        def setValue(self, channel, v):
            func_name, unit = self._outputLookup[channel]
            setattr(self.DS345, func_name, v.m_as(unit))
            return v

        def getValue(self, channel):
            func_name, unit = self._outputLookup[channel]
            v = getattr(self.DS345, func_name)
            return Q(v, unit)

        def getExternalValue(self, channel):
            return self.getValue(channel)

        def connectedInstruments(self):
            project = getProject()
            instrument_list = project.hardware.get('QITI SRS DS345 Function Generator').keys()
            return instrument_list

laserfreqPID_Enabled = project.isEnabled('hardware', 'QITI Laser Frequency PID Lock')

if laserfreqPID_Enabled:
    try:
        from QITI_WavemeterLock.PID_client.PID_client import ConfigREQClient
    except ImportError:
        importErrorPopup('Laser Frequency PID client')


    class LaserFreqPID(ExternalParameterBase):
        """
        Adjust the freq_setpoint and the lock status of the laser frequency PID lock
        """
        className = 'QITI Laser Frequency PID Lock'
        _outputChannels = OrderedDict([("FrequencySetpoint", "THz"), ("EnableLock", "")])
        _inputChannels = OrderedDict([("FrequencySetpoint", "THz"), ("EnableLock", "")])
        _outputLookup = {
            'FrequencySetpoint': ("freq_setpoint", "THz", lambda x: eval(x)[0], lambda x: str([x])),
            "EnableLock": ("enable_lock", "", lambda v: float(v == 'True'), lambda v: str(bool(v)))
        }

        def __init__(self, name, config, globalDict, instrument):
            logger = logging.getLogger(__name__)
            ExternalParameterBase.__init__(self, name, config, globalDict)
            project = getProject()
            server_list = project.hardware.get('QITI Laser Frequency PID Lock').items()
            server_name, server = list(server_list)[0]
            server_address, server_port = server.get('PIDServerAddress').split(":")
            self.instrument = instrument
            self.client_config = {
                'server_settings':
                    {
                        'config_server_ip': server_address,
                        'config_request_port': server_port
                    },
                instrument:
                    {'freq_setpoint': None,
                     'enable_lock': None
                     }
            }
            self.ConfigREQClient = ConfigREQClient(self.client_config)
            logger.info("Trying to connect to the PID server {0}".format(server))
            self.ConfigREQClient.connect()
            self.initializeChannelsToExternals()
            self.qtHelper = qtHelper()
            self.newData = self.qtHelper.newData

            # self.initOutput()

        def setValue(self, channel, v):
            config_name, unit, get_func, set_func = self._outputLookup[channel]
            self.client_config[self.instrument][config_name] = set_func(v.m_as(unit))
            self.ConfigREQClient.update_config(self.client_config)
            self.ConfigREQClient.set_config()
            self.newData.emit(self.name + "_" + channel, (time.time(), self.getValue(channel)))
            return v

        def getValue(self, channel):
            config_name, unit, get_func, set_func = self._outputLookup[channel]
            self.client_config = self.ConfigREQClient.get_config()
            return Q(get_func(self.client_config[self.instrument][config_name]), unit)

        def getExternalValue(self, channel):
            # config_name,unit,get_func,set_func = self._outputLookup[channel]
            # return Q( get_func(self.client_config[self.instrument][config_name]), unit )
            return self.getValue(channel)

DC_Controller_Enabled = project.isEnabled('hardware', 'QITI Four rod DC Controller')

if DC_Controller_Enabled:
    try:
        from QITI_DC_Voltage_Control.src.DC_voltage_control_python.dc_ctr_rpc_client import FourRodDCControllerClient
        from QITI_DC_Voltage_Control.src.DC_voltage_control_python.dc_ctr_enum import *
    except ImportError:
        importErrorPopup('DC Voltage Control')


    class DCVoltageControl(ExternalParameterBase):
        """
        Control the voltages on rods and needles for the four rod trap
        """
        className = "Four rod DC Voltage Control"
        _outputChannels = OrderedDict([
            ('Enable Remote Control', ''),
            ('Needle_1_Voltage', 'V'),
            ('Needle_2_Voltage', 'V'),
            ('Rod_1_Voltage', 'V'),
            ('Rod_2_Voltage', 'V'),
            ('Rod_3_Voltage', 'V'),
            ('Rod_4_Voltage', 'V')])

        _outputLookup = {
            'Needle_1_Voltage': CHANNEL_N1,
            'Needle_2_Voltage': CHANNEL_N2,
            'Rod_1_Voltage': CHANNEL_R1,
            'Rod_2_Voltage': CHANNEL_R2,
            'Rod_3_Voltage': CHANNEL_R3,
            'Rod_4_Voltage': CHANNEL_R4
        }

        def __init__(self, name, config, globalDict, instrument):
            logger = logging.getLogger(__name__)
            ExternalParameterBase.__init__(self, name, config, globalDict)
            project = getProject()
            instrument_list = project.hardware.get('QITI Four rod DC Controller')
            instrument = instrument_list[instrument]
            ip_addr = instrument.get('ipAddress')
            port = instrument.get('port')
            self.dc_client = FourRodDCControllerClient(address=ip_addr + ':' + port)

            # self.initializeChannelsToExternals()
            self.initOutput()
            self.qtHelper = qtHelper()
            self.newData = self.qtHelper.newData

        def setValue(self, channel, v):
            if channel == 'Enable Remote Control':
                v_value = v.m_as('')
                v_value = int(v_value)
                if v_value not in (0, 1, 255):
                    raise ValueError("Not an available mode!!!!!")
                self.dc_client.set_mode_all(v_value)
            else:
                v_value = v.m_as('V')
                v_value = float(v_value)
                v_channel = self._outputLookup[channel]
                print(v_channel, v_value)
                self.dc_client.set_volt(v_channel, v_value)
            return v

        def getExternalValue(self, channel=None):
            if channel == 'Enable Remote Control':
                mode = self.dc_client.get_mode(CHANNEL_N1)
                return Q(mode, '')
            else:
                v_channel = self._outputLookup[channel]
                voltage = self.dc_client.get_volt_adc(v_channel)
                voltage = round(voltage, 4)
                return Q(voltage, 'V')

        def connectedInstruments(self):
            project = getProject()
            instrument_list = project.hardware.get('QITI Four rod DC Controller').keys()
            return instrument_list


four_rod_oven_controller_enabled = project.isEnabled('hardware', 'QITI Four Rod Oven Controller')

if four_rod_oven_controller_enabled:
    try:
        from QITI_four_rod_oven_controller.four_rod_oven_controller.four_rod_oven_controller_client import FourRodOvenControllerClient
    except ImportError:
        importErrorPopup('four rod oven control')


    class FourRodOvenControl(ExternalParameterBase):
        """
        Control the current and voltage of the BK Precision power supply that powers the four rod trap oven
        """
        className = "Four Rod Oven Control"
        _outputChannels = OrderedDict([
            ('Oven current set', 'A'),
            ('Oven voltage set', 'V'),
            ('Oven current reading (read only)', 'A'),
            ('Oven voltage reading (read only)', 'V'),
            ('Oven status (0=CV, 1=CC)', '')
            ])
        
        _outputLookup = {
            'Oven current set': ('A','current_set'),
            'Oven voltage set': ('V','voltage_set'),
            'Oven current reading (read only)': ('A','current_reading'),
            'Oven voltage reading (read only)': ('V','voltage_reading'),
            'Oven status (0=CV, 1=CC)': ('','status')
            }


        def __init__(self, name, config, globalDict, instrument):
            logger = logging.getLogger(__name__)
            ExternalParameterBase.__init__(self, name, config, globalDict)
            project = getProject()
            instrument_list = project.hardware.get('QITI Four Rod Oven Controller')
            instrument = instrument_list[instrument]
            ip_addr = instrument.get('ipAddress')
            port = instrument.get('port')
            self.oven_client = FourRodOvenControllerClient(address=ip_addr + ':' + port)

            # self.initializeChannelsToExternals()
            self.initOutput()
            self.qtHelper = qtHelper()
            self.newData = self.qtHelper.newData

        def setValue(self, channel, v):
            if channel == 'Oven current set':
                v_value = v.m_as('A')
                v_value = float(v_value)
                self.oven_client.set_current(v_value)
            if channel == 'Oven voltage set':
                v_value = v.m_as('V')
                v_value = float(v_value)
                self.oven_client.set_voltage(v_value)
            return v

        def getValue(self, channel):
            unit, data_key = self._outputLookup[channel]
            self.oven_data = self.oven_client.get_data()
            return Q(self.oven_data[data_key], unit)

        def getExternalValue(self, channel):
            return self.getValue(channel)

        def connectedInstruments(self):
            project = getProject()
            instrument_list = project.hardware.get('QITI Four Rod Oven Controller').keys()
            return instrument_list


rfcontroller_enabled = project.isEnabled('hardware', 'QITI RF Controller')

if rfcontroller_enabled:
    try:
        from rf_controller.rf_controller.rf_controller_client import RFControllerClient
    except ImportError:
        importErrorPopup("RF Controller")


    class RFController(ExternalParameterBase):
        className = "RF Controller"
        _outputChannels = OrderedDict([
            #("frequency_cooling_eom", 'MHz'),
            ("frequency_detection_aom", 'MHz'),
            ("frequency_repump_eom", 'MHz'),
            ("frequency_cooling_aom", 'MHz'),
            ("frequency_optpump_eom", 'MHz'),
            ("frequency_microwave_modulation", 'MHz'),
            ("frequency_dmd_aom", 'MHz'),
            ("frequency_four_rod_weak_optical_pumping", 'MHz'),
            ("frequency_four_rod_raman_2_lo", 'MHz'),
            ("frequency_four_rod_dmd_optpump_eom", 'MHz'),
            ("frequency_four_rod_raman_1_aom", 'MHz'),
            #("power_cooling_eom", ''),
            ("power_detection_aom", ''),
            ("power_repump_eom", ''),
            ("power_cooling_aom", ''),
            ("power_optpump_eom", ''),
            ("power_microwave_modulation", ''),
            ("power_four_rod_raman_2_lo", ''),
            ("power_dmd_aom", ''),
            ("power_four_rod_weak_optical_pumping", ''),
            ("power_four_rod_dmd_optpump_eom", ''),
            ("power_four_rod_raman_1_aom", ''),
            #("output_state_cooling_eom",''),
            ("output_state_microwave_modulation", ''),
            ("output_state_four_rod_raman_2_lo", ''),
            ("vernier_dmd_aom", ''),
            ("vernier_four_rod_weak_optical_pumping",'')
        ])

        _outputLookup = {
            'frequency_cooling_eom': ("four_rod_cooling_eom", "frequency"),
            'frequency_detection_aom': ("four_rod_detection_aom", "frequency"),
            'frequency_repump_eom': ("four_rod_repump_eom", "frequency"),
            'frequency_cooling_aom': ("four_rod_cooling_aom", "frequency"),
            'frequency_optpump_eom': ("four_rod_optpump_eom", "frequency"),
            'frequency_microwave_modulation': ("four_rod_microwave_modulation", "frequency"),
            'frequency_dmd_aom': ("four_rod_dmd_aom", "frequency"),
            'frequency_four_rod_weak_optical_pumping': ("four_rod_weak_optical_pumping", "frequency"),
            'frequency_four_rod_raman_2_lo': ("four_rod_raman_2", "frequency"),
            'frequency_four_rod_dmd_optpump_eom': ("four_rod_dmd_optpump_eom", "frequency"),
            'frequency_four_rod_raman_1_aom': ("four_rod_raman_1_aom", "frequency"),
            'power_cooling_eom': ("four_rod_cooling_eom", "power"),
            'power_detection_aom': ("four_rod_detection_aom", "power"),
            'power_repump_eom': ("four_rod_repump_eom", "power"),
            'power_cooling_aom': ("four_rod_cooling_aom", "power"),
            'power_optpump_eom': ("four_rod_optpump_eom", "power"),
            'power_microwave_modulation': ("four_rod_microwave_modulation", "power"),
            'power_dmd_aom': ("four_rod_dmd_aom", "power"),
            'power_four_rod_weak_optical_pumping': ("four_rod_weak_optical_pumping", "power"),
            'power_four_rod_raman_2_lo': ("four_rod_raman_2", "power"),
            'power_four_rod_dmd_optpump_eom': ("four_rod_dmd_optpump_eom", "power"),
            'power_four_rod_raman_1_aom': ("four_rod_raman_1_aom", "power"),
            'output_state_cooling_eom': ("four_rod_cooling_eom", "output_state"),
            'output_state_microwave_modulation': ("four_rod_microwave_modulation", "output_state"),
            'output_state_four_rod_raman_2_lo': ("four_rod_raman_2", "output_state"),
            'vernier_dmd_aom': ("four_rod_dmd_aom", "vernier"),
            "vernier_four_rod_weak_optical_pumping":("four_rod_weak_optical_pumping","vernier")
        }

        # TODO: pint doesn't support pint. Modify pint?
        _unitLookup = {
            "frequency": "Hz",
            "power": "",
            "output_state":"",
            "vernier":""
        }

        _setTypeLookup = {
            "frequency": int,
            "power": float,
            "output_state":bool,
            "vernier":int
        }
        _getTypeLookup = {
            "frequency": int,
            "power": float,
            "output_state":int,
            "vernier":int
        }

        def __init__(self, name, config, globalDict, instrument):
            logger = logging.getLogger(__name__)
            ExternalParameterBase.__init__(self, name, config, globalDict)
            project = getProject()
            instrument_list = project.hardware.get('QITI RF Controller')
            instrument = instrument_list[instrument]
            ip_addr = instrument.get('ipAddress')
            port = instrument.get('port')

            # self.initializeChannelsToExternals()
            self.initOutput()
            self.client = RFControllerClient(ip_addr + ':' + port)
            self.qtHelper = qtHelper()
            self.newData = self.qtHelper.newData

        def setValue(self, channel, v):
            rf_channel, parameter_name = self._outputLookup[channel]
            parameter = v.m_as(self._unitLookup[parameter_name])
            print(channel, parameter, v)
            parameter = self._setTypeLookup[parameter_name](parameter)
            getattr(self.client, "set_" + parameter_name)(rf_channel, parameter)
            return v

        def getExternalValue(self, channel=None):
            rf_channel, parameter_name = self._outputLookup[channel]
            #print("rf controller", rf_channel, parameter_name)
            parameter = getattr(self.client, "get_" + parameter_name)(rf_channel)
            parameter = self._getTypeLookup[parameter_name](parameter)
            return Q(parameter, self._unitLookup[parameter_name])

        def connectedInstruments(self):
            project = getProject()
            instrument_list = project.hardware.get('QITI RF Controller').keys()
            return instrument_list

piadc_enabled = project.isEnabled('hardware', 'QITI PI ADC')

if piadc_enabled:
    try:
        from PI_ADC.PiADC import PiADCWebClient
    except ImportError:
        importErrorPopup("PI ADC")


    class PiADC(ExternalParameterBase):
        className = "PI ADC"
        _outputChannels = OrderedDict([
            ("pi_adc_ch0", 'V'),
            ("pi_adc_ch1", 'V'),
            ("pi_adc_ch2", 'V'),
            ("pi_adc_ch3", 'V'),
            ("pi_adc_ch4", 'V'),
            ("pi_adc_ch5", 'V'),
            ("pi_adc_ch6", 'V'),
            ("pi_adc_ch7", 'V')
        ])


        def __init__(self, name, config, globalDict, instrument):
            logger = logging.getLogger(__name__)
            ExternalParameterBase.__init__(self, name, config, globalDict)
            project = getProject()
            instrument_list = project.hardware.get('QITI RF Controller')
            instrument = instrument_list[instrument]
            ip_addr = instrument.get('ipAddress')
            port = instrument.get('port')

            # self.initializeChannelsToExternals()
            self.initOutput()
            self.client = PiADCWebClient.PiADCWebClient(ip_addr + ':' + port)
            self.qtHelper = qtHelper()
            self.newData = self.qtHelper.newData

        def setValue(self, channel, v):
            return v

        def getExternalValue(self, channel=None):
            channel_num = int(channel[-1])
            parameter = self.client.read_channel(channel_num)
            return Q(parameter, "V")

        @staticmethod
        def connectedInstruments(self):
            project = getProject()
            instrument_list = project.hardware.get('QITI PI ADC').keys()
            return instrument_list

dmd_enabled = project.isEnabled('hardware', 'LuxbeamController')

if dmd_enabled:
    try:
        from pySLM2.util import LuxbeamController
        import numpy as np
    except ImportError as err:
        print(err)
        importErrorPopup('LuxbeamController')


    class Luxbeam4600Control(ExternalParameterBase):
        className = "LuxbeamController"
        _outputChannels = OrderedDict([
            ("hologram_idx", '')
        ])

        def __init__(self, name, config, globalDict, instrument):
            global DMD_HOLOGRAM_DATABASE
            DMD_HOLOGRAM_DATABASE = []
            logger = logging.getLogger(__name__)
            ExternalParameterBase.__init__(self, name, config, globalDict)
            project = getProject()
            instrument_list = project.hardware.get('LuxbeamController')
            instrument = instrument_list[instrument]
            ip_addr = instrument.get('ipAddress')

            invert = instrument.get('invert(y/n)')
            self.data_dir = instrument.get('data_dir')

            if invert=="y":
                invert = True
            elif invert=="n":
                invert= False

            self.luxbeam = LuxbeamController(ip_addr, invert=invert)
            self.luxbeam.initialize()

            # self.initializeChannelsToExternals()
            self.initOutput()

            self.qtHelper = qtHelper()
            self.newData = self.qtHelper.newData
            self.i = -1.0

        def setValue(self, channel, v):
            assert channel=="hologram_idx"
            parameter = v.m_as("")

            parameter = int(parameter)
            self.i = float(parameter)

            img = np.load(self.data_dir + "{}.npy".format(parameter))

            self.luxbeam.load_single(img)
            return v

        def getExternalValue(self, channel=None):
            assert channel == "hologram_idx"
            return Q(self.i, '')

        def connectedInstruments(self):
            project = getProject()
            instrument_list = project.hardware.get('LuxbeamController').keys()
            return instrument_list



sana_enabled = project.isEnabled('hardware', 'QITI SANA')

if sana_enabled:
    try:
        from QITI_WavemeterLock.PID_client.PID_client import PIDServerGRPCClient
    except ImportError as err:
        print(err)
        importErrorPopup('SANA')

    class SANAControl(ExternalParameterBase):
        className = "SANA"
        _outputChannels = OrderedDict([
            ("dmd_FP_mirror_horizontal", 'V'),
            ("dmd_FP_mirror_vertical", 'V'),
        ])

        _outputLookup = {
            'dmd_FP_mirror_horizontal': "2A",
            'dmd_FP_mirror_vertical': "2B",
        }

        def __init__(self, name, config, globalDict, instrument):
            logger = logging.getLogger(__name__)
            ExternalParameterBase.__init__(self, name, config, globalDict)
            project = getProject()
            instrument_list = project.hardware.get('QITI SANA')
            instrument = instrument_list[instrument]
            ip_addr = instrument.get('ipAddress')
            port = instrument.get('port')

            # self.initializeChannelsToExternals()
            self.initOutput()
            self.client = PIDServerGRPCClient(ip_addr + ':' + port)
            self.qtHelper = qtHelper()
            self.newData = self.qtHelper.newData
        
        def setValue(self, channel, v):
            sana_channel = self._outputLookup[channel]
            parameter = v.m_as("V")
            parameter = float(parameter)
            self.client.set_channel_voltage(sana_channel, parameter)
            return v

        def getExternalValue(self, channel=None):
            sana_channel = self._outputLookup[channel]
            parameter = self.client.get_channel_voltage(sana_channel)
            return Q(parameter, 'V')

        def connectedInstruments(self):
            project = getProject()
            instrument_list = project.hardware.get('QITI SANA').keys()
            return instrument_list


ttl_switcher_enabled = project.isEnabled('hardware', 'QITI TTL Voltage Switcher')

if ttl_switcher_enabled:
    try:
        from QITI_TTL_voltage_switcher.py import TTLVoltageSwitcherClient
    except ImportError as err:
        print(err)
        importErrorPopup('QITI TTL Voltage Switcher')

    class TTLVoltageSwitcher(ExternalParameterBase):
        className = "TTLVoltageSwitcher"
        _outputChannels = OrderedDict([
            ("voltage_setpoint_high", 'V'),
            ("voltage_setpoint_low", 'V'),
        ])

        _outputLookup = {
            'voltage_setpoint_high': ["set_voltage_high","get_voltage_high"],
            'voltage_setpoint_low': ["set_voltage_low","get_voltage_low"],
        }

        def __init__(self, name, config, globalDict, instrument):
            logger = logging.getLogger(__name__)
            ExternalParameterBase.__init__(self, name, config, globalDict)
            project = getProject()
            instrument_list = project.hardware.get('QITI TTL Voltage Switcher')
            instrument = instrument_list[instrument]
            ip_addr = instrument.get('ipAddress')
            port = instrument.get('port')

            # self.initializeChannelsToExternals()
            self.initOutput()
            self.client = TTLVoltageSwitcherClient(ip_addr + ':' + port)
            self.qtHelper = qtHelper()
            self.newData = self.qtHelper.newData
        
        def setValue(self, channel, v):
            func_name = self._outputLookup[channel][0]
            parameter = v.m_as("V")
            parameter = float(parameter)
            v_return = getattr(self.client,func_name)(parameter)
            return v_return

        def getExternalValue(self, channel=None):
            func_name = self._outputLookup[channel][1]
            parameter = getattr(self.client,func_name)()
            return Q(parameter, 'V')

        @staticmethod
        def connectedInstruments(self):
            project = getProject()
            instrument_list = project.hardware.get('QITI TTL Voltage Switcher').keys()
            return instrument_list



toptica935Enabled = project.isEnabled('hardware', 'QITI Toptica 935nm')

if toptica935Enabled:
    try:
        from toptica.lasersdk.client import Client as TopticaClient, NetworkConnection as TopticaNetworkConnection

    except ImportError as err:
        print(err)
        importErrorPopup('935nm Toptica SDK')


    class toptica935Control(ExternalParameterBase):
        className = "QITI Toptica 935nm"
        _outputChannels = OrderedDict([
            ("laser_current", 'mA'),
            ("piezo_voltage", 'V'),
        ])

        _outputLookup = {
            'laser_current': "laser1:dl:cc:current-set",
            'piezo_voltage': "laser1:dl:pc:voltage-set",
        }

        def __init__(self, name, config, globalDict, instrument):
            logger = logging.getLogger(__name__)
            ExternalParameterBase.__init__(self, name, config, globalDict)
            project = getProject()
            instrument_list = project.hardware.get('QITI Toptica 935nm')
            instrument = instrument_list[instrument]
            ip_addr = instrument.get('ipAddress')

            # self.initializeChannelsToExternals()
            self.initOutput()
            self.client = TopticaClient(TopticaNetworkConnection(ip_addr))
            self.client.open()
            self.qtHelper = qtHelper()
            self.newData = self.qtHelper.newData

        def setValue(self, channel, v):
            toptica_param = self._outputLookup[channel]
            unit = self._outputChannels[channel]
            parameter = v.m_as(unit)
            parameter = float(parameter)
            self.client.set(toptica_param, parameter)
            return v

        def getExternalValue(self, channel=None):
            toptica_param = self._outputLookup[channel]
            parameter = self.client.get(toptica_param)
            unit = self._outputChannels[channel]
            return Q(parameter, unit)

        def connectedInstruments(self):
            project = getProject()
            instrument_list = project.hardware.get("QITI Toptica 935nm").keys()
            return instrument_list


awg_5014c = project.isEnabled("hardware", "QITI Tektonics 5014C")

if awg_5014c:
    try:
        from tex_awg import TekAwg, Waveform
    except Exception as err:
        print(err)

    class AWG5014C(ExternalParameterBase):
        className = "QITI Tektonics 5014C"
        waveformNAME = "SANDIA"
        _outputChannels = OrderedDict([
            ("waveform_idx", ''),
            #("loops", '')
            #("use_external_trigger", ''),
            #("sample_rate", '')
        ])

        def __init__(self, name, config, globalDict, instrument):
            print("Initialializing AWG......")
            logger = logging.getLogger(__name__)
            ExternalParameterBase.__init__(self, name, config, globalDict)
            project = getProject()
            instrument_list = project.hardware.get("QITI Tektonics 5014C")
            instrument = instrument_list[instrument]
            ip = instrument.get('ipAddress')

            if ip is None:
                raise ValueError("No ip address.")

            self.data_dir = instrument.get('data_dir')
            #self.database = h5py.File(self.data_dir + "awg.hdf5", 'a')
            self.awg = TekAwg.connect_to_ip(ip, backend="@py")

            self.awg.write("*RST")

            
            self.awg.write("AWGCONTROL:RMODE TRIG")
            self.awg.set_trig_source("EXT")

            # use external reference
            self.awg.write("SOUR1:ROSC:SOUR EXT")
            self.awg.write("SOUR1:ROSC:FREQ 10MHz")

            # configure Vpp
            self.awg.write("SOURCE1:VOLTAGE:AMPLITUDE 1.0")
            
            # empty waveform 
            self.awg.set_chan_state("OFF", "1")
            self.awg.del_waveform(self.waveformNAME)
            self.awg.new_waveform(self.waveformNAME, Waveform.from_binary(np.array([0.0, 0.0])))
            self.awg.write("SOUR1:WAV \"{}\"".format(self.waveformNAME))

            self.awg.set_chan_state("ON", "1")
            self.awg.run()

            self.initOutput()

            self.qtHelper = qtHelper()
            self.newData = self.qtHelper.newData
            self.i = -1.0
            print("Initialized!")

        def setValue(self, channel, v):
            self.awg.stop()
            if channel == "waveform_idx":
                parameter = v.m_as("")

                parameter = int(parameter)

                if parameter >= 0:
                    self.awg.set_chan_state("OFF", "1")
                    self.awg.del_waveform(self.waveformNAME)
                    print("loading waveform...")
                    waveform = np.load(self.data_dir + "awg_{}.npy".format(parameter))
                    if waveform.dtype == np.int16:
                        waveform = waveform.astype(np.float) / (2 ** 15 - 1)
                    #self.awg.write("*CLS")
                    self.awg.new_waveform(self.waveformNAME, Waveform.from_binary(waveform))
                    self.awg.write("SOUR1:WAV \"{}\"".format(self.waveformNAME))
                    #print(self.awg.query("SYSTEM:ERROR:NEXT?"))
                    print("loaded")
                    #print(waveform)
                    n = waveform.shape[0]
                    print(n)
                    self.awg.set_chan_state("ON", "1")
                    self.awg.run()
                    print("started")

                self.i = float(parameter)

            elif channel == "use_external_trigger":
                parameter = v.m_as("")
                use_external_trigger =  bool(parameter)
                if use_external_trigger:
                    self.awg.set_run_mode("TRIG")
                else:
                    self.awg.set_run_mode("CONT")
                self.awg.run()

            elif channel == "sample_rate":
                parameter = v.m_as("")
                print(parameter)
                sp = int(parameter)
                self.awg.set_freq(sp)
                self.awg.run()

            # Block until the AWG is in the run state
            while True:
                if self.awg.query("AWGControl:RSTate?") == "1":
                    break
                time.sleep(1)
                print("wating for AWG run state")
            return v
        
        def getExternalValue(self, channel=None):
            if channel == "waveform_idx":
                return Q(self.i, '')
            elif channel == "use_external_trigger":
                return Q(float(self.awg.get_run_mode() == "TRIG"), '')
            elif channel == "sample_rate":
                return Q(float(self.awg.get_freq()))

    

awg_singleReplayMode = project.isEnabled('hardware', 'QITI AWG Single Replay Mode')

if awg_singleReplayMode:
    try:
        from spcm.spcm import DrvHandle, GatedReplayMode, SingleReplayMode, SingleReplayRestartMode
        from spcm.spcm import SPC_CM, SPC_TM, SPC_TMASK, SPCM_XMODE
        import numpy as np
        import h5py

    except Exception as err:
        print(err)
        importErrorPopup('QITI AWG Single Replay Mode')

    class AWGSingleReplayMode(ExternalParameterBase):
        className = "QITI AWG Single Replay Mode"
        _outputChannels = OrderedDict([
            ("waveform_idx", ''),
            #("loops", '')
            ("use_external_trigger", ''),
            ("sample_rate", '')
        ])

        def __init__(self, name, config, globalDict, instrument):
            print("Initialializing AWG......")
            logger = logging.getLogger(__name__)
            ExternalParameterBase.__init__(self, name, config, globalDict)
            project = getProject()
            instrument_list = project.hardware.get('QITI AWG Single Replay Mode')
            instrument = instrument_list[instrument]
            driver_path = instrument.get('driver_path')

            self.data_dir = instrument.get('data_dir')
            #self.database = h5py.File(self.data_dir + "awg.hdf5", 'a')


            self.d = SingleReplayRestartMode(driver_path)

            #self.d.sample_rate = int(600_000_000)
            print(self.d.sample_rate)

            self.d.loops = 0
            self.d.reference_clock = int(10e6) # 10MHz reference clock
            self.d.clock_mode = SPC_CM.SPC_CM_EXTREFCLOCK

            self.d.enable_output(0)  # enable channel 0 output

            self.d.trig_ext0_mode = SPC_TM.SPC_TM_POS # use positive edge trigger

            self.d.trig_or_mask = SPC_TMASK.SPC_TMASK_EXT0  # use external trigger 0

            # Multi-purpose digitial IO 0 output the run state
            self.d.x0_mode = SPCM_XMODE.SPCM_XMODE_RUNSTATE

            # self.initializeChannelsToExternals()
            self.initOutput()

            self.qtHelper = qtHelper()
            self.newData = self.qtHelper.newData
            self.i = -1.0
            print("Initialized!")


        def setValue(self, channel, v):
            self.d.stop()  # stop the card activity
            if channel == "waveform_idx":
                parameter = v.m_as("")

                parameter = int(parameter)

                if parameter >= 0:
                    print("loading waveform...")
                    #waveform = self.database['{}'.format(parameter)][:]

                    waveform = np.load(self.data_dir + "awg_{}.npy".format(parameter))
                    print("loaded")
                    #print(waveform)
                    n = waveform.shape[0]
                    print(n)
                    self.d.mem_size = n
                    self.d.transfer_data(waveform)
                    self.d.start()
                    print("started")

                self.i = float(parameter)
            elif channel == "loops":
                parameter = v.m_as("")
                self.d.loops = int(parameter)
                self.d.start()

            elif channel == "use_external_trigger":
                parameter = v.m_as("")
                use_external_trigger =  bool(parameter)
                if use_external_trigger:
                    self.d.trig_or_mask = SPC_TMASK.SPC_TMASK_EXT0  # use external trigger 0
                else:
                    self.d.trig_or_mask = SPC_TMASK.SPC_TMASK_SOFTWARE
                self.d.start()

            elif channel == "sample_rate":
                parameter = v.m_as("")
                print(parameter)
                sp = int(parameter)

                self.d.sample_rate = sp
                self.d.start()
            return v

        def getExternalValue(self, channel=None):
            if channel == "waveform_idx":
                return Q(self.i, '')
            elif channel == "use_external_trigger":
                return Q(float(self.d.trig_or_mask == SPC_TMASK.SPC_TMASK_EXT0), '')
            elif channel == "sample_rate":
                return Q(float(self.d.sample_rate))

        def connectedInstruments(self):
            project = getProject()
            instrument_list = project.hardware.get('QITI AWG Single Replay Mode').keys()
            return instrument_list

        

awg_singleReplayModeIQ = project.isEnabled('hardware', 'QITI AWG Single Replay Mode IQ')

if awg_singleReplayModeIQ:
    try:
        from spcm.spcm import DrvHandle, GatedReplayMode, SingleReplayMode, SingleReplayRestartMode
        from spcm.spcm import SPC_CM, SPC_TM, SPC_TMASK, SPCM_XMODE
        from spcm import GuardianMiddleware
        import numpy as np
        import h5py
        import gc

    except Exception as err:
        print(err)
        importErrorPopup('QITI AWG Single Replay Mode IQ')

    class AWGSingleReplayMode(ExternalParameterBase):
        className = "QITI AWG Single Replay Mode IQ"
        _outputChannels = OrderedDict([
            ("waveform_idx", ''),
            #("loops", '')
            ("use_external_trigger", ''),
            ("sample_rate", '')
        ])

        def __init__(self, name, config, globalDict, instrument):
            print("Initialializing AWG......")
            logger = logging.getLogger(__name__)
            ExternalParameterBase.__init__(self, name, config, globalDict)
            project = getProject()
            instrument_list = project.hardware.get('QITI AWG Single Replay Mode IQ')
            instrument = instrument_list[instrument]
            driver_path = instrument.get('driver_path')

            self.data_dir = instrument.get('data_dir')
            #self.database = h5py.File(self.data_dir + "awg.hdf5", 'a')


            self.d = SingleReplayRestartMode(driver_path, channels=(0,1,2,3), middleware = GuardianMiddleware(min_voltage=0, termination=GuardianMiddleware.Termination.IMPEDANCE_HIGH))

            #self.d.sample_rate = int(600_000_000)
            print(self.d.sample_rate)

            self.d.loops = 0
            self.d.reference_clock = int(10e6) # 10MHz reference clock
            self.d.clock_mode = SPC_CM.SPC_CM_EXTREFCLOCK

            self.d.enable_output(0)  # enable channel 0 output
            self.d.enable_output(1)
            self.d.enable_output(2)
            self.d.enable_output(3)

            self.d.trig_ext0_mode = SPC_TM.SPC_TM_POS # use positive edge trigger

            self.d.trig_or_mask = SPC_TMASK.SPC_TMASK_EXT0  # use external trigger 0

            # Multi-purpose digitial IO 0 output the run state
            self.d.x0_mode = SPCM_XMODE.SPCM_XMODE_RUNSTATE

            # self.initializeChannelsToExternals()
            self.initOutput()

            self.qtHelper = qtHelper()
            self.newData = self.qtHelper.newData
            self.i = -1.0
            print("Initialized!")


        def setValue(self, channel, v):
            self.d.stop()  # stop the card activity
            if channel == "waveform_idx":
                parameter = v.m_as("")

                parameter = int(parameter)

                if parameter >= 0:
                    print("loading waveform...")
                    #waveform = self.database['{}'.format(parameter)][:]

                    waveform0 = np.load(self.data_dir + "awg_0_{}.npy".format(parameter))
                    waveform1 = np.load(self.data_dir + "awg_1_{}.npy".format(parameter))
                    waveform2 = np.load(self.data_dir + "awg_2_{}.npy".format(parameter))
                    waveform3 = np.load(self.data_dir + "awg_3_{}.npy".format(parameter))
                    print("loaded")

                    self.d.transfer_data((
                        waveform0, waveform1, waveform2, waveform3
                    ))
                    self.d.start()
                    del waveform0
                    del waveform1
                    del waveform2
                    del waveform3

                    gc.collect()
                    print("started")

                self.i = float(parameter)
            elif channel == "loops":
                parameter = v.m_as("")
                self.d.loops = int(parameter)
                self.d.start()

            elif channel == "use_external_trigger":
                parameter = v.m_as("")
                use_external_trigger =  bool(parameter)
                if use_external_trigger:
                    self.d.trig_or_mask = SPC_TMASK.SPC_TMASK_EXT0  # use external trigger 0
                else:
                    self.d.trig_or_mask = SPC_TMASK.SPC_TMASK_SOFTWARE
                self.d.start()

            elif channel == "sample_rate":
                parameter = v.m_as("")
                print(parameter)
                sp = int(parameter)

                self.d.sample_rate = sp
                self.d.start()
            return v

        def getExternalValue(self, channel=None):
            if channel == "waveform_idx":
                return Q(self.i, '')
            elif channel == "use_external_trigger":
                return Q(float(self.d.trig_or_mask == SPC_TMASK.SPC_TMASK_EXT0), '')
            elif channel == "sample_rate":
                return Q(float(self.d.sample_rate))

        def connectedInstruments(self):
            project = getProject()
            instrument_list = project.hardware.get('QITI AWG Single Replay Mode').keys()
            return instrument_list