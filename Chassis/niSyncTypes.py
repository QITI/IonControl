# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from ctypes import *


#These types are found in visatypes.h in
#Windows 7: C:\Program Files (x86)\IVI Foundation\VISA\WinNT\include
#Types
ViRsrc = c_char_p
ViBoolean = c_ushort
ViBoolean_P = c_void_p
ViSession = c_void_p     #A pointer to a uint32 pointer
ViStatus = c_int
ViReal64 = c_double
ViReal64_P = c_void_p
ViConstString = c_char_p
ViInt32 = c_int
ViInt32_P = c_void_p
ViUInt32 = c_uint
ViUInt32_P = c_void_p
ViInt16 = c_short
ViInt16_P = c_void_p
ViUInt16 = c_ushort
ViUInt16_P = c_void_p
ViString = c_char_p
ViAttr = c_uint

#Defined Values
NISYNC_VAL_1588_CLK_STATE_DISABLE = 2
NISYNC_VAL_1588_CLK_STATE_FAULT = 1
NISYNC_VAL_1588_CLK_STATE_INIT = 0
NISYNC_VAL_1588_CLK_STATE_LISTENING = 3
NISYNC_VAL_1588_CLK_STATE_MASTER = 5
NISYNC_VAL_1588_CLK_STATE_NOT_DEFINED = -1
NISYNC_VAL_1588_CLK_STATE_PASSIVE = 6
NISYNC_VAL_1588_CLK_STATE_PREMASTER = 4
NISYNC_VAL_1588_CLK_STATE_SLAVE = 8
NISYNC_VAL_1588_CLK_STATE_UNCALIBRATED = 7
NISYNC_VAL_ALL_CONNECTED = b"AllConnected"
NISYNC_VAL_BOARD_CLK = b"BoardClk"
NISYNC_VAL_CLK10 = b"PXI_Clk10"
NISYNC_VAL_CLK10_IN = b"PXI_Clk10_In"
NISYNC_VAL_CLK100 = b"PXIe_Clk100"
NISYNC_VAL_CLKIN = b"ClkIn"
NISYNC_VAL_CLKOUT = b"ClkOut"
NISYNC_VAL_DDS = b"DDS"
NISYNC_VAL_DDS_UPDATE_IMMEDIATE = b"DDS_UpdateImmediate"
NISYNC_VAL_DONT_INVERT = 0
NISYNC_VAL_EDGE_ANY = 2
NISYNC_VAL_EDGE_FALLING = 1
NISYNC_VAL_EDGE_RISING = 0
NISYNC_VAL_EXT_CAL_ABORT = 0
NISYNC_VAL_EXT_CAL_COMMIT = 1
NISYNC_VAL_GND = "Ground"
NISYNC_VAL_GPS_ANTENNA_ERROR = 1
NISYNC_VAL_GPS_FIX_REJECTED = 9
NISYNC_VAL_GPS_NO_GPS_TIME = 6
NISYNC_VAL_GPS_NO_USEABLE_SATELLITE = 2
NISYNC_VAL_GPS_ONE_USEABLE_SATELLITE = 3
NISYNC_VAL_GPS_PDOP_TOO_HIGH = 7
NISYNC_VAL_GPS_SELF_SURVEY_COMPLETE = 10
NISYNC_VAL_GPS_SELF_SURVEY_NOT_COMPLETE = 11
NISYNC_VAL_GPS_THREE_USEABLE_SATELLITES = 5
NISYNC_VAL_GPS_TWO_USEABLE_SATELLITES = 4
NISYNC_VAL_GPS_UNINITIALIZED = 0
NISYNC_VAL_GPS_UNUSEABLE_SATELLITE = 8
NISYNC_VAL_INIT_TIME_SRC_MANUAL = 1
NISYNC_VAL_INIT_TIME_SRC_SYSTEM_CLK = 0
NISYNC_VAL_INVERT = 1
NISYNC_VAL_IRIG_TYPE_IRIGB_AM = 1
NISYNC_VAL_IRIG_TYPE_IRIGB_DC = 0
NISYNC_VAL_LEVEL_HIGH = 1
NISYNC_VAL_LEVEL_LOW = 0
NISYNC_VAL_OSCILLATOR = b"Oscillator"
NISYNC_VAL_PFILVDS0 = b"PFI_LVDS0"
NISYNC_VAL_PFILVDS1 = b"PFI_LVDS1"
NISYNC_VAL_PFILVDS2 = b"PFI_LVDS2"
NISYNC_VAL_PFI0 = b"PFI0"
NISYNC_VAL_PFI1 = b"PFI1"
NISYNC_VAL_PFI2 = b"PFI2"
NISYNC_VAL_PFI3 = b"PFI3"
NISYNC_VAL_PFI4 = b"PFI4"
NISYNC_VAL_PFI5 = b"PFI5"
NISYNC_VAL_PXIEDSTARA = b"PXIe_DStarA"
NISYNC_VAL_PXIEDSTARA0 = b"PXIe_DStarA0"
NISYNC_VAL_PXIEDSTARA1 = b"PXIe_DStarA1"
NISYNC_VAL_PXIEDSTARA2 = b"PXIe_DStarA2"
NISYNC_VAL_PXIEDSTARA3 = b"PXIe_DStarA3"
NISYNC_VAL_PXIEDSTARA4 = b"PXIe_DStarA4"
NISYNC_VAL_PXIEDSTARA5 = b"PXIe_DStarA5"
NISYNC_VAL_PXIEDSTARA6 = b"PXIe_DStarA6"
NISYNC_VAL_PXIEDSTARA7 = b"PXIe_DStarA7"
NISYNC_VAL_PXIEDSTARA8 = b"PXIe_DStarA8"
NISYNC_VAL_PXIEDSTARA9 = b"PXIe_DStarA9"
NISYNC_VAL_PXIEDSTARA10 = b"PXIe_DStarA10"
NISYNC_VAL_PXIEDSTARA11 = b"PXIe_DStarA11"
NISYNC_VAL_PXIEDSTARA12 = b"PXIe_DStarA12"
NISYNC_VAL_PXIEDSTARA13 = b"PXIe_DStarA13"
NISYNC_VAL_PXIEDSTARA14 = b"PXIe_DStarA14"
NISYNC_VAL_PXIEDSTARA15 = b"PXIe_DStarA15"
NISYNC_VAL_PXIEDSTARA16 = b"PXIe_DStarA16"
NISYNC_VAL_PXIEDSTARB = b"PXIe_DStarB"
NISYNC_VAL_PXIEDSTARB0 = b"PXIe_DStarB0"
NISYNC_VAL_PXIEDSTARB1 = b"PXIe_DStarB1"
NISYNC_VAL_PXIEDSTARB2 = b"PXIe_DStarB2"
NISYNC_VAL_PXIEDSTARB3 = b"PXIe_DStarB3"
NISYNC_VAL_PXIEDSTARB4 = b"PXIe_DStarB4"
NISYNC_VAL_PXIEDSTARB5 = b"PXIe_DStarB5"
NISYNC_VAL_PXIEDSTARB6 = b"PXIe_DStarB6"
NISYNC_VAL_PXIEDSTARB7 = b"PXIe_DStarB7"
NISYNC_VAL_PXIEDSTARB8 = b"PXIe_DStarB8"
NISYNC_VAL_PXIEDSTARB9 = b"PXIe_DStarB9"
NISYNC_VAL_PXIEDSTARB10 = b"PXIe_DStarB10"
NISYNC_VAL_PXIEDSTARB11 = b"PXIe_DStarB11"
NISYNC_VAL_PXIEDSTARB12 = b"PXIe_DStarB12"
NISYNC_VAL_PXIEDSTARB13 = b"PXIe_DStarB13"
NISYNC_VAL_PXIEDSTARB14 = b"PXIe_DStarB14"
NISYNC_VAL_PXIEDSTARB15 = b"PXIe_DStarB15"
NISYNC_VAL_PXIEDSTARB16 = b"PXIe_DStarB16"
NISYNC_VAL_PXIEDSTARC = b"PXIe_DStarC"
NISYNC_VAL_PXIEDSTARC0 = b"PXIe_DStarC0"
NISYNC_VAL_PXIEDSTARC1 = b"PXIe_DStarC1"
NISYNC_VAL_PXIEDSTARC2 = b"PXIe_DStarC2"
NISYNC_VAL_PXIEDSTARC3 = b"PXIe_DStarC3"
NISYNC_VAL_PXIEDSTARC4 = b"PXIe_DStarC4"
NISYNC_VAL_PXIEDSTARC5 = b"PXIe_DStarC5"
NISYNC_VAL_PXIEDSTARC6 = b"PXIe_DStarC6"
NISYNC_VAL_PXIEDSTARC7 = b"PXIe_DStarC7"
NISYNC_VAL_PXIEDSTARC8 = b"PXIe_DStarC8"
NISYNC_VAL_PXIEDSTARC9 = b"PXIe_DStarC9"
NISYNC_VAL_PXIEDSTARC10 = b"PXIe_DStarC10"
NISYNC_VAL_PXIEDSTARC11 = b"PXIe_DStarC11"
NISYNC_VAL_PXIEDSTARC12 = b"PXIe_DStarC12"
NISYNC_VAL_PXIEDSTARC13 = b"PXIe_DStarC13"
NISYNC_VAL_PXIEDSTARC14 = b"PXIe_DStarC14"
NISYNC_VAL_PXIEDSTARC15 = b"PXIe_DStarC15"
NISYNC_VAL_PXIEDSTARC16 = b"PXIe_DStarC16"
NISYNC_VAL_PXISTAR0 = b"PXI_Star0"
NISYNC_VAL_PXISTAR1 = b"PXI_Star1"
NISYNC_VAL_PXISTAR2 = b"PXI_Star2"
NISYNC_VAL_PXISTAR3 = b"PXI_Star3"
NISYNC_VAL_PXISTAR4 = b"PXI_Star4"
NISYNC_VAL_PXISTAR5 = b"PXI_Star5"
NISYNC_VAL_PXISTAR6 = b"PXI_Star6"
NISYNC_VAL_PXISTAR7 = b"PXI_Star7"
NISYNC_VAL_PXISTAR8 = b"PXI_Star8"
NISYNC_VAL_PXISTAR9 = b"PXI_Star9"
NISYNC_VAL_PXISTAR10 = b"PXI_Star10"
NISYNC_VAL_PXISTAR11 = b"PXI_Star11"
NISYNC_VAL_PXISTAR12 = b"PXI_Star12"
NISYNC_VAL_PXISTAR13 = b"PXI_Star13"
NISYNC_VAL_PXISTAR14 = b"PXI_Star14"
NISYNC_VAL_PXISTAR15 = b"PXI_Star15"
NISYNC_VAL_PXISTAR16 = b"PXI_Star16"
NISYNC_VAL_PXITRIG0 = b"PXI_Trig0"
NISYNC_VAL_PXITRIG1 = b"PXI_Trig1"
NISYNC_VAL_PXITRIG2 = b"PXI_Trig2"
NISYNC_VAL_PXITRIG3 = b"PXI_Trig3"
NISYNC_VAL_PXITRIG4 = b"PXI_Trig4"
NISYNC_VAL_PXITRIG5 = b"PXI_Trig5"
NISYNC_VAL_PXITRIG6 = b"PXI_Trig6"
NISYNC_VAL_PXITRIG7 = b"PXI_Trig7"
NISYNC_VAL_RTSI0 = b"RTSI0"
NISYNC_VAL_RTSI1 = b"RTSI1"
NISYNC_VAL_RTSI2 = b"RTSI2"
NISYNC_VAL_RTSI3 = b"RTSI3"
NISYNC_VAL_RTSI4 = b"RTSI4"
NISYNC_VAL_RTSI5 = b"RTSI5"
NISYNC_VAL_RTSI6 = b"RTSI6"
NISYNC_VAL_RTSI7 = b"RTSI7"
NISYNC_VAL_SWTRIG_GLOBAL = b"GlobalSoftwareTrigger"
NISYNC_VAL_SYNC_CLK_ASYNC = b"SyncClkAsync"
NISYNC_VAL_SYNC_CLK_DIV1 = b"SyncClkDivided1"
NISYNC_VAL_SYNC_CLK_DIV2 = b"SyncClkDivided2"
NISYNC_VAL_SYNC_CLK_FULLSPEED = b"SyncClkFullSpeed"
NISYNC_VAL_SYNC_INTERVAL_HALF_SEC = -1
NISYNC_VAL_SYNC_INTERVAL_ONE_SEC = 0
NISYNC_VAL_SYNC_INTERVAL_TWO_SEC = 1
NISYNC_VAL_TIMEREF_1588_ORDINARY_CLOCK = 3
NISYNC_VAL_TIMEREF_FREERUNNING = 4
NISYNC_VAL_TIMEREF_GPS = 0
NISYNC_VAL_TIMEREF_IRIG = 1
NISYNC_VAL_TIMEREF_PPS = 2
NISYNC_VAL_UPDATE_EDGE_FALLING = 1
NISYNC_VAL_UPDATE_EDGE_RISING = 0

#Attribute IDs

NISYNC_ATTR_BASE = 1150000

#Interface Attributes
NISYNC_ATTR_INTF_NUM = NISYNC_ATTR_BASE + 0
NISYNC_ATTR_SERIAL_NUM = NISYNC_ATTR_BASE + 1

#Calibration Attributes
NISYNC_ATTR_PFI0_THRESHOLD = NISYNC_ATTR_BASE + 100
NISYNC_ATTR_PFI1_THRESHOLD = NISYNC_ATTR_BASE + 101
NISYNC_ATTR_PFI2_THRESHOLD = NISYNC_ATTR_BASE + 102
NISYNC_ATTR_PFI3_THRESHOLD = NISYNC_ATTR_BASE + 103
NISYNC_ATTR_PFI4_THRESHOLD = NISYNC_ATTR_BASE + 104
NISYNC_ATTR_PFI5_THRESHOLD = NISYNC_ATTR_BASE + 105
NISYNC_ATTR_OSCILLATOR_VOLATAGE = NISYNC_ATTR_BASE + 106
NISYNC_ATTR_CLK10_PHASE_ADJUST = NISYNC_ATTR_BASE + 107
NISYNC_ATTR_DDS_VCXO_VOLTAGE = NISYNC_ATTR_BASE + 108
NISYNC_ATTR_DDS_PHASE_ADJUST = NISYNC_ATTR_BASE + 109
NISYNC_ATTR_PFI0_1KOHM_ENABLE = NISYNC_ATTR_BASE + 110
NISYNC_ATTR_PFI1_1KOHM_ENABLE = NISYNC_ATTR_BASE + 111
NISYNC_ATTR_PFI2_1KOHM_ENABLE = NISYNC_ATTR_BASE + 112
NISYNC_ATTR_PFI3_1KOHM_ENABLE = NISYNC_ATTR_BASE + 113
NISYNC_ATTR_PFI4_1KOHM_ENABLE = NISYNC_ATTR_BASE + 114
NISYNC_ATTR_PFI5_1KOHM_ENABLE = NISYNC_ATTR_BASE + 115
NISYNC_ATTR_PFI0_10KOHM_ENABLE = NISYNC_ATTR_BASE + 116
NISYNC_ATTR_PFI1_10KOHM_ENABLE = NISYNC_ATTR_BASE + 117
NISYNC_ATTR_PFI2_10KOHM_ENABLE = NISYNC_ATTR_BASE + 118
NISYNC_ATTR_PFI3_10KOHM_ENABLE = NISYNC_ATTR_BASE + 119
NISYNC_ATTR_PFI4_10KOHM_ENABLE = NISYNC_ATTR_BASE + 120
NISYNC_ATTR_PFI5_10KOHM_ENABLE = NISYNC_ATTR_BASE + 121

#Synchronization Clock Attributes
NISYNC_ATTR_FRONT_SYNC_CLK_SRC = NISYNC_ATTR_BASE + 200
NISYNC_ATTR_REAR_SYNC_CLK_SRC = NISYNC_ATTR_BASE + 201
NISYNC_ATTR_SYNC_CLK_DIV1 = NISYNC_ATTR_BASE + 202
NISYNC_ATTR_SYNC_CLK_DIV2 = NISYNC_ATTR_BASE + 203
NISYNC_ATTR_SYNC_CLK_RST_PXITRIG_NUM = NISYNC_ATTR_BASE + 204
NISYNC_ATTR_SYNC_CLK_PFI0_FREQ = NISYNC_ATTR_BASE + 205
NISYNC_ATTR_SYNC_CLK_RST_DDS_CNTR_ON_PXITRIG = NISYNC_ATTR_BASE + 206
NISYNC_ATTR_SYNC_CLK_RST_PFI0_CNTR_ON_PXITRIG = NISYNC_ATTR_BASE + 207
NISYNC_ATTR_SYNC_CLK_RST_CLK10_CNTR_ON_PXITRIG = NISYNC_ATTR_BASE + 208

#Trigger State Attributes
NISYNC_ATTR_TERMINAL_STATE_PXISTAR = NISYNC_ATTR_BASE + 300
NISYNC_ATTR_TERMINAL_STATE_PXITRIG = NISYNC_ATTR_BASE + 301
NISYNC_ATTR_TERMINAL_STATE_PFI = NISYNC_ATTR_BASE + 302
NISYNC_ATTR_TERMINAL_STATE_PXIEDSTARC = NISYNC_ATTR_BASE + 303
NISYNC_ATTR_TERMINAL_STATE_PFILVDS = NISYNC_ATTR_BASE + 304
NISYNC_ATTR_TERMINAL_STATE_PXIEDSTARCPERIPHERAL = NISYNC_ATTR_BASE + 305
NISYNC_ATTR_TERMINAL_STATE_PXIEDSTARBPERIPHERAL = NISYNC_ATTR_BASE + 306
NISYNC_ATTR_TERMINAL_STATE_PXISTARPERIPHERAL = NISYNC_ATTR_BASE + 307

#DDS Attributes
NISYNC_ATTR_DDS_FREQ = NISYNC_ATTR_BASE + 400
NISYNC_ATTR_DDS_UPDATE_SOURCE = NISYNC_ATTR_BASE + 401
NISYNC_ATTR_DDS_INITIAL_DELAY = NISYNC_ATTR_BASE + 402

#Clk Attributes
NISYNC_ATTR_CLKIN_PLL_FREQ = NISYNC_ATTR_BASE + 500
NISYNC_ATTR_CLKIN_USE_PLL = NISYNC_ATTR_BASE + 501
NISYNC_ATTR_CLKIN_PLL_LOCKED = NISYNC_ATTR_BASE + 502
NISYNC_ATTR_CLKOUT_GAIN_ENABLE = NISYNC_ATTR_BASE + 503
NISYNC_ATTR_PXICLK10_PRESENT = NISYNC_ATTR_BASE + 504
NISYNC_ATTR_CLKIN_ATTENUATION_DISABLE = NISYNC_ATTR_BASE + 505

#User LED Attributes
NISYNC_ATTR_USER_LED_STATE = NISYNC_ATTR_BASE + 600

#1588 Attributes
NISYNC_ATTR_1588_IP_ADDRESS = NISYNC_ATTR_BASE + 700
#ViString
NISYNC_ATTR_1588_CLOCK_STATE = NISYNC_ATTR_BASE + 712
#ViInt32
NISYNC_ATTR_1588_CLOCK_ID = NISYNC_ATTR_BASE + 729
#ViString
NISYNC_ATTR_1588_CLOCK_CLASS = NISYNC_ATTR_BASE + 730
#ViInt32
NISYNC_ATTR_1588_CLOCK_ACCURACY = NISYNC_ATTR_BASE + 731
#ViInt32
NISYNC_ATTR_1588_PRIORITY1 = NISYNC_ATTR_BASE + 732
#ViInt32
NISYNC_ATTR_1588_PRIORITY2 = NISYNC_ATTR_BASE + 733
#ViInt32
NISYNC_ATTR_1588_GRANDMASTER_CLOCK_ID = NISYNC_ATTR_BASE + 734
#ViString
NISYNC_ATTR_1588_GRANDMASTER_CLOCK_CLASS = NISYNC_ATTR_BASE + 735
#ViInt32
NISYNC_ATTR_1588_GRANDMASTER_CLOCK_ACCURACY = NISYNC_ATTR_BASE + 736
#ViInt32
NISYNC_ATTR_1588_GRANDMASTER_PRIORITY1 = NISYNC_ATTR_BASE + 737
#ViInt32
NISYNC_ATTR_1588_GRANDMASTER_PRIORITY2 = NISYNC_ATTR_BASE + 738
#ViInt32
NISYNC_ATTR_1588_STEPS_TO_GRANDMASTER = NISYNC_ATTR_BASE + 716
#ViInt32
NISYNC_ATTR_1588_LOG_SYNC_INTERVAL = NISYNC_ATTR_BASE + 739
#ViInt32
NISYNC_ATTR_1588_MEAN_PATH_DELAY = NISYNC_ATTR_BASE + 740
#ViReal64
NISYNC_ATTR_1588_TIMESTAMP_BUF_SIZE = NISYNC_ATTR_BASE + 718
#ViInt32
NISYNC_ATTR_1588_AVAIL_TIMESTAMPS = NISYNC_ATTR_BASE + 719
#ViInt32
NISYNC_ATTR_1588_CLK_RESOLUTION = NISYNC_ATTR_BASE + 720

#Time Reference Attributes
NISYNC_ATTR_TIMEREF_PRESENT = NISYNC_ATTR_BASE + 800
#ViBoolean
NISYNC_ATTR_TIMEREF_CURRENT = NISYNC_ATTR_BASE + 801
#ViInt32
NISYNC_ATTR_TIMEREF_OFFSET = NISYNC_ATTR_BASE + 802
#ViReal64
NISYNC_ATTR_TIMEREF_CORRECTION = NISYNC_ATTR_BASE + 804
#ViReal64
NISYNC_ATTR_TIMEREF_UTC_OFFSET = NISYNC_ATTR_BASE + 805
#ViInt32
NISYNC_ATTR_TIMEREF_UTC_OFFSET_VALID = NISYNC_ATTR_BASE + 806
#ViBoolean
NISYNC_ATTR_TIMEREF_LAST_SYNC_ID = NISYNC_ATTR_BASE + 807

#GPS Attributes
NISYNC_ATTR_GPS_ANTENNA_CONNECTED = NISYNC_ATTR_BASE + 900
#ViBoolean
NISYNC_ATTR_GPS_RECALCULATE_POSITION = NISYNC_ATTR_BASE + 901
#ViBoolean
NISYNC_ATTR_GPS_SATELLITES_AVAILABLE = NISYNC_ATTR_BASE + 902
#ViInt32
NISYNC_ATTR_GPS_SELF_SURVEY = NISYNC_ATTR_BASE + 903
#ViInt32
NISYNC_ATTR_GPS_MOBILE_MODE = NISYNC_ATTR_BASE + 904
#ViBoolean
NISYNC_ATTR_GPS_STATUS = NISYNC_ATTR_BASE + 905

#Depreciated Attributes - Do not use
NISYNC_ATTR_TIMEREF_CLK_ADJ_OFFSET = NISYNC_ATTR_BASE + 803
NISYNC_ATTR_GPS_UTC_OFFSET = NISYNC_ATTR_BASE + 906
NISYNC_ATTR_IRIG_TAI_OFFSET = NISYNC_ATTR_BASE + 1000
