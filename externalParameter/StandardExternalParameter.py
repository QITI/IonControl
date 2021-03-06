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
            ("frequency_cooling_eom", 'MHz'),
            ("frequency_detection_aom", 'MHz'),
            ("frequency_repump_eom", 'MHz'),
            ("frequency_cooling_aom", 'MHz'),
            ("frequency_optpump_eom", 'MHz'),
            ("frequency_microwave_modulation", 'MHz'),
            ("frequency_dmd_aom", 'MHz'),
            ("power_cooling_eom", ''),
            ("power_detection_aom", ''),
            ("power_repump_eom", ''),
            ("power_cooling_aom", ''),
            ("power_optpump_eom", ''),
            ("power_microwave_modulation", ''),
            ("power_dmd_aom", ''),
            ("output_state_cooling_eom",''),
            ("output_state_microwave_modulation", '')
        ])

        _outputLookup = {
            'frequency_cooling_eom': ("four_rod_cooling_eom", "frequency"),
            'frequency_detection_aom': ("four_rod_detection_aom", "frequency"),
            'frequency_repump_eom': ("four_rod_repump_eom", "frequency"),
            'frequency_cooling_aom': ("four_rod_cooling_aom", "frequency"),
            'frequency_optpump_eom': ("four_rod_optpump_eom", "frequency"),
            'frequency_microwave_modulation': ("four_rod_microwave_modulation", "frequency"),
            'frequency_dmd_aom': ("four_rod_dmd_aom", "frequency"),
            'power_cooling_eom': ("four_rod_cooling_eom", "power"),
            'power_detection_aom': ("four_rod_detection_aom", "power"),
            'power_repump_eom': ("four_rod_repump_eom", "power"),
            'power_cooling_aom': ("four_rod_cooling_aom", "power"),
            'power_optpump_eom': ("four_rod_optpump_eom", "power"),
            'power_microwave_modulation': ("four_rod_microwave_modulation", "power"),
            'power_dmd_aom': ("four_rod_dmd_aom", "power"),
            'output_state_cooling_eom': ("four_rod_cooling_eom", "output_state"),
            'output_state_microwave_modulation': ("four_rod_microwave_modulation", "output_state")
        }

        # TODO: pint doesn't support pint. Modify pint?
        _unitLookup = {
            "frequency": "Hz",
            "power": "",
            "output_state":""
        }

        _setTypeLookup = {
            "frequency": int,
            "power": float,
            "output_state":bool
        }
        _getTypeLookup = {
            "frequency": int,
            "power": float,
            "output_state":int
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
            parameter = self._setTypeLookup[parameter_name](parameter)
            getattr(self.client, "set_" + parameter_name)(rf_channel, parameter)
            return v

        def getExternalValue(self, channel=None):
            rf_channel, parameter_name = self._outputLookup[channel]
            parameter = getattr(self.client, "get_" + parameter_name)(rf_channel)
            parameter = self._getTypeLookup[parameter_name](parameter)
            return Q(parameter, self._unitLookup[parameter_name])

        def connectedInstruments(self):
            project = getProject()
            instrument_list = project.hardware.get('QITI RF Controller').keys()
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
        
