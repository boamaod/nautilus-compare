#!/usr/bin/python3
# -*- coding: utf-8 -*-
#    nautilus-compare --- Context menu extension for Nautilus file manager
#    Copyright (C) 2011-2024  Märt Põder <tramm@infoaed.ee>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import os
import gettext
import locale

from urllib.parse import unquote
from gi.repository import Nautilus, GObject, Gio

sys.path.insert(0, "/usr/share/nautilus-compare")

import utils

class NautilusCompareExtension(GObject.GObject, Nautilus.MenuProvider):
	'''Class for the extension itself'''

	# to hold an item for later comparison
	for_later = None

	def __init__(self):
		'''Load config'''

		GObject.GObject.__init__(self)

		self.config = utils.NautilusCompareConfig()
		self.config.load()

	def menu_activate_cb(self, menu, paths):
		'''Telling from amount of paths runs appropriate comparator engine'''
		if len(paths) == 1:
			self.for_later = paths[0]
			return

		args = ""
		for path in paths:
			args += "\"%s\" " % path

		cmd = None
		if len(paths) == 2:
			cmd = (self.config.diff_engine + " " + args + "&")
		elif len(paths) == 3 and len(self.config.diff_engine_3way.strip()) > 0:
			cmd = (self.config.diff_engine_3way + " " + args + "&")
		elif len(self.config.diff_engine_multi.strip()) > 0:
			cmd = (self.config.diff_engine_multi + " " + args + "&")

		if cmd is not None:
			os.system(cmd)
		
	def valid_file(self, file):
		'''Tests if the file is valid comparable'''
		if file.get_uri_scheme() == 'file' and file.get_file_type() in (Gio.FileType.DIRECTORY, Gio.FileType.REGULAR, Gio.FileType.SYMBOLIC_LINK):
			return True
		elif self.config.diff_engine in utils.URI_COMPAT_ENGINES and file.get_location().get_path() is not None and file.get_file_type() in (Gio.FileType.DIRECTORY, Gio.FileType.REGULAR, Gio.FileType.SYMBOLIC_LINK):
			return True
		else:
			return False

	def get_file_items(self, files):
		'''Main method to detect what choices should be offered in the context menu'''
		paths = []
		for file in files:
			if self.valid_file(file):
				if self.config.diff_engine in utils.URI_COMPAT_ENGINES:
					path = unquote(file.get_uri())
				else:
					path = unquote(file.get_uri()[7:])
				paths.append(path)

		# no files selected
		if len(paths) < 1:
			return

		# initialize i18n
		locale.setlocale(locale.LC_ALL, '')
		gettext.bindtextdomain(utils.APP)
		gettext.textdomain(utils.APP)
		_ = gettext.gettext

		item1 = None
		item2 = None
		item3 = None

		# for paths with remembered items
		new_paths = list(paths)

		# exactly one file selected
		if len(paths) == 1:

			# and one was already selected for later comparison
			if self.for_later is not None:

				# we don't want to compare file to itself
				if self.for_later not in paths:
					item1 = Nautilus.MenuItem(
						name="NautilusCompareExtension::CompareTo",
						label=_('Compare to ') + utils.prepare_for_menu(self.for_later),
						tip=_("Compare to the file remembered before")
					)

					# compare the one saved for later to the one selected now
					new_paths.insert(0, self.for_later)

			# if only one file selected, we offer to remember it for later anyway
			item3 = Nautilus.MenuItem(
				name="NautilusCompareExtension::CompareLater",
				label=_('Compare Later'),
				tip=_("Remember file for later comparison")
			)

		# can always compare, if more than one selected
		else:
			# if we have already remembered one file and add some more, we can do n-way compare
			if self.for_later is not None:
				if self.for_later not in paths:
					# if multi compare enabled and in case of 2 files selected 3way compare enabled
					if len(self.config.diff_engine_multi.strip()) > 0 or (len(paths) == 2 and len(self.config.diff_engine_3way.strip()) > 0):
						item1 = Nautilus.MenuItem(
							name="NautilusCompareExtension::MultiCompare",
							label=_('Compare to ') + utils.prepare_for_menu(self.for_later),
							tip=_("Compare selected files to the file remembered before")
						)
						# compare the one saved for later to the ones selected now
						new_paths.insert(0, self.for_later)

			# if multi compare enabled, we can compare any number
			# if there are two files selected we can always compare
			# if three files selected and 3-way compare is on, we can do it
			if len(self.config.diff_engine_multi.strip()) > 0 or len(paths) == 2 or (len(paths) == 3 and len(self.config.diff_engine_3way.strip()) > 0):
				item2 = Nautilus.MenuItem(
					name="NautilusCompareExtension::CompareWithin",
					label=_('Compare'),
					tip=_("Compare selected files")
				)

		if item1: item1.connect('activate', self.menu_activate_cb, new_paths)
		if item2: item2.connect('activate', self.menu_activate_cb, paths)
		if item3: item3.connect('activate', self.menu_activate_cb, paths)

		items = [item1, item2, item3]

		while None in items:
			items.remove(None)

		return items

