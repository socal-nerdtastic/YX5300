#!/usr/bin/env python3

# BIG THANK YOU TO https://github.com/MajicDesigns/MD_YX5300/blob/main/src/MD_YX5300.h

import serial

CMD_NUL = 0x00             # < No command
CMD_NEXT_SONG = 0x01       # < Play next song
CMD_PREV_SONG = 0x02       # < Play previous song
CMD_PLAY_WITH_INDEX = 0x03 # < Play song with index number
CMD_VOLUME_UP = 0x04       # < Volume increase by one
CMD_VOLUME_DOWN = 0x05     # < Volume decrease by one
CMD_SET_VOLUME = 0x06      # < Set the volume to level specified
CMD_SET_EQUALIZER = 0x07   # < Set the equalizer to specified level
CMD_SNG_CYCL_PLAY = 0x08   # < Loop play (repeat) specified track
CMD_SEL_DEV = 0x09         # < Select storage device to TF card
CMD_SLEEP_MODE = 0x0a      # < Chip enters sleep mode
CMD_WAKE_UP = 0x0b         # < Chip wakes up from sleep mode
CMD_RESET = 0x0c           # < Chip reset
CMD_PLAY = 0x0d            # < Playback restart
CMD_PAUSE = 0x0e           # < Playback is paused
CMD_PLAY_FOLDER_FILE = 0x0f# < Play the song with the specified folder and index number
CMD_STOP_PLAY = 0x16       # < Playback is stopped
CMD_FOLDER_CYCLE = 0x17    # < Loop playback from specified folder
CMD_SHUFFLE_PLAY = 0x18    # < Playback shuffle mode
CMD_SET_SNGL_CYCL = 0x19   # < Set loop play (repeat) on/off for current file
CMD_SET_DAC = 0x1a         # < DAC on/off control
CMD_PLAY_W_VOL = 0x22      # < Play track at the specified volume
CMD_SHUFFLE_FOLDER = 0x28  # < Playback shuffle mode for folder specified
CMD_QUERY_STATUS = 0x42    # < Query Device Status
CMD_QUERY_VOLUME = 0x43    # < Query Volume level
CMD_QUERY_EQUALIZER = 0x44 # < Query current equalizer (disabled in hardware)
CMD_QUERY_TOT_FILES = 0x48 # < Query total files in all folders
CMD_QUERY_PLAYING = 0x4c   # < Query which track playing
CMD_QUERY_FLDR_FILES = 0x4e# < Query total files in folder
CMD_QUERY_TOT_FLDR = 0x4f  # < Query number of folders

CMD_OPT_ON = 0x00;    # < On indicator
CMD_OPT_OFF = 0x01;   # < Off indicator
CMD_OPT_DEV_UDISK = 0X01; # < Device option UDisk (not used)
CMD_OPT_DEV_TF = 0X02;    # < Device option TF
CMD_OPT_DEV_FLASH = 0X04; # < Device option Flash (not used)

# Protocol Message Characters
PKT_SOM = 0x7e;       # < Start of message delimiter character
PKT_VER = 0xff;       # < Version information
PKT_LEN = 0x06;       # < Data packet length in bytes (excluding SOM, EOM)
PKT_FB_OFF = 0x00;    # < Command feedback OFF
PKT_FB_ON = 0x01;     # < Command feedback ON
PKT_DATA_NUL = 0x00;  # < Packet data place marker
PKT_EOM = 0xef;       # < End of message delimiter character

RESP = dict(
    STS_OK = 0x00,         # < No error (library generated status)
    STS_TIMEOUT = 0x01,    # < Timeout on response message (library generated status)
    STS_VERSION = 0x02,    # < Wrong version number in return message (library generated status)
    STS_CHECKSUM = 0x03,   # < Device checksum invalid (library generated status)
    STS_TF_INSERT = 0x3a,  # < TF Card was inserted (unsolicited)
    STS_TF_REMOVE = 0x3b,  # < TF card was removed (unsolicited)
    STS_FILE_END = 0x3d,   # < Track/file has ended (unsolicited)
    STS_INIT = 0x3f,       # < Initialization complete (unsolicited)
    STS_ERR_FILE = 0x40,   # < Error file not found
    STS_ACK_OK = 0x41,     # < Message acknowledged ok
    STS_STATUS = 0x42,     # < Current status
    STS_VOLUME = 0x43,     # < Current volume level
    STS_EQUALIZER = 0x44,  # < Equalizer status
    STS_TOT_FILES = 0x48,  # < TF Total file count
    STS_PLAYING = 0x4c,    # < Current file playing
    STS_FLDR_FILES = 0x4e, # < Total number of files in the folder
    STS_TOT_FLDR = 0x4f,   # < Total number of folders
)
responses = {v:k for k,v in RESP.items()}

'''
  * Status return structure specification.
  *
  * Used to return (through callback or getStatus() method) the
  * status value of the last device request.
  *
  * Device commands will always receive a STS_ACK_OK if the message was received
  * correctly. Some commands, notably query requests, will also be followed by an
  * unsolicited message containing the status or information data. These methods
  * are listed below:
  *
  * | Method             | Return Status (code) | Return Data (data)
  * |:-------------------|:---------------------|:--------------------
  * | Unsolicited mesg   | STS_FILE_END         | Index number of the file just completed.
  * | Unsolicited mesg   | STS_INIT             | Device initialization complete - file store types available (0x02 for TF).
  * | Unsolicited mesg   | STS_ERR_FILE         | File index
  * | queryStatus()      | STS_STATUS           | Current status. High byte is file store (0x02 for TF); low byte 0x00=stopped, 0x01=play, 0x02=paused.
  * | queryVolume()      | STS_VOLUME           | Current volume level [0..MAX_VOLUME].
  * | queryFilesCount()  | STS_TOT_FILES        | Total number of files on the TF card.
  * | queryFile()        | STS_PLAYING          | Index number of the current file playing.
  * | queryFolderFiles() | STS_FLDR_FILES       | Total number of files in the folder.
  * | queryFolderCount() | STS_TOT_FLDR         | Total number of folders on the TF card.
  * | queryEqualizer()   | STS_EQUALIZER        | Current equalizer mode [0..5].
'''

def WriteCommand(ser, cmd, arg1=0, arg2=0):
    data = [PKT_SOM, PKT_VER, PKT_LEN, cmd, PKT_FB_OFF, arg1, arg2, PKT_EOM]
    ser.write(bytes(data))

def ReadResponse(ser):
    while True:
        if ser.in_waiting < 8: return
        if ser.read(1)[0] == PKT_SOM: break
    ver, length, code, feedback, data_high, data_low, chk_high, chk_low, endcode  = ser.read(9)
    data = (data_high << 8) + data_low
    if endcode != PKT_EOM:
        return -1, "READ ERROR"
    print(responses.get(code, "UNKNOWN STS"), data)
    return code, data

def read_all(ser):
    while (resp := ReadResponse(ser)) is not None:
        print(resp)

def prettyprint(cmd):
    print(" ".join(f"{c:0>2X}" for c in cmd))

def main():
    ser = serial.Serial('/dev/ttyACM0')
    WriteCommand(ser, CMD_SEL_DEV, 0, 2) # required setup
    WriteCommand(ser, CMD_PLAY_FOLDER_FILE, 1, 1) # play folder 1, song 1
    read_all(ser) # print the reply

