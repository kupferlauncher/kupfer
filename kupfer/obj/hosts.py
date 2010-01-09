# -*- encoding: utf-8 -*-
"""
Kupfer's Hosts API

Main definition and *constructor* classes.
"""

from kupfer.obj.grouping import GroupingLeaf 

__author__ = ("Ulrik Sverdrup <ulrik.sverdrup@gmail.com>, "
              "Karol Będkowski <karol.bedkowsk+gh@gmail.com>" )

HOST_NAME_KEY = "HOST_NAME"
HOST_ADDRESS_KEY = "HOST_ADDRESS"

class HostLeaf(GroupingLeaf):
	grouping_slots = (HOST_NAME_KEY, HOST_ADDRESS_KEY)

	def get_icon_name(self):
		return "computer"


