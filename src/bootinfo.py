#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  bootinfo.py
#
#  Copyright © 2013,2014 Antergos
#
#  This file is part of Cnchi.
#
#  Cnchi is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  Cnchi is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Cnchi; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.

""" Detects installed OSes (needs root privileges)"""

import os
import subprocess
import re
import tempfile

# When testing, no _() is available
try:
    _("")
except NameError as err:
    def _(message): return message

# constants
WIN_DIRS = ["windows", "WINDOWS", "Windows"]
SYSTEM_DIRS = ["system32", "System32"]

WINLOAD_NAMES = ["Winload.exe", "winload.exe"]
SECEVENT_NAMES = ["SecEvent.Evt", "secevent.evt"]
DOS_NAMES = ["IO.SYS", "io.sys"]
LINUX_NAMES = ["issue", "slackware_version"]

VISTA_MARKS = ["Windows Vista"]
SEVEN_MARKS = ["Win7", "Windows 7"]

DOS_MARKS = ["MS-DOS", "MS-DOS 6.22", "MS-DOS 6.21", "MS-DOS 6.0",
             "MS-DOS 5.0", "MS-DOS 4.01", "MS-DOS 3.3", "Windows 98",
             "Windows 95"]

# Possible locations for os-release. Do not put a trailing /
OS_RELEASE_PATHS = ["usr/lib/os-release", "etc/os-release"]

if __name__ == '__main__':
    import gettext
    _ = gettext.gettext

def _check_windows(mount_name):
    """ Checks for a Microsoft Windows installed """
    # FIXME: Windows Vista/7 detection does not work
    
    detected_os = _("unknown")
    for windows in WIN_DIRS:
        for system in SYSTEM_DIRS:
            # Search for Windows Vista and 7
            for name in WINLOAD_NAMES:
                path = os.path.join(mount_name, windows, system, name)
                if os.path.exists(path):
                    with open(path, "rb") as system_file:
                        lines = system_file.readlines()
                        for line in lines:
                            for vista_mark in VISTA_MARKS:
                                if vista_mark.encode('utf-8') in line:
                                    detected_os = "Windows Vista"
                        if detected_os == _("unknown"):
                            for line in lines:
                                for seven_mark in SEVEN_MARKS:
                                    if seven_mark.encode('utf-8') in line:
                                        detected_os = "Windows 7"
            # Search for Windows XP
            if detected_os == _("unknown"):
                for name in SECEVENT_NAMES:
                    path = os.path.join(mount_name, windows, system, "config", name)
                    if os.path.exists(path):
                        detected_os = "Windows XP"
    return detected_os

def _hexdump8081(partition):
    try:
        return subprocess.check_output(
            ["hexdump", "-v", "-n", "2", "-s", "0x80", "-e", '2/1 "%02x"', partition])
    except subprocess.CalledProcessError as err:
        logging.warning(err)
        return ""

def _get_partition_info(partition):
    # Get bytes 0x80-0x81 of VBR to identify Boot sectors.
    bytes80_to_81 = _hexdump8081(partition).decode()

    bst = {
        '7405':'Windows 7: FAT32',
        '0734':'Dos_1.0',
        '0745':'Windows Vista: FAT32',
        '089e':'MSDOS5.0: FAT16',
        '08cd':'Windows XP: NTFS',
        '0bd0':'MSWIN4.1: FAT32',
        '2a00':'ReactOS',
        '2d5e':'Dos 1.1',
        '3a5e':'Recovery: FAT32',
        '55aa':'Windows Vista/7: NTFS',
        '638b':'Freedos: FAT32',
        '7cc6':'MSWIN4.1: FAT32',
        '8ec0':'Windows XP: NTFS',
        'b6d1':'Windows XP: FAT32',
        'e2f7':'FAT32, Non Bootable',
        'e9d8':'Windows Vista/7: NTFS',
        'fa33':'Windows XP: NTFS'}
    
    if bytes80_to_81 in bst.keys():
        return bst[bytes80_to_81]
    else:
        return _("unknown")

def _check_reactos(mount_name):
    """ Checks for ReactOS """
    detected_os = _("unknown")
    path = os.path.join(mount_name, "ReactOS/system32/config/SecEvent.Evt")
    if os.path.exists(path):
        #print("reactos: ", path)
        detected_os = "ReactOS"
    return detected_os

def _check_dos(mount_name):
    """ Checks for DOS and W9x """
    detected_os = _("unknown")
    for name in DOS_NAMES:
        path = os.path.join(mount_name, name)
        if os.path.exists(path):
            with open(path, "rb") as system_file:
                for mark in DOS_MARKS:
                    if mark in system_file:
                        detected_os = mark
    return detected_os  

def _check_linux(mount_name):
    """ Checks for linux """
    detected_os = _("unknown")

    for os_release in OS_RELEASE_PATHS:
        path = os.path.join(mount_name, os_release)
        if os.path.exists(path):
            with open(path, 'r') as os_release_file:
                lines = os_release_file.readlines()
            for line in lines:
                # Let's use the "PRETTY_NAME"
                if line.startswith("PRETTY_NAME"):
                    detected_os = line[len("PRETTY_NAME="):]
            if detected_os == _("unknown"):
                # Didn't find PRETTY_NAME, we will use ID
                if line.startswith("ID"):
                    os_id = line[len("ID="):]
                if line.startswith("VERSION"):
                    os_version = line[len("VERSION="):]
                detected_os = os_id
                if len(os_version) > 0:
                    detected_os += " " + os_version
    detected_os = detected_os.replace('"', '').strip('\n')

    # If os_release was not found, try old issue file
    if detected_os == _("unknown"):
        for name in LINUX_NAMES:
            path = os.path.join(mount_name, "etc", name)
            if os.path.exists(path):
                with open(path, 'r') as system_file:
                    line = system_file.readline()
                textlist = line.split()
                text = ""
                for element in textlist:
                    if not "\\" in element:
                        text = text + element
                detected_os = text
    return detected_os

def _get_os(mount_name, device):
    """ Detect installed OSes """
    #  If partition is mounted, try to identify the Operating System
    # (OS) by looking for files specific to the OS.
    
    detected_os = _check_windows(mount_name)    

    if detected_os == _("unknown"):
        detected_os = _check_linux(mount_name)

    if detected_os == _("unknown"):
        detected_os = _check_reactos(mount_name)

    if detected_os == _("unknown"):
        detected_os = _check_dos(mount_name)

    return detected_os

def get_os_dict():
    """ Returns all detected OSes in a dict """
    oses = {}

    with open("/proc/partitions", 'r') as partitions_file:
        for line in partitions_file:
            line_split = line.split()
            if len(line_split) > 0:
                device = line_split[3]
                if "sd" in device and re.search(r'\d+$', device):
                    # ok, it has sd and ends with a number
                    device = "/dev/" + device
                    tmp_dir = tempfile.mkdtemp()
                    
                    try:
                        subprocess.call(["mount", device, tmp_dir], stderr=subprocess.DEVNULL)
                        oses[device] = _get_os(tmp_dir, device)
                        subprocess.call(["umount", "-l", tmp_dir], stderr=subprocess.DEVNULL)
                    except AttributeError:
                        subprocess.call(["mount", device, tmp_dir])
                        oses[device] = _get_os(tmp_dir, device)
                        subprocess.call(["umount", "-l", tmp_dir])
                    
                    if oses[device] == _("unknown"):
                        # As a last resort, try reading partition info with hexdump
                        detected_os = _get_partition_info(device)
                        
    return oses

if __name__ == '__main__':
    print(get_os_dict())
