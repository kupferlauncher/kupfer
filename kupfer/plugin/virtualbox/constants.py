# -*- coding: UTF-8 -*-
'''
virtualbox_const_support.py

Constants for VirtualBox.
'''
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"
__version__ = '0.3'

# virtual machine states
VM_STATE_POWEROFF = 0
VM_STATE_POWERON = 1
VM_STATE_PAUSED = 2
VM_STATE_SAVED = 3

# virtual machine actions
VM_START_NORMAL = 1
VM_START_HEADLESS = 2
VM_PAUSE = 3
VM_POWEROFF = 4
VM_ACPI_POWEROFF = 5
VM_REBOOT = 6
VM_RESUME = 7
VM_SAVE = 8
