from enigma import iPlayableService, iServiceInformation, iFrontendInformation, eTimer, gRGB, eConsoleAppContainer, getDesktop
from boxbranding import getBoxType  # MODEL import from getBoxType for all images OE
from requests import get
from urllib.request import urlopen, Request
from twisted.web.client import getPage
from datetime import datetime
from json import dump, loads
from glob import glob
from os import listdir, makedirs, remove
from os.path import join, exists, normpath
from configparser import ConfigParser
from time import sleep, localtime, mktime, time
from shutil import move, copy
from re import search
from sys import stdout
from RecordTimer import RecordTimerEntry
from ServiceReference import ServiceReference
from timer import TimerEntry
from Tools.Directories import SCOPE_PLUGINS, fileContains, fileExists, isPluginInstalled, resolveFilename
from Plugins.Plugin import PluginDescriptor
from Components.config import config, getConfigListEntry, ConfigClock, ConfigSelection, ConfigYesNo, ConfigText, ConfigSubsection, ConfigEnableDisable, ConfigSubDict
from Components.ActionMap import ActionMap
from Components.ServiceEventTracker import ServiceEventTracker
from Components.ConfigList import ConfigListScreen
from Components.MenuList import MenuList
from Components.Label import Label
from Components.SystemInfo import BoxInfo
from Components.Sources.StaticText import StaticText
from Components.Console import Console
from Components.Harddisk import harddiskmanager
from Screens.Screen import Screen
from Screens.ChannelSelection import ChannelSelectionBase
from Screens.MessageBox import MessageBox
from Screens.Standby import TryQuitMainloop

screenWidth = getDesktop(0).size().width()
MODEL = getBoxType()
PLAYLIST_PATH = "/etc/enigma2/iptosat.json"
CHANNELS_LISTS_PATH = "/etc/enigma2/iptosatchlist.json"
SUSCRIPTION_USER_DATA = "/etc/enigma2/suscriptiondata"
BUILDBOUQUETS_FILE = resolveFilename(SCOPE_PLUGINS, "Extensions/IPToSAT/buildbouquets")
BUILDBOUQUETS_SOURCE = resolveFilename(SCOPE_PLUGINS, "Extensions/IPToSAT/buildbouquets.py")
REFERENCES_FILE = "/etc/enigma2/iptosatreferences"
CONFIG_PATH_CATEGORIES = "/etc/enigma2/iptosatcategories.json"
WILD_CARD_ALL_CATEGORIES = "/etc/enigma2/iptosatcatall"
WILD_CARD_CATYOURLIST = "/etc/enigma2/iptosatyourcatall"
BACKUP_CATEGORIES = "iptosatyourcatbackup"
WILD_CARD_CATEGORIES_FILE = "/etc/enigma2/wildcardcategories"
ALL_CATEGORIES = "/etc/enigma2/iptosatcategoriesall.json"
CATEGORIES_TIMER_OK = "/tmp/timercatiptosat.log"
TIMER_OK = ""
CATEGORIES_TIMER_ERROR = "/tmp/timercatiptosat_error.log"
TIMER_ERROR = ""
USER_LIST_CATEGORIE_CHOSEN = ""
USER_EDIT_CATEGORIE = ""
READ_M3U = "/etc/enigma2/readm3u.txt"
CONFIG_PATH = "/etc/enigma2/iptosat.conf"
SOURCE_PATH = resolveFilename(SCOPE_PLUGINS, "Extensions/IPToSAT")
LANGUAGE_PATH = resolveFilename(SCOPE_PLUGINS, "Extensions/IPToSAT/languages")
VERSION_PATH = resolveFilename(SCOPE_PLUGINS, "Extensions/IPToSAT/version")
IPToSAT_EPG_PATH = "/etc/enigma2/userbouquet.iptosat_epg.tv"
FILE_IPToSAT_EPG = "userbouquet.iptosat_epg.tv"
BOUQUETS_TV = "/etc/enigma2/bouquets.tv"
BOUQUET_IPTV_NORHAP = "/etc/enigma2/userbouquet.iptosat_norhap.tv"
WILD_CARD_BOUQUET_IPTV_NORHAP = "/etc/enigma2/wildcardbouquetnorhap"
WILD_CARD_EPG_FILE = "/etc/enigma2/wildcardepg"
WILD_CARD_BOUQUETSTV = "/etc/enigma2/wildcardbouquetstv"
ENIGMA2_PATH = "/etc/enigma2"
ENIGMA2_PATH_LISTS = "/etc/enigma2/"
FILES_TUXBOX = "/etc/tuxbox"

try:
	if not fileContains(LANGUAGE_PATH, "[" + config.osd.language.value[:-3] + "]"):
		lang = "en"
	else:
		from Components.Language import language
		lang = language.getLanguage()
		lang = lang[:2]
except Exception:
	try:
		lang = config.osd.language.value[:-3]
	except Exception:
		lang = "en"

try:
	language = ConfigParser()
	language.read(LANGUAGE_PATH, encoding="utf8")
except Exception:
	try:
		lang = "en"
		language = ConfigParser()
		language.read(LANGUAGE_PATH, encoding="utf8")
	except Exception:
		pass


def choices_list():
	if fileExists('/var/lib/dpkg/status'):
		# Fixed DreamOS by. audi06_19 , gst-play-1.0
		return [("gst-play-1.0", "OE-2.5 Player"), ("exteplayer3", "ExtEplayer3"),]
	elif isPluginInstalled("FastChannelChange") and BoxInfo.getItem("distro") == "norhap":
		return [("gstplayer", "GstPlayer")]
	else:
		return [("gstplayer", "GstPlayer"), ("exteplayer3", "ExtEplayer3"),]


default_player = "exteplayer3" if fileExists('/var/lib/dpkg/status') or not isPluginInstalled("FastChannelChange") else "gstplayer"
config.plugins.IPToSAT = ConfigSubsection()
config.plugins.IPToSAT.enable = ConfigYesNo(default=True) if fileContains(PLAYLIST_PATH, '"sref": "') else ConfigYesNo(default=False)
config.plugins.IPToSAT.mainmenu = ConfigYesNo(default=False)
config.plugins.IPToSAT.showuserdata = ConfigYesNo(default=True)
config.plugins.IPToSAT.usercategories = ConfigYesNo(default=False)
config.plugins.IPToSAT.deletecategories = ConfigYesNo(default=False)
config.plugins.IPToSAT.autotimerbouquets = ConfigYesNo(default=False)
config.plugins.IPToSAT.player = ConfigSelection(default=default_player, choices=choices_list())
config.plugins.IPToSAT.assign = ConfigSelection(choices=[("1", language.get(lang, "34"))], default="1")
config.plugins.IPToSAT.typecategories = ConfigSelection(choices=[("live", language.get(lang, "148")), ("vod", language.get(lang, "149")), ("series", language.get(lang, "150")), ("all", language.get(lang, "157")), ("none", language.get(lang, "158"))], default="live")
config.plugins.IPToSAT.playlist = ConfigSelection(choices=[("1", language.get(lang, "34"))], default="1")
config.plugins.IPToSAT.categories = ConfigSelection(choices=[("1", language.get(lang, "34"))], default="1")
config.plugins.IPToSAT.installchannelslist = ConfigSelection(choices=[("1", language.get(lang, "34"))], default="1")
config.plugins.IPToSAT.domain = ConfigText(default="http://domain", fixed_size=False)
config.plugins.IPToSAT.serverport = ConfigText(default="80", fixed_size=False)
config.plugins.IPToSAT.username = ConfigText(default=language.get(lang, "113"), fixed_size=False)
config.plugins.IPToSAT.password = ConfigText(default=language.get(lang, "114"), fixed_size=False)
config.plugins.IPToSAT.networkidzerotier = ConfigText(default=language.get(lang, "188"), fixed_size=False)
config.plugins.IPToSAT.timebouquets = ConfigClock(default=64800)
if BoxInfo.getItem("distro") == "norhap":
	config.plugins.IPToSAT.timecardon = ConfigSubDict()
	config.plugins.IPToSAT.timecardoff = ConfigSubDict()
	config.plugins.IPToSAT.cardday = ConfigSubDict()
	for day in range(7):
		config.plugins.IPToSAT.cardday[day] = ConfigEnableDisable(default=False)
		config.plugins.IPToSAT.timecardon[day] = ConfigClock(default=((23 * 60 + 0) * 60))
		config.plugins.IPToSAT.timecardoff[day] = ConfigClock(default=((20 * 60 + 0) * 60))


def typeselectcategorie():
	if config.plugins.IPToSAT.typecategories.value == "live":
		USER_LIST_CATEGORIE_CHOSEN = language.get(lang, "133") + " " + '"' + language.get(lang, "148") + '"'
	elif config.plugins.IPToSAT.typecategories.value == "vod":
		USER_LIST_CATEGORIE_CHOSEN = language.get(lang, "133") + " " + '"' + language.get(lang, "149") + '"'
	elif config.plugins.IPToSAT.typecategories.value == "series":
		USER_LIST_CATEGORIE_CHOSEN = language.get(lang, "133") + " " + '"' + language.get(lang, "150") + '"'
	else:
		USER_LIST_CATEGORIE_CHOSEN = language.get(lang, "163") + " " + '"' + language.get(lang, "157") + '"'
	return USER_LIST_CATEGORIE_CHOSEN


def trace_error():
	import traceback
	try:
		traceback.print_exc(file=stdout)
		traceback.print_exc(file=open('/tmp/IPToSAT.log', 'a'))
	except Exception:
		pass


def log(data):
	now = datetime.now().strftime('%Y-%m-%d %H:%M')
	open('/tmp/IPToSAT.log', 'a').write(now + ' : ' + str(data) + '\r\n')


def getversioninfo():
	currversion = '1.0'
	if exists(VERSION_PATH):
		try:
			with open(VERSION_PATH, 'r') as versionread:
				version = versionread.readlines()
				for line in version:
					if 'version' in line:
						currversion = line.split('=')[1].strip()
		except Exception:
			pass
	return (currversion)


VERSION = getversioninfo()


def parseColor(s):
	return gRGB(int(s[1:], 0x10))


def getPlaylist():
	if fileExists(PLAYLIST_PATH):
		with open(PLAYLIST_PATH, 'r') as f:
			try:
				return loads(f.read())
			except ValueError:
				trace_error()
	else:
		return None


def getCategories():
	if fileExists(CONFIG_PATH_CATEGORIES):
		with open(CONFIG_PATH_CATEGORIES, 'r') as f:
			try:
				return loads(f.read())
			except ValueError:
				trace_error()
	else:
		return None


def getChannelsLists():
	if fileExists(CHANNELS_LISTS_PATH):
		with open(CHANNELS_LISTS_PATH, 'r') as f:
			try:
				return loads(f.read())
			except ValueError:
				trace_error()
	else:
		return None


class IPToSATSetup(Screen, ConfigListScreen):
	skin = """
	<screen name="IPToSATSetup" position="30,90" size="1860,930" backgroundColor="#0023262f" title="IPToSATSetup settings">
		<eLabel backgroundColor="#0044a2ff" position="982,8" size="873,2"/>
		<eLabel backgroundColor="#0044a2ff" position="982,8" size="2,920"/>
		<eLabel backgroundColor="#0044a2ff" position="982,926" size="873,2"/>
		<eLabel backgroundColor="#0044a2ff" position="1855,8" size="2,920"/>
		<eLabel backgroundColor="#0044a2ff" position="11,872" size="1,52"/>
		<eLabel backgroundColor="#0044a2ff" position="11,924" size="169,1"/>
		<eLabel backgroundColor="#0044a2ff" position="11,871" size="169,1"/>
		<eLabel backgroundColor="#0044a2ff" position="179,872" size="1,52"/>
		<eLabel backgroundColor="#0044a2ff" position="188,872" size="1,52"/>
		<eLabel backgroundColor="#0044a2ff" position="188,924" size="168,1"/>
		<eLabel backgroundColor="#0044a2ff" position="188,871" size="168,1"/>
		<eLabel backgroundColor="#0044a2ff" position="355,872" size="1,52"/>
		<widget name="config" itemHeight="50" position="0,10" font="Regular;27" valueFont="Regular;22" size="980,860" backgroundColor="#0023262f" scrollbarMode="showOnDemand" scrollbarForegroundColor="#0044a2ff" scrollbarBorderColor="#0044a2ff" />
		<widget name="key_red" position="12,872" size="165,52" zPosition="2" backgroundColor="key_red" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text" />
		<widget name="key_green" position="189,872" size="165,52" zPosition="2" backgroundColor="key_green" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text" />
		<widget source="key_yellow" render="Label" objectTypes="key_yellow,StaticText" position="366,872" zPosition="2" size="165,52" backgroundColor="key_yellow" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
			<convert type="ConditionalShowHide"/>
		</widget>
		<widget source="key_blue" conditional="key_blue" render="Label" objectTypes="key_blue,StaticText" position="720,872" zPosition="2" size="200,52" backgroundColor="key_blue" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
			<convert type="ConditionalShowHide"/>
		</widget>
		<widget source="VKeyIcon" text="TEXT" render="Label" position="543,872" size="165,52" zPosition="2" backgroundColor="key_back" conditional="VKeyIcon" font="Regular;22" foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="session.VideoPicture" render="Pig" position="985,10" size="870,500" zPosition="1" backgroundColor="#df0b1300"/>
		<widget name="HelpWindow" position="1010,855" size="0,0" alphaTest="blend" conditional="HelpWindow" transparent="1" zPosition="+1" />
		<widget name="description" font="Regular;26" position="985,520" size="860,320" foregroundColor="#00e5e619" transparent="1" verticalAlignment="top"/>
		<widget name="footnote" conditional="footnote" position="985,842" size="860,80" foregroundColor="#0086dc3d" font="Regular;25" transparent="1" zPosition="3" />
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = ["IPToSATSetup"] if screenWidth == 1920 else ["Setup"]
		self.setup_title = language.get(lang, "13")
		self.storage = False
		self.path = None
		self.onChangedEntry = []
		self.list = []
		ConfigListScreen.__init__(self, self.list, session=session, on_change=self.changedEntry)
		self["actions"] = ActionMap(["IPToSATActions"],
		{
			"back": self.keyCancel,
			"down": self.moveDown,
			"up": self.moveUp,
			"left": self.keyLeft,
			"right": self.keyRight,
			"cancel": self.keyCancel,
			"red": self.keyCancel,
			"green": self.keySave,
			"yellow": self.joinZeroTier,
			"blue": self.IPToSATWithCardOrFull,
			"ok": self.ok,
		}, -2)
		self["description"] = Label("")
		self["key_red"] = Label(_("Cancel"))  # noqa: F821
		self["key_green"] = Label(_("Save"))  # noqa: F821
		self["key_yellow"] = StaticText("")  # noqa: F821
		self["key_blue"] = StaticText("")  # noqa: F821
		self["footnote"] = Label("")  # noqa: F821
		self.timerupdatebouquets = config.plugins.IPToSAT.timebouquets.value[0] + config.plugins.IPToSAT.timebouquets.value[1]
		self.typecategories = config.plugins.IPToSAT.typecategories.value
		self.onLayoutFinish.append(self.layoutFinished)
		for partition in harddiskmanager.getMountedPartitions():
			self.path = normpath(partition.mountpoint)
			if self.path != "/" and "net" not in self.path and "autofs" not in self.path:
				if exists(str(self.path)) and listdir(self.path):
					self.storage = True
		if BoxInfo.getItem("distro") == "norhap":
			if not exists(ENIGMA2_PATH_LISTS + "iptosatjsonall") and not exists(ENIGMA2_PATH_LISTS + "iptosatjsoncard"):
				copy(PLAYLIST_PATH, ENIGMA2_PATH_LISTS + "iptosatjsonall")
			if exists(ENIGMA2_PATH_LISTS + "iptosatjsonall"):
				self["key_blue"].setText(language.get(lang, "194"))  # noqa: F821
			elif exists(ENIGMA2_PATH_LISTS + "iptosatjsoncard"):
				self["key_blue"].setText(language.get(lang, "195"))  # noqa: F821
		self.createSetup()

	def layoutFinished(self):
		self.setTitle(language.get(lang, "13"))

	def createSetup(self):
		if not fileContains(CONFIG_PATH, "pass"):
			self.list = [getConfigListEntry(language.get(lang, "14"),
				config.plugins.IPToSAT.enable, language.get(lang, "8"))]
		else:
			self.list = [getConfigListEntry(language.get(lang, "14"),
				config.plugins.IPToSAT.enable, language.get(lang, "141"))]
		self.list.append(getConfigListEntry(language.get(lang, "15"),
			config.plugins.IPToSAT.assign, language.get(lang, "35")))
		self.list.append(getConfigListEntry(language.get(lang, "16"),
			config.plugins.IPToSAT.playlist, language.get(lang, "100")))
		if config.plugins.IPToSAT.showuserdata.value:
			self.list.append(getConfigListEntry(language.get(lang, "111"),
				config.plugins.IPToSAT.domain, language.get(lang, "99")))
			self.list.append(getConfigListEntry(language.get(lang, "112"),
				config.plugins.IPToSAT.serverport, language.get(lang, "99")))
			self.list.append(getConfigListEntry(language.get(lang, "113"),
				config.plugins.IPToSAT.username, language.get(lang, "99")))
			self.list.append(getConfigListEntry(language.get(lang, "114"),
				config.plugins.IPToSAT.password, language.get(lang, "99")))
			if exists("/usr/sbin/zerotier-one"):
				if config.plugins.IPToSAT.networkidzerotier.default != config.plugins.IPToSAT.networkidzerotier.value:
					self.list.append(getConfigListEntry(language.get(lang, "186"),
						config.plugins.IPToSAT.networkidzerotier, language.get(lang, "191")))
				else:
					self.list.append(getConfigListEntry(language.get(lang, "186"),
						config.plugins.IPToSAT.networkidzerotier, language.get(lang, "187")))
		if not fileContains(CONFIG_PATH, "pass"):
			if config.plugins.IPToSAT.typecategories.value not in ("all", "none"):
				self.list.append(getConfigListEntry(language.get(lang, "151"),
					config.plugins.IPToSAT.typecategories, language.get(lang, "152")))
			if config.plugins.IPToSAT.typecategories.value == "all":
				self.list.append(getConfigListEntry(language.get(lang, "151"),
					config.plugins.IPToSAT.typecategories, language.get(lang, "159")))
			if config.plugins.IPToSAT.typecategories.value == "none":
				self.list.append(getConfigListEntry(language.get(lang, "160"),
					config.plugins.IPToSAT.typecategories, language.get(lang, "168")))
			else:
				if fileContains(CONFIG_PATH_CATEGORIES, ":"):
					self.list.append(getConfigListEntry(typeselectcategorie(),
						config.plugins.IPToSAT.categories, language.get(lang, "74")))
				else:
					self.list.append(getConfigListEntry(typeselectcategorie(),
						config.plugins.IPToSAT.categories, language.get(lang, "156")))
				if config.plugins.IPToSAT.typecategories.value != "all":
					self.list.append(getConfigListEntry(language.get(lang, "171") + " " + typeselectcategorie(),
						config.plugins.IPToSAT.usercategories, language.get(lang, "172") + " " + typeselectcategorie() + "."))
				if fileContains(BOUQUETS_TV, "iptosat_norhap"):
					self.list.append(getConfigListEntry(language.get(lang, "127"),
						config.plugins.IPToSAT.deletecategories, language.get(lang, "122")))
				self.list.append(getConfigListEntry(language.get(lang, "144"),
					config.plugins.IPToSAT.autotimerbouquets, language.get(lang, "146")))
				if config.plugins.IPToSAT.autotimerbouquets.value:
					self.list.append(getConfigListEntry(language.get(lang, "145"),
						config.plugins.IPToSAT.timebouquets, language.get(lang, "130")))
		if BoxInfo.getItem("distro") == "norhap":
			for day in range(7):
				self.list.append(getConfigListEntry([
					language.get(lang, "199"),
					language.get(lang, "200"),
					language.get(lang, "201"),
					language.get(lang, "202"),
					language.get(lang, "203"),
					language.get(lang, "204"),
					language.get(lang, "205")]
					[day],
					config.plugins.IPToSAT.cardday[day]))
				if config.plugins.IPToSAT.cardday[day].value:
					self.list.append(getConfigListEntry(language.get(lang, "197"),
						config.plugins.IPToSAT.timecardoff[day]))
					self.list.append(getConfigListEntry(language.get(lang, "198"),
						config.plugins.IPToSAT.timecardon[day]))
		if self.storage:
			self.list.append(getConfigListEntry(language.get(lang, "88"), config.plugins.IPToSAT.installchannelslist))
		self.list.append(getConfigListEntry(language.get(lang, "17"), config.plugins.IPToSAT.player))
		self.list.append(getConfigListEntry(language.get(lang, "98"),
			config.plugins.IPToSAT.mainmenu, language.get(lang, "38")))
		self.list.append(getConfigListEntry(language.get(lang, "116"), config.plugins.IPToSAT.showuserdata))
		self["config"].list = self.list
		self["config"].setList(self.list)
		self.saveConfig()
		if TimerEntry.StateEnded < int(time()):
			self.session.nav.PowerTimer.cleanup()
		if RecordTimerEntry.StateEnded < int(time()):
			self.session.nav.RecordTimer.cleanup()
		if config.plugins.IPToSAT.autotimerbouquets.value:
			if exists(str(CATEGORIES_TIMER_OK)):
				with open(CATEGORIES_TIMER_OK, "r") as fr:
					TIMER_OK = fr.read()
					self["footnote"] = Label(language.get(lang, "167") + "\n" + TIMER_OK)
			elif exists(str(CATEGORIES_TIMER_ERROR)):
				with open(CATEGORIES_TIMER_ERROR, "r") as fr:
					TIMER_ERROR = fr.read()
					self["footnote"] = Label(language.get(lang, "147") + " " + TIMER_ERROR)
		if isPluginInstalled("FastChannelChange") and fileContains(PLAYLIST_PATH, '"sref": "') and BoxInfo.getItem("distro") == "norhap" and config.plugins.IPToSAT.enable.value:
			try:
				if not config.plugins.fccsetup.activate.value:
					config.plugins.fccsetup.activate.value = True
					config.plugins.fccsetup.activate.save()
					config.plugins.fccsetup.maxfcc.value = 2
					config.plugins.fccsetup.maxfcc.save()
					config.usage.remote_fallback_enabled.value = False
					config.usage.remote_fallback_enabled.save()
					self.session.open(TryQuitMainloop, 3)
			except Exception:
				pass

	def saveConfig(self):
		if fileExists(CONFIG_PATH):
			try:
				with open(CONFIG_PATH, "r") as f:
					iptosatconfread = f.read()
					host = iptosatconfread.split()[1].split('Host=')[1].split(':')[1].replace("//", "http://") if not fileContains(CONFIG_PATH, "https") else iptosatconfread.split()[1].split('Host=')[1].split(':')[1].replace("//", "https://")
					port = iptosatconfread.split()[1].split(host)[1].replace(":", "")
					user = iptosatconfread.split()[2].split('User=')[1]
					password = iptosatconfread.split()[3].split('Pass=')[1]
					config.plugins.IPToSAT.domain.value = host
					config.plugins.IPToSAT.domain.save()
					config.plugins.IPToSAT.serverport.value = port if port != "port" else language.get(lang, "115")
					config.plugins.IPToSAT.serverport.save()
					config.plugins.IPToSAT.username.value = user
					config.plugins.IPToSAT.username.save()
					config.plugins.IPToSAT.password.value = password
					config.plugins.IPToSAT.password.save()
			except Exception as err:
				print("ERROR: %s" % str(err))
		self.saveiptosatconf()

	def ok(self):
		current = self["config"].getCurrent()
		if current[1] == config.plugins.IPToSAT.assign:
			self.session.open(AssignService)
		elif current[1] == config.plugins.IPToSAT.playlist:
			self.session.open(EditPlaylist)
		elif current[1] == config.plugins.IPToSAT.categories:
			self.session.open(EditCategories)
		elif current[1] == config.plugins.IPToSAT.installchannelslist:
			self.session.open(InstallChannelsLists)

	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def keySave(self):
		if config.plugins.IPToSAT.autotimerbouquets.value:
			self.timerinstance = TimerUpdateCategories(self.session)
			self.timerinstance.refreshScheduler()
		if self.timerupdatebouquets != config.plugins.IPToSAT.timebouquets.value[0] + config.plugins.IPToSAT.timebouquets.value[1]:
			if exists(str(CATEGORIES_TIMER_ERROR)):
				remove(CATEGORIES_TIMER_ERROR)
		if config.plugins.IPToSAT.autotimerbouquets.value:
			self.timercategories = TimerUpdateCategories(self)
		if BoxInfo.getItem("distro") == "norhap":
			if config.plugins.IPToSAT.cardday[day].value:
				self.timercardoff = TimerOffCard(self)  # timer cardoff init
				self.timercardon = TimerOnCard(self)  # timer cardon init
		if config.plugins.IPToSAT.typecategories.value not in ("all", "none"):
			if self.typecategories != config.plugins.IPToSAT.typecategories.value:
				if config.plugins.IPToSAT.usercategories.value:
					config.plugins.IPToSAT.usercategories.value = False
					config.plugins.IPToSAT.usercategories.save()
				AssignService(self.session)
		else:
			if self.typecategories != config.plugins.IPToSAT.typecategories.value:
				config.plugins.IPToSAT.typecategories.value = "all"
				config.plugins.IPToSAT.typecategories.save()
				if fileContains(WILD_CARD_CATYOURLIST, ":"):
					with open(WILD_CARD_CATYOURLIST, "r") as fr:
						with open(CONFIG_PATH_CATEGORIES, "w") as fw:
							fw.write("{" + '\n')
						with open(CONFIG_PATH_CATEGORIES, "a") as fw:
							for lines in fr.readlines():
								lines = lines.replace("]", "],").replace("],,", "],")
								fw.write(lines)
						with open(CONFIG_PATH_CATEGORIES, "r") as fwildcardread:
							with open(CONFIG_PATH_CATEGORIES, "a") as fwildcardwrite:
								readcategoriesjson = fwildcardread.readlines()
								if len(readcategoriesjson) > 1:
									for last in readcategoriesjson[-2]:
										last = last.replace(",", "")
										fwildcardwrite.write(last)
						with open(CONFIG_PATH_CATEGORIES, "a") as fw:
							fw.write("}")
				else:
					if fileContains(ALL_CATEGORIES, ":"):
						move(ALL_CATEGORIES, CONFIG_PATH_CATEGORIES)
		if config.plugins.IPToSAT.typecategories.value == "none":
			self.deleteBouquetsNorhap()
		AssignService(self)
		self.saveiptosatconf()
		ConfigListScreen.keySave(self)

	def joinZeroTier(self):
		if config.plugins.IPToSAT.showuserdata.value:
			if exists("/usr/sbin/zerotier-one"):
				from process import ProcessList  # noqa: E402
				zerotier_process = str(ProcessList().named('zerotier-one')).strip('[]')
				zerotier_auto = glob("/etc/rc2.d/S*zerotier")
				if not zerotier_process:
					eConsoleAppContainer().execute("/etc/init.d/zerotier start")
				if not zerotier_auto:
					eConsoleAppContainer().execute("update-rc.d -f zerotier defaults")
				if config.plugins.IPToSAT.networkidzerotier.value != config.plugins.IPToSAT.networkidzerotier.default:
					eConsoleAppContainer().execute('sleep 15; zerotier-cli join {}' .format(config.plugins.IPToSAT.networkidzerotier.value))
					self.session.open(MessageBox, language.get(lang, "190"), MessageBox.TYPE_INFO, default=False, simple=True, timeout=15)
				else:
					self.session.open(MessageBox, language.get(lang, "192"), MessageBox.TYPE_ERROR, simple=True)
			else:
				self.session.open(MessageBox, language.get(lang, "193"), MessageBox.TYPE_ERROR, simple=True)

	def IPToSATWithCardOrFull(self):
		if BoxInfo.getItem("distro") == "norhap" and exists(FILES_TUXBOX + "/config/oscam/oscam.services.no.card") and exists(str(PLAYLIST_PATH)):
			if exists(ENIGMA2_PATH_LISTS + "iptosatjsonall"):
				move(PLAYLIST_PATH, ENIGMA2_PATH_LISTS + "iptosatjsoncard")
				move(ENIGMA2_PATH_LISTS + "iptosatjsonall", PLAYLIST_PATH)
				move(FILES_TUXBOX + "/config/oscam/oscam.services", FILES_TUXBOX + "/config/oscam/oscam.services.card")
				move(FILES_TUXBOX + "/config/oscam/oscam.services.no.card", FILES_TUXBOX + "/config/oscam/oscam.services")
				self["key_blue"].setText(language.get(lang, "195"))
				eConsoleAppContainer().execute("/etc/init.d/softcam.oscam restart")
				return
			elif exists(ENIGMA2_PATH_LISTS + "iptosatjsoncard"):
				move(PLAYLIST_PATH, ENIGMA2_PATH_LISTS + "iptosatjsonall")
				move(ENIGMA2_PATH_LISTS + "iptosatjsoncard", PLAYLIST_PATH)
				move(FILES_TUXBOX + "/config/oscam/oscam.services", FILES_TUXBOX + "/config/oscam/oscam.services.no.card")
				move(FILES_TUXBOX + "/config/oscam/oscam.services.card", FILES_TUXBOX + "/config/oscam/oscam.services")
				self["key_blue"].setText(language.get(lang, "194"))
				eConsoleAppContainer().execute("/etc/init.d/softcam.oscam restart")

	def keyCancel(self):
		ConfigListScreen.keyCancel(self)

	def moveUp(self):
		self["config"].moveUp()
		if BoxInfo.getItem("distro") not in ("norhap", "openspa"):
			self["description"].text = self.getCurrentDescription()

	def moveDown(self):
		self["config"].moveDown()
		if BoxInfo.getItem("distro") not in ("norhap", "openspa"):
			self["description"].text = self.getCurrentDescription()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.createSetup()
		if BoxInfo.getItem("distro") not in ("norhap", "openspa"):
			self["description"].text = self.getCurrentDescription()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.createSetup()
		if BoxInfo.getItem("distro") not in ("norhap", "openspa"):
			self["description"].text = self.getCurrentDescription()

	def saveiptosatconf(self):
		if exists(CONFIG_PATH):
			with open(CONFIG_PATH, 'w') as iptosatconf:
				iptosatconf.write("[IPToSAT]" + "\n" + 'Host=' + config.plugins.IPToSAT.domain.value + ":" + config.plugins.IPToSAT.serverport.value + "\n" + "User=" + config.plugins.IPToSAT.username.value + "\n" + "Pass=" + config.plugins.IPToSAT.password.value)
		else:
			with open(CONFIG_PATH, 'w') as iptosatconf:
				iptosatconf.write("[IPToSAT]" + "\n" + 'Host=http://domain:port' + "\n" + "User=user" + "\n" + "Pass=pass")
		if config.plugins.IPToSAT.showuserdata.value:
			if exists("/usr/sbin/zerotier-one"):
				self["key_yellow"] = StaticText(language.get(lang, "189"))  # noqa: F821

	def deleteBouquetsNorhap(self):
		with open(CONFIG_PATH_CATEGORIES, 'w') as fw:
			fw.write("")
		with open(WILD_CARD_ALL_CATEGORIES, 'w') as fw:
			fw.write("")
		for bouquets_iptosat_norhap in [x for x in listdir(ENIGMA2_PATH) if "iptosat_norhap" in x]:
			with open(BOUQUETS_TV, "r") as fr:
				bouquetread = fr.readlines()
				with open(BOUQUETS_TV, "w") as bouquetswrite:
					for line in bouquetread:
						if "iptosat_norhap" not in line:
							bouquetswrite.write(line)
			enigma2files = join(ENIGMA2_PATH, bouquets_iptosat_norhap)
			if enigma2files:
				remove(enigma2files)
			eConsoleAppContainer().execute('wget -qO - http://127.0.0.1/web/servicelistreload?mode=2 ; wget -qO - http://127.0.0.1/web/servicelistreload?mode=2')


class TimerUpdateCategories:
	def __init__(self, session):
		self.session = session
		self.categoriestimer = eTimer()
		self.categoriestimer.callback.append(self.iptosatDownloadTimer)
		self.iptosatpolltimer = eTimer()
		self.iptosatpolltimer.timeout.get().append(self.iptosatPollTimer)
		self.refreshScheduler()

	def iptosatPollTimer(self):
		self.iptosatpolltimer.stop()
		self.scheduledtime = self.prepareTimer()

	def getTimeDownloadCategories(self):
		downloadcategoriesclock = config.plugins.IPToSAT.timebouquets.value
		now = localtime(time())
		return int(mktime((now.tm_year, now.tm_mon, now.tm_mday, downloadcategoriesclock[0], downloadcategoriesclock[1], 0, now.tm_wday, now.tm_yday, now.tm_isdst)))

	def prepareTimer(self):
		self.categoriestimer.stop()
		downloadtime = self.getTimeDownloadCategories()
		now = int(time())
		if downloadtime > 0:
			if downloadtime < now:
				downloadtime += 24 * 3600
				while (int(downloadtime) - 30) < now:
					downloadtime += 24 * 3600
			next = downloadtime - now
			self.categoriestimer.startLongTimer(next)
		else:
			downloadtime = -1
		return downloadtime

	def iptosatDownloadTimer(self):
		self.categoriestimer.stop()
		now = int(time())
		wake = self.getTimeDownloadCategories()
		self.m3ufile = join(ENIGMA2_PATH, "iptosat_norhap.m3u")
		m3u = ""
		response = ""
		with open(CONFIG_PATH, "r") as fr:
			configfile = fr.read()
			hostport = configfile.split()[1].split("Host=")[1]
			user = configfile.split()[2].split('User=')[1]
			password = configfile.split()[3].split('Pass=')[1]
			# try:
			# 	urlm3u = str(hostport) + '/get.php?username=' + str(user) + '&password=' + str(password) + '&type=m3u_plus&output=ts'
			# 	m3u = get(urlm3u, allow_redirects=True)
			# except Exception:
			# 	try:
			# 		urlm3u = str(hostport) + '/get.php?username=' + str(user) + '&password=' + str(password) + '&type=m3u_plus&output=m3u8'
			# 		m3u = get(urlm3u, allow_redirects=True)
			urlm3u = str(hostport) + '/get.php?username=' + str(user) + '&password=' + str(password) + '&type=m3u_plus&output=ts'
			header = {"User-Agent": "Enigma2 - IPToSAT Plugin"}
			request = Request(urlm3u, headers=header)
			try:
				response = urlopen(request, timeout=5)
			except Exception:
				try:
					response = urlopen(request, timeout=75)
				except Exception as err:
					with open(CATEGORIES_TIMER_ERROR, "w") as fw:
						fw.write(str(err))
		if wake - now < 60 and config.plugins.IPToSAT.autotimerbouquets.value:
			if exists(str(CATEGORIES_TIMER_ERROR)):
				remove(CATEGORIES_TIMER_ERROR)
			if exists(str(CATEGORIES_TIMER_OK)):
				remove(CATEGORIES_TIMER_OK)
			try:
				if response:
					m3u = response.read()
				if config.plugins.IPToSAT.deletecategories.value and m3u:
					for bouquets_iptosat_norhap in [x for x in listdir(ENIGMA2_PATH) if "iptosat_norhap" in x]:
						with open(BOUQUETS_TV, "r") as fr:
							bouquetread = fr.readlines()
							with open(BOUQUETS_TV, "w") as bouquetswrite:
								for line in bouquetread:
									if "iptosat_norhap" not in line:
										bouquetswrite.write(line)
						enigma2files = join(ENIGMA2_PATH, bouquets_iptosat_norhap)
						if enigma2files:
							remove(enigma2files)
				AssignService.checkStorageDevice(self)
				if not fileContains(CONFIG_PATH_CATEGORIES, "null") and fileContains(CONFIG_PATH_CATEGORIES, ":") and m3u:
					with open(READ_M3U, "wb") as m3ufile:
						m3ufile.write(m3u)  # m3ufile.write(m3u.content) with get
					with open(READ_M3U, "r") as m3uread:
						charactertoreplace = m3uread.readlines()
						sleep(3)
						with open(READ_M3U, "w") as m3uw:
							for line in charactertoreplace:
								if '[' in line and ']' in line and '|' in line:
									line = line.replace('[', '').replace(']', '|')
								if '|  ' in line:
									line = line.replace('|  ', '| ')
								m3uw.write(line)
					move(READ_M3U, str(self.m3ufile))
					if exists(str(BUILDBOUQUETS_FILE)):
						move(BUILDBOUQUETS_FILE, BUILDBOUQUETS_SOURCE)
					sleep(3)
					with open(CATEGORIES_TIMER_OK, "w") as fw:
						now = datetime.now().strftime("%A %-d %B") + " " + language.get(lang, "170") + " " + datetime.now().strftime("%H:%M")
						fw.write(now)
					eConsoleAppContainer().execute('python ' + str(BUILDBOUQUETS_SOURCE) + " ; mv " + str(BOUQUET_IPTV_NORHAP) + ".del" + " " + str(BOUQUET_IPTV_NORHAP) + " ; wget -qO - http://127.0.0.1/web/servicelistreload?mode=2 ; wget -qO - http://127.0.0.1/web/servicelistreload?mode=2 ; rm -f " + str(self.m3ufile) + " ; mv " + str(BUILDBOUQUETS_SOURCE) + " " + str(BUILDBOUQUETS_FILE) + " ; echo 1 > /proc/sys/vm/drop_caches ; echo 2 > /proc/sys/vm/drop_caches ; echo 3 > /proc/sys/vm/drop_caches")
					if self.storage:
						eConsoleAppContainer().execute('rm -f ' + str(self.m3ustoragefile) + " ; cp " + str(self.m3ufile) + " " + str(self.m3ustoragefile))
				else:
					if m3u:
						with open(CATEGORIES_TIMER_ERROR, "w") as fw:
							fw.write(language.get(lang, "156"))
			except Exception as err:
				with open(CATEGORIES_TIMER_ERROR, "w") as fw:
					fw.write(str(err))

	def refreshScheduler(self):
		now = int(time())
		if config.plugins.IPToSAT.autotimerbouquets.value:
			if now > 1262304000:
				self.scheduledtime = self.prepareTimer()
			else:
				self.scheduledtime = 0
				self.iptosatpolltimer.start(36000)
		else:
			self.scheduledtime = 0
			self.iptosatpolltimer.stop()


class TimerOffCard:
	def __init__(self, session):
		self.session = session
		self.cardofftimer = eTimer()
		self.cardofftimer.callback.append(self.iptosatCardOffTimer)
		self.cardpolltimer = eTimer()
		self.cardpolltimer.timeout.get().append(self.cardPollTimer)
		self.refreshTimerCard()

	def cardPollTimer(self):
		self.cardpolltimer.stop()
		self.scheduledtime = self.prepareTimer()

	def getTimeOffCard(self):
		now = localtime()
		current_day = int(now.tm_wday)
		return int(mktime((now.tm_year, now.tm_mon, now.tm_mday, config.plugins.IPToSAT.timecardoff[current_day].value[0], config.plugins.IPToSAT.timecardoff[current_day].value[1], 0, now.tm_wday, now.tm_yday, now.tm_isdst)))

	def prepareTimer(self):
		self.cardofftimer.stop()
		cardofftime = self.getTimeOffCard()
		now = int(time())
		if cardofftime > 0:
			if cardofftime < now:
				cardofftime += 24 * 3600
				while (int(cardofftime) - 30) < now:
					cardofftime += 24 * 3600
			next = cardofftime - now
			self.cardofftimer.startLongTimer(next)
		else:
			cardofftime = -1
		return cardofftime

	def iptosatCardOffTimer(self):
		now = int(time())
		cardoff = self.getTimeOffCard()
		if cardoff - now < 60 and config.plugins.IPToSAT.cardday[day].value:
			if exists(FILES_TUXBOX + "/config/oscam/oscam.services") and exists(str(PLAYLIST_PATH)):
				if exists(ENIGMA2_PATH_LISTS + "iptosatjsonall"):
					move(PLAYLIST_PATH, ENIGMA2_PATH_LISTS + "iptosatjsoncard")
					move(ENIGMA2_PATH_LISTS + "iptosatjsonall", PLAYLIST_PATH)
					move(FILES_TUXBOX + "/config/oscam/oscam.services", FILES_TUXBOX + "/config/oscam/oscam.services.card")
					move(FILES_TUXBOX + "/config/oscam/oscam.services.no.card", FILES_TUXBOX + "/config/oscam/oscam.services")
					eConsoleAppContainer().execute("/etc/init.d/softcam.oscam restart")

	def refreshTimerCard(self):
		now = int(time())
		if now > 1262304000:
			self.scheduledtime = self.prepareTimer()
		else:
			self.scheduledtime = 0
			self.cardpolltimer.start(36000)


class TimerOnCard:
	def __init__(self, session):
		self.session = session
		self.cardontimer = eTimer()
		self.cardontimer.callback.append(self.iptosatCardOnTimer)
		self.cardpolltimer = eTimer()
		self.cardpolltimer.timeout.get().append(self.cardPollTimer)
		self.refreshTimerCard()

	def cardPollTimer(self):
		self.cardpolltimer.stop()
		self.scheduledtime = self.prepareTimer()

	def getTimeOnCard(self):
		now = localtime()
		current_day = int(now.tm_wday)
		return int(mktime((now.tm_year, now.tm_mon, now.tm_mday, config.plugins.IPToSAT.timecardon[current_day].value[0], config.plugins.IPToSAT.timecardon[current_day].value[1], 0, now.tm_wday, now.tm_yday, now.tm_isdst)))

	def prepareTimer(self):
		self.cardontimer.stop()
		cardofftime = self.getTimeOnCard()
		now = int(time())
		if cardofftime > 0:
			if cardofftime < now:
				cardofftime += 24 * 3600
				while (int(cardofftime) - 30) < now:
					cardofftime += 24 * 3600
			next = cardofftime - now
			self.cardontimer.startLongTimer(next)
		else:
			cardofftime = -1
		return cardofftime

	def iptosatCardOnTimer(self):
		now = int(time())
		cardon = self.getTimeOnCard()
		if cardon - now < 60 and config.plugins.IPToSAT.cardday[day].value:
			if exists(ENIGMA2_PATH_LISTS + "iptosatjsoncard"):
				move(PLAYLIST_PATH, ENIGMA2_PATH_LISTS + "iptosatjsonall")
				move(ENIGMA2_PATH_LISTS + "iptosatjsoncard", PLAYLIST_PATH)
				move(FILES_TUXBOX + "/config/oscam/oscam.services", FILES_TUXBOX + "/config/oscam/oscam.services.no.card")
				move(FILES_TUXBOX + "/config/oscam/oscam.services.card", FILES_TUXBOX + "/config/oscam/oscam.services")
				eConsoleAppContainer().execute("/etc/init.d/softcam.oscam restart")

	def refreshTimerCard(self):
		now = int(time())
		if now > 1262304000:
			self.scheduledtime = self.prepareTimer()
		else:
			self.scheduledtime = 0
			self.cardpolltimer.start(36000)


class IPToSAT(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
			iPlayableService.evStart: self.__evStart,
			iPlayableService.evTunedIn: self.__evStart,
			iPlayableService.evEnd: self.__evEnd,
			iPlayableService.evStopped: self.__evEnd,
		})
		self.Timer = eTimer()
		try:
			self.Timer.callback.append(self.get_channel)
		except Exception:
			self.Timer_conn = self.Timer.timeout.connect(self.get_channel)
		if BoxInfo.getItem("distro") == "norhap":
			if config.plugins.IPToSAT.cardday[day].value:
				self.timercardoff = TimerOffCard(self)  # timer cardoff init in restart enigma and reboot
				self.timercardon = TimerOnCard(self)  # timer cardon init in restart enigma and reboot
		if config.plugins.IPToSAT.autotimerbouquets.value:
			self.timercategories = TimerUpdateCategories(self)  # timer init in restart enigma and reboot
		self.container = eConsoleAppContainer()
		self.ip_sat = False

	def current_channel(self, channel, lastservice):
		playlist = getPlaylist()
		player = config.plugins.IPToSAT.player.value
		if channel and playlist and not self.ip_sat:
			for ch in playlist['playlist']:
				iptosat = ch['sref'] if 'sref' in ch else ch['channel'].strip()
				if channel == iptosat or iptosat == str(ServiceReference(lastservice)):
					self.session.nav.stopService()
					cmd = '{} "{}"'.format(player, ch['url'])
					self.container.execute(cmd)
					self.session.nav.playService(lastservice)
					self.ip_sat = True

	def get_channel(self):
		service = self.session.nav.getCurrentService()
		if service:
			info = service and service.info()
			if info:
				FeInfo = service and service.frontendInfo()
				if FeInfo:
					SNR = FeInfo.getFrontendInfo(iFrontendInformation.signalQuality) / 655
					isCrypted = info and info.getInfo(iServiceInformation.sIsCrypted)
					if isCrypted and SNR > 10:
						lastservice = self.session.nav.getCurrentlyPlayingServiceReference()
						channel_name = ServiceReference(lastservice).getServiceName()
						self.current_channel(channel_name, lastservice)
					else:
						if self.ip_sat:
							self.container.sendCtrlC()
							self.ip_sat = False

	def __evStart(self):
		self.Timer.start(1000)

	def __evEnd(self):
		self.Timer.stop()
		if self.ip_sat:
			self.container.sendCtrlC()
			self.ip_sat = False


class AssignService(ChannelSelectionBase):
	if screenWidth == 1920:
		skin = """
		<screen name="IPToSAT Service Assign" position="1,80" size="1920,1020" backgroundColor="#0023262f" title="IPToSAT Service Assign">
			<eLabel backgroundColor="#0044a2ff" position="0,0" size="1917,2"/>
			<eLabel backgroundColor="#0044a2ff" position="0,2" size="2,997"/>
			<eLabel backgroundColor="#0044a2ff" position="0,997" size="1917,2"/>
			<eLabel backgroundColor="#0044a2ff" position="1917,0" size="2,999"/>
			<eLabel backgroundColor="#0044a2ff" position="1274,2" size="1,400"/>
			<eLabel backgroundColor="#0044a2ff" position="1274,393" size="642,1" zPosition="10"/>
			<widget source="session.VideoPicture" render="Pig" position="1275,5" size="635,400" zPosition="1" backgroundColor="#df0b1300"/>
			<widget name="titleChannelsList" position="3,05" size="665,35" horizontalAlignment="center" verticalAlignment="center" foregroundColor="yellow" backgroundColor="#0023262f" zPosition="2" font="Regular;25" />
			<widget name="titleSuscriptionList" position="670,05" size="500,35" horizontalAlignment="center" verticalAlignment="center" foregroundColor="yellow" backgroundColor="#0023262f" zPosition="2" font="Regular;25" />
			<widget name="list" position="23,42" size="613,310" backgroundColor="#0023262f" scrollbarMode="showOnDemand" scrollbarForegroundColor="#0044a2ff" scrollbarBorderColor="#0044a2ff" />
			<widget name="list2" position="658,42" size="612,304" backgroundColor="#0023262f" scrollbarMode="showOnDemand" scrollbarForegroundColor="#0044a2ff" scrollbarBorderColor="#0044a2ff" />
			<widget name="please" position="680,42" size="590,35" font="Regular;24" backgroundColor="#0023262f" zPosition="12" />
			<widget name="status" position="33,394" size="870,355" font="Regular;24" backgroundColor="#0023262f" zPosition="10" />
			<widget name="description" position="925,394" size="990,565" font="Regular;24" backgroundColor="#0023262f" zPosition="6" />
			<widget name="assign" position="33,394" size="870,140" font="Regular;24" backgroundColor="#0023262f" zPosition="6" />
			<widget name="codestatus" position="33,500" size="870,249" font="Regular;24" backgroundColor="#0023262f" zPosition="10" />
			<widget name="helpbouquetepg" position="33,355" size="870,550" font="Regular;24" backgroundColor="#0023262f" zPosition="6" />
			<widget name="managerlistchannels" position="33,750" size="870,152" font="Regular;24" backgroundColor="#0023262f" zPosition="10" />
			<widget name="help" position="925,394" size="990,565" font="Regular;24" backgroundColor="#0023262f" zPosition="3" />
			<widget name="play" position="925,394" size="990,565" font="Regular;24" backgroundColor="#0023262f" zPosition="3" />
			<widget source="key_green" render="Label" objectTypes="key_green,StaticText" position="12,940" zPosition="2" size="165,57" backgroundColor="key_green" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text" />
			<widget source="key_blue" render="Label" objectTypes="key_blue,StaticText" position="189,940" zPosition="2" size="165,57" backgroundColor="key_blue" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text" />
			<widget source="key_red" conditional="key_red" render="Label" objectTypes="key_red,StaticText" position="365,940" zPosition="2" size="165,57" backgroundColor="key_red" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_yellow" conditional="key_yellow" render="Label" objectTypes="key_yellow,StaticText" position="541,940" zPosition="2" size="165,57" backgroundColor="key_yellow" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_epg" render="Label" conditional="key_epg" position="717,962" zPosition="4" size="165,35" backgroundColor="key_back" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_help" render="Label" conditional="key_help" position="893,962" zPosition="4" size="165,35" backgroundColor="key_back" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_play" render="Label" conditional="key_play" position="1069,962" zPosition="4" size="165,35" backgroundColor="key_back" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_volumeup" render="Label" conditional="key_volumeup" position="1245,962" zPosition="4" size="165,35" backgroundColor="key_back" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_volumedown" render="Label" conditional="key_volumedown" position="1421,962" zPosition="4" size="165,35" backgroundColor="key_back" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_stop" render="Label" conditional="key_stop" position="1597,962" zPosition="4" size="165,35" backgroundColor="key_back" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_0" render="Label" conditional="key_0" position="1772,962" zPosition="12" size="60,35" backgroundColor="key_back" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_tv" conditional="key_tv" render="Label" position="12,903" size="165,35" zPosition="12" backgroundColor="key_back" font="Regular;20" horizontalAlignment="center" verticalAlignment="center">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_audio" render="Label" conditional="key_audio" position="189,903" zPosition="12" size="165,35" backgroundColor="key_back" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_rec" render="Label" conditional="key_rec" position="365,903" zPosition="12" size="165,35" backgroundColor="key_back" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget name="HelpWindow" position="0,0" size="0,0" alphaTest="blend" conditional="HelpWindow" transparent="1" zPosition="+1" />
		</screen>"""
	else:
		skin = """
		<screen name="IPToSAT Service Assign" position="40,65" size="1200,625" title="IPToSAT Service Assign">
			<widget name="titleChannelsList" position="33,05" size="550,35" horizontalAlignment="center" verticalAlignment="center" foregroundColor="yellow" zPosition="2" font="Regular;25" />
			<widget name="titleSuscriptionList" position="600,05" size="550,35" horizontalAlignment="center" verticalAlignment="center" foregroundColor="yellow" zPosition="2" font="Regular;25" />
			<widget name="list" position="33,42" size="550,198" scrollbarMode="showOnDemand" />
			<widget name="list2" position="600,42" size="550,200" scrollbarMode="showOnDemand" />
			<widget name="please" position="600,42" size="540,35" font="Regular;18" zPosition="12" />
			<widget name="status" position="33,245" size="540,225" font="Regular;18" zPosition="11" />
			<widget name="description" position="600,245" size="595,320" font="Regular;18" zPosition="6" />
			<widget name="assign" position="33,245" size="540,100" font="Regular;18" zPosition="6" />
			<widget name="codestatus" position="33,330" size="540,150" font="Regular;18" zPosition="10" />
			<widget name="helpbouquetepg" position="33,245" size="540,318" font="Regular;17" zPosition="6" />
			<widget name="managerlistchannels" position="33,450" size="540,100" font="Regular;18" zPosition="10" />
			<widget name="help" position="600,245" size="595,322" font="Regular;17" zPosition="3" />
			<widget name="play" position="600,245" size="595,320" font="Regular;18" zPosition="3" />
			<widget source="key_green" render="Label" objectTypes="key_green,StaticText" position="12,588" zPosition="2" size="110,35" backgroundColor="key_green" font="Regular;16" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text" />
			<widget source="key_blue" render="Label" objectTypes="key_blue,StaticText" position="127,588" zPosition="2" size="110,35" backgroundColor="key_blue" font="Regular;16" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text" />
			<widget source="key_red" conditional="key_red" render="Label" objectTypes="key_red,StaticText" position="242,588" zPosition="2" size="110,35" backgroundColor="key_red" font="Regular;16" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_yellow" conditional="key_yellow" render="Label" objectTypes="key_yellow,StaticText" position="357,588" zPosition="2" size="110,35" backgroundColor="key_yellow" font="Regular;16" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_epg" render="Label" conditional="key_epg" position="472,588" zPosition="4" size="110,40" backgroundColor="key_back" font="Regular;18" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_help" render="Label" conditional="key_help" position="587,588" zPosition="4" size="110,40" backgroundColor="key_back" font="Regular;18" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_play" render="Label" conditional="key_play" position="702,588" zPosition="4" size="110,40" backgroundColor="key_back" font="Regular;18" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_volumeup" render="Label" conditional="key_volumeup" position="817,588" zPosition="4" size="110,40" backgroundColor="key_back" font="Regular;18" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_volumedown" render="Label" conditional="key_volumedown" position="932,588" zPosition="4" size="110,40" backgroundColor="key_back" font="Regular;18" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_stop" render="Label" conditional="key_stop" position="1047,588" zPosition="4" size="110,40" backgroundColor="key_back" font="Regular;18" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_0" render="Label" conditional="key_0" position="1162,588" zPosition="12" size="35,40" backgroundColor="key_back" font="Regular;18" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_tv" conditional="key_tv" render="Label" position="12,560" size="110,25" zPosition="12" backgroundColor="key_back" font="Regular;18" horizontalAlignment="center" verticalAlignment="center">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_audio" render="Label" conditional="key_audio" position="127,560" zPosition="12" size="110,25" backgroundColor="key_back" font="Regular;18" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_rec" render="Label" conditional="key_rec" position="242,560" zPosition="12" size="110,25" backgroundColor="key_back" font="Regular;18" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget name="HelpWindow" position="0,0" size="0,0" alphaTest="blend" conditional="HelpWindow" transparent="1" zPosition="+1" />
		</screen>"""

	def __init__(self, session, *args):
		self.session = session
		ChannelSelectionBase.__init__(self, session)
		self.bouquet_mark_edit = 0
		self.secondSuscription = False
		self.storage = False
		self.Console = Console()
		self.backupChannelsListStorage = False
		self.backupdirectory = None
		self.alternatefolder = None
		self.changefolder = None
		self.m3ufolder = None
		self.m3ufile = join(ENIGMA2_PATH, "iptosat_norhap.m3u")
		self.m3ustoragefile = None
		self.path = None
		self["titleChannelsList"] = Label(language.get(lang, "11"))
		self["titleSuscriptionList"] = Label()
		self["status"] = Label()
		self["please"] = Label()
		self["description"] = Label()
		self["assign"] = Label()
		self["codestatus"] = Label()
		self["managerlistchannels"] = Label()
		self["helpbouquetepg"] = Label()
		self["help"] = Label()
		self["play"] = Label()
		self["key_volumeup"] = StaticText("")
		self["key_volumedown"] = StaticText("")
		self["key_stop"] = StaticText("")
		self["key_green"] = StaticText(language.get(lang, "36"))
		self["key_blue"] = StaticText(language.get(lang, "37"))
		self["key_yellow"] = StaticText("")
		self["key_red"] = StaticText("")
		self["key_epg"] = StaticText("EPG")
		self["key_help"] = StaticText("HELP")
		self["key_play"] = StaticText("PLAY")
		self["key_tv"] = StaticText("")
		self["key_rec"] = StaticText("")
		self["key_audio"] = StaticText("")
		self["key_0"] = StaticText("")
		self.checkStorageDevice()
		self["ChannelSelectBaseActions"] = ActionMap(["IPToSATAsignActions"],
		{
			"cancel": self.exit,
			"back": self.exit,
			"ok": self.channelSelected,
			"2": self.channelSelectedForce,
			"left": self.left,
			"right": self.right,
			"down": self.moveDown,
			"up": self.moveUp,
			"green": self.showSatellites,
			"epg": self.setEPGChannel,
			"yellow": self.createBouquetIPTV,
			"blue": self.showFavourites,
			"nextBouquet": self.chUP,
			"prevBouquet": self.chDOWN,
			"help": self.showHelpEPG,
			"play": self.showHelpChangeList,
			"volumeUp": self.toggleSecondList,
			"volumeDown": self.setChangeList,
			"stop": self.purge,
			"showTv": self.backupChannelsList,
			"audio": self.deleteChannelsList,
			"rec": self.installChannelsList,
			"red": self.installBouquetIPToSATEPG,
			"0": self.searchBouquetIPTV,
		}, -2)
		self.errortimer = eTimer()
		if not fileContains(CONFIG_PATH, "pass") and not fileContains(CONFIG_PATH, "domain"):
			self["key_yellow"].setText(language.get(lang, "32"))
		if self.backupChannelsListStorage:
			self["key_rec"].setText("REC")
		if self.storage and not fileContains(CONFIG_PATH, "pass"):
			self["key_tv"].setText("TV")
			self["description"].setText(language.get(lang, "60"))
		elif self.storage and fileContains(CONFIG_PATH, "pass"):
			self["key_tv"].setText("TV")
			self["description"].setText(language.get(lang, "78"))
		else:
			self["description"] = Label(language.get(lang, "0"))
		try:
			self.errortimer.callback.append(self.errorMessage)
		except Exception:
			self.errortimer_conn = self.errortimer.timeout.connect(self.errorMessage)
		self.in_bouquets = False
		self.in_channels = False
		self.url = None
		self.channels = []
		self.categories = []
		self['list2'] = MenuList([])
		self.selectedList = self["list"]
		self.getUserData()
		self.onLayoutFinish.append(self.setModeTv)
		self.onShown.append(self.onWindowShow)

	def checkStorageDevice(self):
		try:
			if not exists(CONFIG_PATH):
				with open(CONFIG_PATH, 'w') as fw:
					fw.write("[IPToSAT]" + "\n" + 'Host=http://domain:port' + "\n" + "User=user" + "\n" + "Pass=pass")
			for partition in harddiskmanager.getMountedPartitions():
				self.path = normpath(partition.mountpoint)
				if self.path != "/" and "net" not in self.path and "autofs" not in self.path:
					if exists(str(self.path)) and listdir(self.path):
						self.storage = True
						self.backupdirectory = join(self.path, f"IPToSAT/{MODEL}/BackupChannelsList")
						self.alternatefolder = join(self.path, f"IPToSAT/{MODEL}/AlternateList")
						self.changefolder = join(self.path, f"IPToSAT/{MODEL}/ChangeSuscriptionList")
						self.m3ufolder = join(self.path, f"IPToSAT/{MODEL}/M3U")
						self.m3ustoragefile = join(self.m3ufolder, "iptosat_norhap.m3u")
						backupfiles = ""
						bouquetiptosatepg = ""
						if exists(str(BUILDBOUQUETS_SOURCE)):
							move(BUILDBOUQUETS_SOURCE, BUILDBOUQUETS_FILE)
						for files in [x for x in listdir(self.backupdirectory) if x.endswith(".tv")]:
							backupfiles = join(self.backupdirectory, files)
							bouquetiptosatepg = join(self.backupdirectory, FILE_IPToSAT_EPG)
							if backupfiles:
								self["key_audio"].setText("AUDIO")
								self.backupChannelsListStorage = True
							if exists(str(bouquetiptosatepg)):
								self["key_red"].setText(language.get(lang, "18"))
		except Exception as err:
			print("ERROR: %s" % str(err))

	def showHelpChangeList(self):
		if self.storage:
			self["play"].setText(language.get(lang, "58"))
		else:
			self["play"].setText(language.get(lang, "61"))
			self["key_volumeup"] = StaticText("")
			self["key_volumedown"] = StaticText("")
			self["key_stop"] = StaticText("")
		self['managerlistchannels'].hide()
		self["key_0"].setText("")
		self["description"].hide()
		self["help"].hide()
		self["helpbouquetepg"].hide()
		self["play"].show()
		self["key_volumeup"].setText(language.get(lang, "39"))
		self["key_volumedown"].setText(language.get(lang, "47"))
		self["key_stop"].setText(language.get(lang, "51"))

	def showHelpEPG(self):
		epghelp = language.get(lang, "9")
		#  helpbouquetepg = language.get(lang, "74")
		self["description"].hide()
		#  self["key_0"].setText("0")
		self["play"].hide()
		self["help"].setText(epghelp)
		self["help"].show()
		self["help"].setText(epghelp)
		self["helpbouquetepg"].show()
		#  self["helpbouquetepg"].setText(helpbouquetepg)
		self["assign"].hide()
		self["codestatus"].hide()
		self["status"].hide()

	def onWindowShow(self):
		self.onShown.remove(self.onWindowShow)
		try:
			self.disablelist2()
		except Exception:
			pass

	def setModeTv(self):
		self.setTvMode()
		self.showFavourites()
		self.buildTitleString()

	def buildTitleString(self):
		titleStr = self.getTitle().replace('IPToSAT - ', '')
		pos = titleStr.find(']')
		if pos == -1:
			pos = titleStr.find(')')
		if pos != -1:
			titleStr = titleStr[:pos + 1]
			Len = len(self.servicePath)
			if Len > 0:
				base_ref = self.servicePath[0]
				if Len > 1:
					end_ref = self.servicePath[Len - 1]
				else:
					end_ref = None
				nameStr = self.getServiceName(base_ref)
				titleStr += ' - ' + nameStr
				if end_ref is not None:
					if Len > 2:
						titleStr += '/../'
					else:
						titleStr += '/'
					nameStr = self.getServiceName(end_ref)
					titleStr += nameStr
				self.setTitle('IPToSAT - ' + titleStr)

	def chUP(self):
		if self.selectedList == self["list"]:
			self.servicelist.instance.moveSelection(self.servicelist.instance.pageDown)

	def chDOWN(self):
		if self.selectedList == self["list"]:
			self.servicelist.instance.moveSelection(self.servicelist.instance.pageUp)

	def enablelist1(self):
		instance = self["list"].instance
		instance.setSelectionEnable(1)

	def enablelist2(self):
		instance = self["list2"].instance
		instance.setSelectionEnable(1)

	def disablelist1(self):
		instance = self["list"].instance
		instance.setSelectionEnable(0)

	def disablelist2(self):
		instance = self["list2"].instance
		instance.setSelectionEnable(0)

	def left(self):
		if self.selectedList == self["list2"]:
			self.selectedList = self["list"]
			self.enablelist1()
			self.disablelist2()
		self.resetWidget()
		self["play"].hide()
		self["help"].hide()
		self["key_volumeup"].setText("")
		self["key_volumedown"].setText("")
		self["key_0"].setText("")
		self["key_stop"].setText("")
		self["helpbouquetepg"].hide()
		self['managerlistchannels'].hide()
		if not fileContains(CONFIG_PATH, "pass"):
			self["description"].show()
			self["codestatus"].show()
		else:
			self["status"].show()

	def right(self):
		if self.selectedList.getCurrent():
			self.selectedList = self["list2"]
			self.enablelist2()
		self.resetWidget()

	def moveDown(self):
		if self.selectedList.getCurrent():
			instance = self.selectedList.instance
			instance.moveSelection(instance.moveDown)
		self.resetWidget()

	def moveUp(self):
		if self.selectedList.getCurrent():
			instance = self.selectedList.instance
			instance.moveSelection(instance.moveUp)
		self.resetWidget()

	def getUserData(self):
		if not self.secondSuscription:
			self["titleSuscriptionList"].setText(language.get(lang, "12"))
		else:
			self["titleSuscriptionList"].setText(language.get(lang, "44"))
		if not fileContains(CONFIG_PATH, "pass") and self.storage:
			self["status"].hide()
			self["description"].setText(language.get(lang, "60"))
		if fileContains(CONFIG_PATH, "pass") and not self.storage:
			self["status"].show()
			self["status"].setText(language.get(lang, "72"))
			self["description"].hide()
			self["codestatus"].hide()
		if fileExists(CONFIG_PATH):
			try:
				with open(CONFIG_PATH, "r") as fr:
					xtream = fr.read()
					self.host = xtream.split()[1].split('Host=')[1]
					self.user = xtream.split()[2].split('User=')[1]
					self.password = xtream.split()[3].split('Pass=')[1]
					self.url = '{}/player_api.php?username={}&password={}'.format(self.host, self.user, self.password)
					self.getCategories(self.url)
					self.getUserSuscription(self.url)
			except Exception:
				trace_error()
				self.errortimer.start(200, True)
		else:
			log('%s, No such file or directory' % CONFIG_PATH)
			self.close(True)

	def errorMessage(self):
		self.session.openWithCallback(self.exit, MessageBox, language.get(lang, "19"), MessageBox.TYPE_ERROR, timeout=10)

	def getCategories(self, url):
		if config.plugins.IPToSAT.typecategories.value not in ("all", "none"):
			url += f'&action=get_{config.plugins.IPToSAT.typecategories.value}_categories'
		else:
			url += '&action=get_live_categories'
		self.callAPI(url, self.getData)

	def getUserSuscription(self, url):
		self.suscription(url, self.getSuscriptionData)

	def channelSelected(self):
		if config.plugins.IPToSAT.typecategories.value in ("vod", "series"):
			self['managerlistchannels'].show()
			self.assignWidgetScript("#00ff2525", config.plugins.IPToSAT.typecategories.value.upper() + "  " + language.get(lang, "154"))
		else:
			self["codestatus"].hide()
			if self.selectedList == self["list"]:
				ref = self.getCurrentSelection()
				if (ref.flags & 7) == 7:
					self.enterPath(ref)
					self.in_bouquets = True
			elif self.selectedList == self["list2"]:
				if self.url and not self.in_channels and len(self.categories) > 0:
					index = self['list2'].getSelectionIndex()
					cat_id = self.categories[index][1]
					url = self.url
					url += '&action=get_live_streams&category_id=' + cat_id
					self.callAPI(url, self.getChannels)
				elif self.in_channels and len(self.channels) > 0:
					index = self['list2'].getSelectionIndex()
					xtream_channel = self.channels[index][0]
					stream_id = self.channels[index][1]
					sref = self.getSref()
					channel_name = ServiceReference(sref).getServiceName()
					self.addChannel(channel_name, stream_id, sref, xtream_channel)

	def channelSelectedForce(self):
		if config.plugins.IPToSAT.typecategories.value in ("vod", "series"):
			self['managerlistchannels'].show()
			self.assignWidgetScript("#00ff2525", config.plugins.IPToSAT.typecategories.value.upper() + "  " + language.get(lang, "154"))
		else:
			self["codestatus"].hide()
			if self.selectedList == self["list"]:
				ref = self.getCurrentSelection()
				if (ref.flags & 7) == 7:
					self.enterPath(ref)
					self.in_bouquets = True
			elif self.selectedList == self["list2"]:
				if self.url and not self.in_channels and len(self.categories) > 0:
					index = self['list2'].getSelectionIndex()
					cat_id = self.categories[index][1]
					url = self.url
					url += '&action=get_live_streams&category_id=' + cat_id
					self.callAPI(url, self.getChannelsForce)
				elif self.in_channels and len(self.channels) > 0:
					index = self['list2'].getSelectionIndex()
					xtream_channel = self.channels[index][0]
					stream_id = self.channels[index][1]
					sref = self.getSref()
					channel_name = ServiceReference(sref).getServiceName()
					self.addChannel(channel_name, stream_id, sref, xtream_channel)

	def addChannel(self, channel_name, stream_id, sref, xtream_channel):
		if exists(FILES_TUXBOX + "/config/oscam/oscam.services.no.card"):
			self['managerlistchannels'].show()
			self.assignWidgetScript("#e5e619", language.get(lang, "196"))
		playlist = getPlaylist()
		if playlist:
			if sref.startswith('1') and 'http' not in sref:
				url = self.host + '/' + self.user + '/' + self.password + '/' + stream_id
				if not fileContains(PLAYLIST_PATH, sref) and "FROM BOUQUET" not in sref:
					from unicodedata import normalize
					playlist['playlist'].append({'sref': sref, 'channel': normalize('NFKD', channel_name).encode('ascii', 'ignore').decode(), 'url': url})
					with open(PLAYLIST_PATH, 'w') as f:
						dump(playlist, f, indent=4)
					if fileContains(PLAYLIST_PATH, sref):
						text = (channel_name + " " + language.get(lang, "21") + " " + xtream_channel)
						self.assignWidget("#86dc3d", text)
				else:
					if "FROM BOUQUET" in sref:
						text = (channel_name + " " + language.get(lang, "142"))
						self.assignWidget("#00ff2525", text)
					else:
						reference = sref[7:11] if ":" not in sref[7:11] else sref[6:10]
						text = (channel_name + " " + language.get(lang, "20") + "  " + reference)
						self.assignWidget("#00ff2525", text)
			else:
				text = (language.get(lang, "23"))
				self.assignWidget("#00ff2525", text)
		else:
			text = (language.get(lang, "22"))
			self.assignWidget("#00ff2525", text)

	def restarGUI(self, answer):
		if answer:
			self.session.open(TryQuitMainloop, 3)
		else:
			self.channelSelected()

	def doinstallBouquetIPToSATEPG(self, answer):
		if answer:
			try:
				IPToSAT_EPG = join(self.backupdirectory, FILE_IPToSAT_EPG)
				if not fileContains(BOUQUETS_TV, "iptosat_epg"):
					with open(WILD_CARD_BOUQUETSTV, "a") as newbouquetstvwrite:
						newbouquetstvwrite.write('#NAME User - Bouquets (TV)' + "\n" + '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET' + " " + '"' + FILE_IPToSAT_EPG + '"' + " " 'ORDER BY bouquet' + '\n')
						with open(BOUQUETS_TV, "r") as bouquetstvread:
							bouquetstvread = bouquetstvread.readlines()
							for linesbouquet in bouquetstvread:
								if "#NAME User - Bouquets (TV)" not in linesbouquet:
									newbouquetstvwrite.write(linesbouquet)
					move(WILD_CARD_BOUQUETSTV, BOUQUETS_TV)
					copy(IPToSAT_EPG, ENIGMA2_PATH)
					eConsoleAppContainer().execute('wget -qO - http://127.0.0.1/web/servicelistreload?mode=2 ; wget -qO - http://127.0.0.1/web/servicelistreload?mode=2')
					self.session.open(MessageBox, "Bouquet" + " " + FILE_IPToSAT_EPG.replace("userbouquet.", "").replace(".tv", "").upper() + " " + language.get(lang, "80"), MessageBox.TYPE_INFO, simple=True, timeout=5)
				else:
					self.session.open(MessageBox, FILE_IPToSAT_EPG.replace("userbouquet.", "").replace(".tv", "").upper() + " " + language.get(lang, "82"), MessageBox.TYPE_INFO)
			except Exception as err:
				self.session.open(MessageBox, "ERROR: %s" % str(err), MessageBox.TYPE_ERROR, default=False, timeout=10)

	def installBouquetIPToSATEPG(self):
		if self.storage:
			try:
				IPToSAT_EPG = ""
				for file in [x for x in listdir(self.backupdirectory) if FILE_IPToSAT_EPG in x]:
					IPToSAT_EPG = join(self.backupdirectory, file)
				if IPToSAT_EPG:
					self.session.openWithCallback(self.doinstallBouquetIPToSATEPG, MessageBox, language.get(lang, "79") + "\n\n" + FILE_IPToSAT_EPG.replace("userbouquet.", "").replace(".tv", "").upper(), MessageBox.TYPE_YESNO)
				else:
					self.session.open(MessageBox, language.get(lang, "81") + " " + FILE_IPToSAT_EPG.replace("userbouquet.", "").replace(".tv", "").upper() + "\n\n" + self.backupdirectory + "/", MessageBox.TYPE_ERROR, timeout=10)
			except Exception as err:
				print("ERROR: %s" % str(err))

	def doinstallChannelsList(self, answer):
		try:
			backupfilesenigma = ""
			enigma2files = ""
			tuxboxfiles = ""
			backupfilestuxbox = ""
			if answer:
				self.session.open(MessageBox, language.get(lang, "77"), MessageBox.TYPE_INFO, simple=True)
				for filesenigma2 in [x for x in listdir(self.backupdirectory) if "alternatives." in x or "whitelist" in x or "lamedb" in x or "iptosat.conf" in x or "iptosat.json" in x or "iptosatjsonall" in x or "iptosatjsoncard" in x or "iptosatcategories.json" in x or "iptosatreferences" in x or "iptosatyourcatall" in x or x.endswith(".radio") or x.endswith(".tv") or "blacklist" in x]:
					backupfilesenigma = join(self.backupdirectory, filesenigma2)
					if backupfilesenigma:
						for fileschannelslist in [x for x in listdir(ENIGMA2_PATH) if "alternatives." in x or "whitelist" in x or "lamedb" in x or x.startswith("iptosat.conf") or x.startswith("iptosat.json") or "iptosatjsonall" in x or "iptosatjsoncard" in x or x.startswith("iptosatcategories.json") or x.startswith("iptosatreferences") or "iptosatyourcatall" in x or ".radio" in x or ".tv" in x or "blacklist" in x or "iptv.sh" in x]:
							enigma2files = join(ENIGMA2_PATH, fileschannelslist)
							if enigma2files:
								remove(enigma2files)
				for filestuxbox in [x for x in listdir(self.backupdirectory) if ".xml" in x]:
					backupfilestuxbox = join(self.backupdirectory, filestuxbox)
					if backupfilestuxbox:
						for fileschannelslist in [x for x in listdir(FILES_TUXBOX) if ".xml" in x and "timezone.xml" not in x]:
							tuxboxfiles = join(FILES_TUXBOX, fileschannelslist)
							if tuxboxfiles:
								remove(tuxboxfiles)
				eConsoleAppContainer().execute('init 4 && sleep 5 && cp -a ' + self.backupdirectory + '/' + '*' + ' ' + ENIGMA2_PATH_LISTS + ' ; mv ' + ENIGMA2_PATH_LISTS + 'cables.xml ' + FILES_TUXBOX + '/ ; mv ' + ENIGMA2_PATH_LISTS + 'atsc.xml ' + FILES_TUXBOX + '/ ; mv ' + ENIGMA2_PATH_LISTS + 'terrestrial.xml ' + FILES_TUXBOX + '/ ; mv ' + ENIGMA2_PATH_LISTS + 'satellites.xml ' + FILES_TUXBOX + '/ ; init 3')
		except Exception as err:
			self.session.open(MessageBox, "ERROR: %s" % str(err), MessageBox.TYPE_ERROR, default=False, timeout=10)

	def installChannelsList(self):
		if self.storage:
			try:
				backupfiles = ""
				for files in [x for x in listdir(self.backupdirectory) if "alternatives." in x or "whitelist" in x or "lamedb" in x or "iptosat.conf" in x or "iptosat.json" in x or "iptosatjsonall" in x or "iptosatjsoncard" in x or "iptosatcategories.json" in x or "iptosatreferences" in x or "iptosatyourcatall" in x or x.endswith(".radio") or x.endswith(".tv") or "blacklist" in x or "settings" in x or ".xml" in x]:
					backupfiles = join(self.backupdirectory, files)
					if backupfiles:
						self.session.openWithCallback(self.doinstallChannelsList, MessageBox, language.get(lang, "71"), MessageBox.TYPE_YESNO)
						break
					else:
						self.session.open(MessageBox, language.get(lang, "70"), MessageBox.TYPE_ERROR, default=False, timeout=10)
						break
			except Exception as err:
				print("ERROR: %s" % str(err))

	def doDeleteChannelsList(self, answer):
		try:
			backupfiles = ""
			if answer:
				for files in [x for x in listdir(self.backupdirectory) if "alternatives." in x or "whitelist" in x or "lamedb" in x or ".xml" in x or "iptosat.conf" in x or "iptosat.json" in x or "iptosatjsonall" in x or "iptosatjsoncard" in x or "iptosatcategories.json" in x or "iptosatreferences" in x or "iptosatyourcatall" in x or x.endswith(".radio") or x.endswith(".tv") or "blacklist" in x or "settings" in x]:
					backupfiles = join(self.backupdirectory, files)
					remove(backupfiles)
					self['managerlistchannels'].show()
					self.assignWidgetScript("#86dc3d", language.get(lang, "68"))
					if fileContains(CONFIG_PATH, "pass"):
						self["status"].show()
					self["key_rec"].setText("")
					self["key_audio"].setText("")
					self["key_red"].setText("")
		except Exception as err:
			print("ERROR: %s" % str(err))

	def deleteChannelsList(self):
		if self.storage:
			try:
				backupfiles = ""
				for files in [x for x in listdir(self.backupdirectory) if x.endswith(".radio") or x.endswith(".tv")]:
					backupfiles = join(self.backupdirectory, files)
					if backupfiles:
						self.session.openWithCallback(self.doDeleteChannelsList, MessageBox, language.get(lang, "67"), MessageBox.TYPE_YESNO)
						break
			except Exception as err:
				print("ERROR: %s" % str(err))

	def dobackupChannelsList(self, answer):
		try:
			backupfiles = ""
			enigma2files = ""
			bouquetiptosatepg = ""
			tuxboxfiles = ""
			if answer:
				for files in [x for x in listdir(self.backupdirectory) if "alternatives." in x or "whitelist" in x or "lamedb" in x or "iptosat.conf" in x or "iptosat.json" in x or "iptosatjsonall" in x or "iptosatjsoncard" in x or "iptosatcategories.json" in x or "iptosatreferences" in x or "iptosatyourcatall" in x or x.endswith(".radio") or x.endswith(".tv") or "blacklist" in x or "settings" in x]:
					backupfiles = join(self.backupdirectory, files)
					remove(backupfiles)
				for fileschannelslist in [x for x in listdir(ENIGMA2_PATH) if "alternatives." in x or "whitelist" in x or "lamedb" in x or x.endswith("iptosat.conf") or x.endswith("iptosat.json") or "iptosatjsonall" in x or "iptosatjsoncard" in x or x.endswith("iptosatcategories.json") or x.endswith("iptosatreferences") or "iptosatyourcatall" in x or x.endswith(".radio") or x.endswith(".tv") or "blacklist" in x or "settings" in x]:
					enigma2files = join(ENIGMA2_PATH, fileschannelslist)
					if enigma2files:
						copy(enigma2files, self.backupdirectory)
				for files in [x for x in listdir(self.backupdirectory) if ".xml" in x]:
					backupfiles = join(self.backupdirectory, files)
					remove(backupfiles)
				for fileschannelslist in [x for x in listdir(FILES_TUXBOX) if ".xml" in x and "timezone.xml" not in x]:
					tuxboxfiles = join(FILES_TUXBOX, fileschannelslist)
					if tuxboxfiles:
						copy(tuxboxfiles, self.backupdirectory)
					if fileContains(CONFIG_PATH, "pass"):
						self["status"].show()
				self['managerlistchannels'].show()
				self.assignWidgetScript("#86dc3d", language.get(lang, "66"))
				self["key_rec"].setText("REC")
				self["key_audio"].setText("AUDIO")
				bouquetiptosatepg = join(self.backupdirectory, FILE_IPToSAT_EPG)
				if exists(str(bouquetiptosatepg)):
					self["key_red"].setText(language.get(lang, "18"))
			else:
				self.showFavourites()
		except Exception as err:
			print("ERROR: %s" % str(err))

	def backupChannelsList(self):
		if self.storage:
			try:
				backupfiles = ""
				if not exists(str(self.backupdirectory)):
					makedirs(self.backupdirectory)
				for backupfiles in [x for x in listdir(self.backupdirectory) if "alternatives." in x or "whitelist" in x or ".xml" in x or "lamedb" in x or x.endswith("iptosat.conf") or x.endswith("iptosat.json") or "iptosatjsonall" in x or "iptosatjsoncard" in x or x.endswith("iptosatcategories.json") or x.endswith("iptosatreferences") or "iptosatyourcatall" in x or x.endswith(".radio") or x.endswith(".tv") or "blacklist" in x or "settings" in x]:
					backupfiles = join(self.backupdirectory, backupfiles)
				if backupfiles:
					self.session.openWithCallback(self.dobackupChannelsList, MessageBox, language.get(lang, "63") + " " + self.backupdirectory + "/" + "\n\n" + language.get(lang, "64"), MessageBox.TYPE_YESNO)
				else:
					self.session.openWithCallback(self.dobackupChannelsList, MessageBox, language.get(lang, "65"), MessageBox.TYPE_YESNO)
			except Exception as err:
				print("ERROR: %s" % str(err))

	def createBouquetIPTV(self):
		if hasattr(self, "getSref"):
			sref = str(self.getSref())
			channel_name = str(ServiceReference(sref).getServiceName())
		if exists(str(BUILDBOUQUETS_FILE)):
			move(BUILDBOUQUETS_FILE, BUILDBOUQUETS_SOURCE)
		if exists(CONFIG_PATH) and not fileContains(CONFIG_PATH, "pass"):
			try:
				m3u = ""
				response = ""
				if not fileContains(CONFIG_PATH_CATEGORIES, "null") and fileContains(CONFIG_PATH_CATEGORIES, ":"):
					if exists(str(CATEGORIES_TIMER_ERROR)):
						remove(CATEGORIES_TIMER_ERROR)
					if exists(str(CATEGORIES_TIMER_OK)):
						remove(CATEGORIES_TIMER_OK)
					with open(REFERENCES_FILE, "a") as updatefile:
						if search(r'[áÁéÉíÍóÓúÚñÑM+m+.]', channel_name):
							channel_name = channel_name.replace(" ", "").replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U").replace("M+", "M").replace("MOVISTAR+", "M").replace("MOVISTAR", "M").replace("+", "").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("Ñ", "N").replace("movistar+", "m").replace("m+", "m").replace("movistar", "m").replace(".", "").encode('ascii', 'ignore').decode()
						if "iptosat" not in channel_name and not fileContains(REFERENCES_FILE, str(channel_name).lower()):
							if fileContains(REFERENCES_FILE, ":"):
								updatefile.write("\n" + str(channel_name).lower() + "-->" + str(sref) + "-->1")
							else:
								updatefile.write(str(channel_name).lower() + "-->" + str(sref) + "-->1")
					with open(CONFIG_PATH, "r") as fr:
						configfile = fr.read()
						hostport = configfile.split()[1].split("Host=")[1]
						user = configfile.split()[2].split('User=')[1]
						password = configfile.split()[3].split('Pass=')[1]
						urlm3u = str(hostport) + '/get.php?username=' + str(user) + '&password=' + str(password) + '&type=m3u_plus&output=ts'
						header = {"User-Agent": "Enigma2 - IPToSAT Plugin"}
						request = Request(urlm3u, headers=header)
						try:
							response = urlopen(request, timeout=5)
						except Exception:
							try:
								response = urlopen(request, timeout=75)
							except Exception:
								pass
						if response:
							m3u = response.read()
							if config.plugins.IPToSAT.deletecategories.value and m3u:
								for bouquets_iptosat_norhap in [x for x in listdir(ENIGMA2_PATH) if "iptosat_norhap" in x]:
									with open(BOUQUETS_TV, "r") as fr:
										bouquetread = fr.readlines()
										with open(BOUQUETS_TV, "w") as bouquetswrite:
											for line in bouquetread:
												if "iptosat_norhap" not in line:
													bouquetswrite.write(line)
									enigma2files = join(ENIGMA2_PATH, bouquets_iptosat_norhap)
									if enigma2files:
										remove(enigma2files)
							if m3u:
								with open(READ_M3U, "wb") as m3ufile:
									m3ufile.write(m3u)
								with open(READ_M3U, "r") as m3uread:
									charactertoreplace = m3uread.readlines()
									sleep(3)
									with open(READ_M3U, "w") as m3uw:
										for line in charactertoreplace:
											if '[' in line and ']' in line and '|' in line:
												line = line.replace('[', '').replace(']', '|')
											if '|  ' in line:
												line = line.replace('|  ', '| ')
											m3uw.write(line)
								move(READ_M3U, str(self.m3ufile))
								if exists(str(BUILDBOUQUETS_FILE)):
									move(BUILDBOUQUETS_FILE, BUILDBOUQUETS_SOURCE)
								sleep(3)
								eConsoleAppContainer().execute('python ' + str(BUILDBOUQUETS_SOURCE) + " ; mv " + str(BOUQUET_IPTV_NORHAP) + ".del" + " " + str(BOUQUET_IPTV_NORHAP) + " ; wget -qO - http://127.0.0.1/web/servicelistreload?mode=2 ; wget -qO - http://127.0.0.1/web/servicelistreload?mode=2 ; rm -f " + str(self.m3ufile) + " ; mv " + str(BUILDBOUQUETS_SOURCE) + " " + str(BUILDBOUQUETS_FILE) + " ; echo 1 > /proc/sys/vm/drop_caches ; echo 2 > /proc/sys/vm/drop_caches ; echo 3 > /proc/sys/vm/drop_caches")
								if self.storage:
									eConsoleAppContainer().execute('rm -f ' + str(self.m3ustoragefile) + " ; cp " + str(self.m3ufile) + " " + str(self.m3ustoragefile))
								self["helpbouquetepg"].hide()
								self['managerlistchannels'].show()
								self.assignWidgetScript("#e5e619", language.get(lang, "5"))
								with open(CATEGORIES_TIMER_OK, "w") as fw:
									now = datetime.now().strftime("%A %-d %B") + " " + language.get(lang, "170") + " " + datetime.now().strftime("%H:%M")
									fw.write(now)
						else:
							self.assignWidgetScript("#00ff2525", language.get(lang, "6"))
				else:
					self.assignWidgetScript("#00ff2525", language.get(lang, "156"))
			except Exception as err:
				self.session.open(MessageBox, "ERROR: %s" % str(err), MessageBox.TYPE_ERROR, default=False)
		else:
			self.session.open(MessageBox, language.get(lang, "33"), MessageBox.TYPE_ERROR, default=False)

	def setEPGChannel(self):
		bouquetname = BOUQUET_IPTV_NORHAP
		if not exists(str(bouquetname)):
			self.createBouquetIPTV()
			return
		self['managerlistchannels'].hide()
		sref = str(self.getSref())
		channel_name = str(ServiceReference(sref).getServiceName())
		if self.selectedList == self["list"]:
			self.addEPGChannel(channel_name, sref, bouquetname)

	def searchBouquetIPTV(self):
		iptv_channels = False
		self['managerlistchannels'].hide()
		sref = str(self.getSref())
		channel_name = str(ServiceReference(sref).getServiceName())
		for filelist in [x for x in listdir(ENIGMA2_PATH) if x.endswith(".tv") or x.endswith(".radio")]:
			bouquetiptv = join(filelist)
			if fileContains(ENIGMA2_PATH_LISTS + bouquetiptv, channel_name) and fileContains(ENIGMA2_PATH_LISTS + bouquetiptv, "http"):
				self['managerlistchannels'].show()
				text = (ENIGMA2_PATH_LISTS + bouquetiptv)
				self.assignWidgetScript("#86dc3d", text)
				iptv_channels = True
				break
		if not iptv_channels:
			self['managerlistchannels'].show()
			text = (language.get(lang, "86"))
			self.assignWidgetScript("#00ff2525", text)
		self.showFavourites()

	def addEPGChannel(self, channel_name, sref, bouquetname):
		ref = self.getCurrentSelection()
		if (ref.flags & 7) == 7:  # this is bouquet selection no channel!!
			self.session.open(MessageBox, language.get(lang, "84"), MessageBox.TYPE_ERROR, simple=True, timeout=5)
		else:
			try:
				epg_channel_name = channel_name.upper()
				characterascii = [epg_channel_name]
				satreferencename = ""
				bouquetnamemsgbox = ""
				stream_iptv = ""
				bouquetiptosatepg = ""
				for character in characterascii:
					if not fileContains(bouquetname, ".ts") and not fileContains(bouquetname, ".m3u"):
						if search(r'[ÁÉÍÓÚÑ]', character):
							epg_channel_name = epg_channel_name.replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U").replace("Ñ", "N").encode('ascii', 'ignore').decode()
							break
					break
					if exists(IPToSAT_EPG_PATH) and fileContains(IPToSAT_EPG_PATH, epg_channel_name) and not fileContains(IPToSAT_EPG_PATH, sref.upper()) or search(r'[ÁÉÍÓÚÑ]', character) and not fileContains(IPToSAT_EPG_PATH, sref.upper()):  # remove old channel with sref old
						with open(IPToSAT_EPG_PATH, "r") as iptosat_epg_read:
							bouquetiptosatepg = iptosat_epg_read.readlines()
						with open(IPToSAT_EPG_PATH, "w") as iptosat_epg_write:
							for channel in bouquetiptosatepg:
								if epg_channel_name in channel and "http" in channel and "%3a " not in channel:  # replace reference old -> condition two points + channel_name
									changereference = channel.split("http")[1]
									channel = "#SERVICE " + sref + "http" + changereference
								if " FHD" not in epg_channel_name:
									if epg_channel_name not in channel and "%3a " not in channel or epg_channel_name + " " + "HD" not in channel and "%3a " not in channel or "#DESCRIPTION " + epg_channel_name not in channel and "#SERVICE" in channel and "HD" not in channel:
										iptosat_epg_write.write(channel)
								else:
									if epg_channel_name not in channel and "%3a " not in channel or epg_channel_name + " " + "HD" not in channel and "%3a " not in channel or "#DESCRIPTION " + epg_channel_name not in channel and "#SERVICE" in channel:
										iptosat_epg_write.write(channel)
						if fileContains(IPToSAT_EPG_PATH, sref.upper()):
							self.session.open(MessageBox, language.get(lang, "76") + " " + epg_channel_name, MessageBox.TYPE_INFO, simple=True)
				for filelist in [x for x in listdir(ENIGMA2_PATH) if x.endswith(".tv") or x.endswith(".radio")]:
					bouquetiptv = join(filelist)
					if fileContains(ENIGMA2_PATH_LISTS + bouquetiptv, ":" + epg_channel_name):
						with open(ENIGMA2_PATH_LISTS + bouquetiptv, "r") as fr:
							lines = fr.readlines()
							with open(WILD_CARD_EPG_FILE, "w") as fw:
								for line in lines:
									fw.write(line)
						if not fileContains(IPToSAT_EPG_PATH, ":" + epg_channel_name) and not fileContains(bouquetiptv, ":" + " " + epg_channel_name):
							with open(ENIGMA2_PATH_LISTS + bouquetiptv, "r") as file:
								for line in file:
									line = line.strip()
									ref = line.split('http')[0].replace("#SERVICE ", "")
									if "#NAME" in line:
										bouquetnamemsgbox = line.replace("#NAME ", "")
										namebouquet = line
									if ":" + epg_channel_name in line and "http" in line:
										sat_reference_name = line.replace(ref, self.getSref()).replace("::", ":").replace("0:" + epg_channel_name, "0").replace("C00000:0:0:0:00000:0:0:0", "C00000:0:0:0").replace("#DESCRIPT" + sref, "").replace("C00000:0:0:0:0000:0:0:0:0000:0:0:0:0000:0:0:0", "C00000:0:0:0").replace(":0000:0:0:0", "")
										satreferencename = sat_reference_name
						if "http" in str(satreferencename):
							with open(ENIGMA2_PATH_LISTS + bouquetiptv, "w") as fw:
								with open(WILD_CARD_EPG_FILE, "r") as fr:
									lineNAME = fr.readlines()
									for line in lineNAME:
										fw.write(line)
							if not fileContains(IPToSAT_EPG_PATH, sref.upper()):
								with open(ENIGMA2_PATH_LISTS + bouquetiptv, "w") as fw:
									fw.write(namebouquet + "\n" + satreferencename + "\n" + "#DESCRIPTION " + epg_channel_name + "\n")
								with open(IPToSAT_EPG_PATH, "a") as fw:
									if not fileContains(IPToSAT_EPG_PATH, '#NAME IPToSAT_EPG'):
										fw.write('#NAME IPToSAT_EPG' + "\n" + satreferencename + "\n" + "#DESCRIPTION " + epg_channel_name + "\n")
									else:
										fw.write(satreferencename + "\n" + "#DESCRIPTION " + epg_channel_name + "\n")
							with open(WILD_CARD_EPG_FILE, "r") as fr:
								with open(ENIGMA2_PATH_LISTS + bouquetiptv, "w") as fw:
									read_bouquetiptv = fr.readlines()
									for line in read_bouquetiptv:
										if epg_channel_name in line and "http" in line:
											fw.write(satreferencename + "\n".replace("\n", "").replace("\n", ""))  # init reference + description channel name
										if ":" + epg_channel_name not in line:
											fw.write(line)
							with open(ENIGMA2_PATH_LISTS + bouquetiptv, "r") as fr:  # new block reference + description channel name
								read_bouquetiptv = fr.readlines()
								with open(ENIGMA2_PATH_LISTS + bouquetiptv, "w") as fw:
									for line in read_bouquetiptv:
										if ":" + epg_channel_name in line:
											fw.write(line.replace(epg_channel_name + "#DESCRIPTION ", "") + "#DESCRIPTION " + epg_channel_name + "\n")
										if ":" + epg_channel_name not in line:
											fw.write(line)  # End TODO refererence + description channel name
							if not fileContains(BOUQUETS_TV, "iptosat_epg"):
								with open(WILD_CARD_BOUQUETSTV, "a") as newbouquetstvwrite:
									newbouquetstvwrite.write('#NAME User - Bouquets (TV)' + "\n" + '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET' + " " + '"' + FILE_IPToSAT_EPG + '"' + " " 'ORDER BY bouquet' + '\n')
									with open(BOUQUETS_TV, "r") as bouquetstvread:
										bouquetstvread = bouquetstvread.readlines()
										for linesbouquet in bouquetstvread:
											if "#NAME" not in linesbouquet:
												newbouquetstvwrite.write(linesbouquet)
								move(WILD_CARD_BOUQUETSTV, BOUQUETS_TV)
							eConsoleAppContainer().execute('wget -qO - http://127.0.0.1/web/servicelistreload?mode=2 ; wget -qO - http://127.0.0.1/web/servicelistreload?mode=2')
						if fileContains(IPToSAT_EPG_PATH, epg_channel_name) and fileContains(ENIGMA2_PATH_LISTS + bouquetiptv, epg_channel_name) and not fileContains(ENIGMA2_PATH_LISTS + bouquetiptv, epg_channel_name + "#SERVICE") and fileContains(IPToSAT_EPG_PATH, sref.upper()):
							self.session.open(MessageBox, language.get(lang, "24") + epg_channel_name + "\n\n" + language.get(lang, "75") + FILE_IPToSAT_EPG.replace("userbouquet.", "").replace(".tv", "").upper() + "\n\n" + bouquetnamemsgbox, MessageBox.TYPE_INFO, simple=True)
							break
				if exists(WILD_CARD_EPG_FILE):
					self.Console.ePopen("rm -f " + WILD_CARD_EPG_FILE)
				for filelist in [x for x in listdir(ENIGMA2_PATH) if x.endswith(".tv") or x.endswith(".radio")]:
					bouquets_categories = join(filelist)
					with open(ENIGMA2_PATH_LISTS + bouquets_categories, "r") as file:
						lines = file.readlines()
						for line in lines:
							for character in characterascii:
								if sref in line and "http" in line and ":" + epg_channel_name not in line:
									replacement = line.replace(".ts", ".ts" + ":" + epg_channel_name).replace(".m3u8", ".m3u8" + ":" + epg_channel_name).replace(".m3u", ".m3u" + ":" + epg_channel_name)  # add condition -> two points + channel_name for change old reference
									if ":" + epg_channel_name + ":" in replacement:  # remove one :channel_name (two channels name in bouquets_categories)
										if ".ts" in replacement:
											if search(r'[Á]', character):
												line = replacement.split(".ts:" + epg_channel_name)[0] + ".ts:" + epg_channel_name.replace("A", "Á") + "\n"
											if search(r'[É]', character):
												line = replacement.split(".ts:" + epg_channel_name)[0] + ".ts:" + epg_channel_name.replace("E", "É") + "\n"
											if search(r'[Í]', character):
												line = replacement.split(".ts:" + epg_channel_name)[0] + ".ts:" + epg_channel_name.replace("I", "Í") + "\n"
											if search(r'[Ó]', character):
												line = replacement.split(".ts:" + epg_channel_name)[0] + ".ts:" + epg_channel_name.replace("O", "Ó") + "\n"
											if search(r'[Ú]', character):
												line = replacement.split(".ts:" + epg_channel_name)[0] + ".ts:" + epg_channel_name.replace("U", "Ú") + "\n"
											if not search(r'[ÁÉÍÓÚ]', character):
												line = replacement.split(".ts:" + epg_channel_name)[0] + ".ts:" + epg_channel_name + "\n"
										elif ".m3u8" in replacement:
											if search(r'[Á]', character):
												line = replacement.split(".m3u8:" + epg_channel_name)[0] + ".m3u8:" + epg_channel_name.replace("A", "Á") + "\n"
											if search(r'[É]', character):
												line = replacement.split(".m3u8:" + epg_channel_name)[0] + ".m3u8:" + epg_channel_name.replace("E", "É") + "\n"
											if search(r'[Í]', character):
												line = replacement.split(".m3u8:" + epg_channel_name)[0] + ".m3u8:" + epg_channel_name.replace("I", "Í") + "\n"
											if search(r'[Ó]', character):
												line = replacement.split(".m3u8:" + epg_channel_name)[0] + ".m3u8:" + epg_channel_name.replace("O", "Ó") + "\n"
											if search(r'[Ú]', character):
												line = replacement.split(".m3u8:" + epg_channel_name)[0] + ".m3u8:" + epg_channel_name.replace("U", "Ú") + "\n"
											if not search(r'[ÁÉÍÓÚ]', character):
												line = replacement.split(".m3u8:" + epg_channel_name)[0] + ".m3u8:" + epg_channel_name + "\n"
										else:
											if search(r'[Á]', character):
												line = replacement.split(".m3u:" + epg_channel_name)[0] + ".m3u:" + epg_channel_name.replace("A", "Á") + "\n"
											if search(r'[É]', character):
												line = replacement.split(".m3u:" + epg_channel_name)[0] + ".m3u:" + epg_channel_name.replace("E", "É") + "\n"
											if search(r'[Í]', character):
												line = replacement.split(".m3u:" + epg_channel_name)[0] + ".m3u:" + epg_channel_name.replace("I", "Í") + "\n"
											if search(r'[Ó]', character):
												line = replacement.split(".m3u:" + epg_channel_name)[0] + ".m3u:" + epg_channel_name.replace("O", "Ó") + "\n"
											if search(r'[Ú]', character):
												line = replacement.split(".m3u:" + epg_channel_name)[0] + ".m3u:" + epg_channel_name.replace("U", "Ú") + "\n"
											if not search(r'[ÁÉÍÓÚ]', character):
												line = replacement.split(".m3u:" + epg_channel_name)[0] + ".m3u:" + epg_channel_name + "\n"
									else:
										line = replacement
								if sref in line and "http" in line:
									stream_iptv = line
				if stream_iptv and not fileContains(IPToSAT_EPG_PATH, epg_channel_name) and not fileContains(IPToSAT_EPG_PATH, sref.upper()):  # add stream IPTV with EPG to IPToSAT_EPG
					if not fileContains(IPToSAT_EPG_PATH, '#NAME IPToSAT_EPG'):
						with open(IPToSAT_EPG_PATH, "w") as fw:
							fw.write('#NAME IPToSAT_EPG' + "\n")
					else:
						for character in characterascii:
							with open(IPToSAT_EPG_PATH, "a") as fw:
								if search(r'[Á]', character):
									fw.write(stream_iptv + "#DESCRIPTION " + epg_channel_name.replace("A", "Á") + "\n")
								if search(r'[É]', character):
									fw.write(stream_iptv + "#DESCRIPTION " + epg_channel_name.replace("E", "É") + "\n")
								if search(r'[Í]', character):
									fw.write(stream_iptv + "#DESCRIPTION " + epg_channel_name.replace("I", "Í") + "\n")
								if search(r'[Ó]', character):
									fw.write(stream_iptv + "#DESCRIPTION " + epg_channel_name.replace("O", "Ó") + "\n")
								if search(r'[Ú]', character):
									fw.write(stream_iptv + "#DESCRIPTION " + epg_channel_name.replace("U", "Ú") + "\n")
								if not search(r'[ÁÉÍÓÚ]', character):
									fw.write(stream_iptv + "#DESCRIPTION " + epg_channel_name + "\n")
					if not fileContains(BOUQUETS_TV, "iptosat_epg"):
						with open(WILD_CARD_BOUQUETSTV, "a") as newbouquetstvwrite:
							newbouquetstvwrite.write('#NAME User - Bouquets (TV)' + "\n" + '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET' + " " + '"' + FILE_IPToSAT_EPG + '"' + " " 'ORDER BY bouquet' + '\n')
							with open(BOUQUETS_TV, "r") as bouquetstvread:
								bouquetstvread = bouquetstvread.readlines()
								for linesbouquet in bouquetstvread:
									if "#NAME" not in linesbouquet:
										newbouquetstvwrite.write(linesbouquet)
								move(WILD_CARD_BOUQUETSTV, BOUQUETS_TV)
					eConsoleAppContainer().execute('wget -qO - http://127.0.0.1/web/servicelistreload?mode=2 ; wget -qO - http://127.0.0.1/web/servicelistreload?mode=2')
			except Exception as err:
				print("ERROR: %s" % str(err))
			self.resultEditionBouquets(epg_channel_name, sref, bouquetname)

	def resultEditionBouquets(self, channel_name, sref, bouquetname):
		try:
			sref_update = sref.upper()
			characterascii = [channel_name]
			epg_channel_name = channel_name.upper()
			try:
				for character in characterascii:
					if search(r'[áÁéÉíÍóÓúÚñÑM+m+.]', channel_name):
						channel_name = character.replace(" ", "").replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U").replace("M+", "M").replace("MOVISTAR+", "M").replace("MOVISTAR", "M").replace("+", "").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("Ñ", "N").replace("movistar+", "m").replace("m+", "m").replace("movistar", "m").replace(".", "").encode('ascii', 'ignore').decode()
					if not fileContains(REFERENCES_FILE, channel_name.lower()):
						with open(REFERENCES_FILE, "a") as updatefile:
							updatefile.write("\n" + str(channel_name).lower() + "-->" + str(sref_update) + "-->1")
				with open(REFERENCES_FILE, "r") as file:  # clear old services references
					filereference = file.readlines()
					with open(REFERENCES_FILE, "w") as finalfile:
						for line in filereference:
							if ":" in line and "FROM BOUQUET" not in line:
								if str(channel_name).lower() + "." in line and str(sref_update) in line or str(channel_name).lower() in line and str(sref_update) in line or str(channel_name).lower() not in line and str(sref_update) not in line:
									finalfile.write(line)
			except Exception:
				pass
			if not fileContains(IPToSAT_EPG_PATH, "#SERVICE") and not fileContains(IPToSAT_EPG_PATH, "#NAME IPToSAT_EPG"):
				if fileContains(bouquetname, ".ts") or fileContains(bouquetname, ".m3u"):
					self.addEPGChannel(channel_name, sref)
			if fileContains(IPToSAT_EPG_PATH, epg_channel_name) and fileContains(IPToSAT_EPG_PATH, sref) or fileContains(IPToSAT_EPG_PATH, sref):
				self.session.open(MessageBox, language.get(lang, "24") + epg_channel_name + "\n\n" + language.get(lang, "94") + "\n\n" + FILE_IPToSAT_EPG.replace("userbouquet.", "").replace(".tv", "").upper(), MessageBox.TYPE_INFO, simple=True)
			if exists(BOUQUET_IPTV_NORHAP) and not fileContains(CONFIG_PATH, "pass") and fileContains(IPToSAT_EPG_PATH, "#SERVICE"):
				if not fileContains(IPToSAT_EPG_PATH, epg_channel_name) and not fileContains(IPToSAT_EPG_PATH, sref) and bouquetname:
					self.session.open(MessageBox, language.get(lang, "128") + " " + epg_channel_name + ":" + "\n" + bouquetname + "\n\n" + language.get(lang, "129") + "\n\n" + ":" + epg_channel_name + "\n\n" + language.get(lang, "124"), MessageBox.TYPE_ERROR)
				elif not fileContains(IPToSAT_EPG_PATH, epg_channel_name) and not fileContains(IPToSAT_EPG_PATH, sref):
					self.session.open(MessageBox, language.get(lang, "83") + " " + epg_channel_name + "\n\n" + language.get(lang, "93") + "\n\n" + ":" + epg_channel_name + "\n\n" + language.get(lang, "124"), MessageBox.TYPE_ERROR)
			else:
				if not fileContains(IPToSAT_EPG_PATH, ":" + epg_channel_name) and fileContains(IPToSAT_EPG_PATH, "#SERVICE"):
					if fileContains(bouquetname, ".ts") or fileContains(bouquetname, ".m3u"):
						self.session.open(MessageBox, language.get(lang, "85") + language.get(lang, "129") + "\n\n" + ":" + epg_channel_name, MessageBox.TYPE_ERROR)
				else:
					if not fileContains(bouquetname, ".ts") and not fileContains(bouquetname, ".m3u"):
						if not fileContains(IPToSAT_EPG_PATH, '#NAME IPToSAT_EPG'):
							with open(IPToSAT_EPG_PATH, "w") as fw:
								fw.write('#NAME IPToSAT_EPG' + "\n")
						self.session.open(MessageBox, language.get(lang, "132"), MessageBox.TYPE_ERROR, simple=True)
					else:
						self.session.open(MessageBox, language.get(lang, "131"), MessageBox.TYPE_ERROR, simple=True)
			if epg_channel_name == ".":  # it is not a valid channel
				self.session.open(MessageBox, language.get(lang, "125"), MessageBox.TYPE_ERROR)
		except Exception as err:
			print("ERROR: %s" % str(err))

	def purge(self):
		if self.storage:
			iptosatconf = join(self.alternatefolder, "iptosat.conf")
			iptosat2conf = join(self.changefolder, "iptosat.conf")
			iptosatjson = join(self.alternatefolder, "iptosat.json")
			iptosat2json = join(self.changefolder, "iptosat.json")
			if exists(str(iptosatconf)) or exists(str(iptosat2conf)) or exists(str(iptosatjson)) or exists(str(iptosat2json)):
				self.session.openWithCallback(self.purgeDeviceFiles, MessageBox, language.get(lang, "57"), MessageBox.TYPE_YESNO, default=False)
			else:
				self.session.open(MessageBox, language.get(lang, "43"), MessageBox.TYPE_INFO)

	def purgeDeviceFiles(self, answer):
		if answer:
			try:
				iptosatconf = join(self.alternatefolder, "iptosat.conf")
				iptosat2conf = join(self.changefolder, "iptosat.conf")
				iptosatjson = join(self.alternatefolder, "iptosat.json")
				iptosat2json = join(self.changefolder, "iptosat.json")
				if exists(str(iptosatconf)):
					remove(iptosatconf)
				if exists(str(iptosat2conf)):
					remove(iptosat2conf)
				if exists(str(iptosatjson)):
					remove(iptosatjson)
				if exists(str(iptosat2json)):
					remove(iptosat2json)
				if not exists(str(iptosatconf)) or not exists(str(iptosat2conf)) or not exists(str(iptosatjson)) or not exists(str(iptosat2json)):
					self.session.open(MessageBox, language.get(lang, "52"), MessageBox.TYPE_INFO)
			except Exception as err:
				print("ERROR: %s" % str(err))

	def toggleSecondList(self):
		if self.storage:
			self["helpbouquetepg"].hide()
			try:
				fileconf = join(ENIGMA2_PATH, "iptosat.conf")
				iptosat2conf = join(self.alternatefolder, "iptosat.conf")
				iptosatlist2conf = join(self.alternatefolder, "iptosat_LIST2.conf")
				iptosatlist1conf = join(self.alternatefolder, "iptosat_LIST1.conf")
				filejson = join(ENIGMA2_PATH, "iptosat.json")
				iptosat2json = join(self.alternatefolder, "iptosat.json")
				iptosatlist2json = join(self.alternatefolder, "iptosat_LIST2.json")
				iptosatlist1json = join(self.alternatefolder, "iptosat_LIST1.json")
				if config.plugins.IPToSAT.usercategories.value:
					config.plugins.IPToSAT.usercategories.value = False
					config.plugins.IPToSAT.usercategories.save()
				if config.plugins.IPToSAT.typecategories.value == "all":
					if exists(str(ALL_CATEGORIES)):
						remove(ALL_CATEGORIES)
					if exists(str(WILD_CARD_ALL_CATEGORIES)):
						remove(WILD_CARD_ALL_CATEGORIES)
					if exists(str(WILD_CARD_CATYOURLIST)):
						remove(WILD_CARD_CATYOURLIST)
					with open(CONFIG_PATH_CATEGORIES, 'w') as f:
						f.write("null")
				if exists(str(iptosat2conf)):
					if exists(str(iptosatlist2conf)) or exists(str(iptosatlist1conf)):
						remove(iptosat2conf)
				if exists(str(iptosat2json)):
					if exists(str(iptosatlist2json)) or exists(str(iptosatlist1json)):
						remove(iptosat2json)
				if not exists(str(self.alternatefolder)):
					makedirs(self.alternatefolder)
				if not exists(str(iptosat2conf)) and not exists(str(iptosatlist1conf)) and not exists(str(iptosatlist2conf)):
					self.session.open(MessageBox, language.get(lang, "40") + "\n\n" + self.alternatefolder + "/" + "\n\n" + language.get(lang, "208"), MessageBox.TYPE_INFO)
					return
				if not exists(str(iptosat2json)) and not exists(str(iptosatlist1json)) and not exists(str(iptosatlist2json)):
					self.session.open(MessageBox, language.get(lang, "206") + "\n\n" + language.get(lang, "207") + "\n\n" + self.alternatefolder + "/" + "\n\n" + language.get(lang, "208"), MessageBox.TYPE_INFO)
					return
				if BoxInfo.getItem("distro") == "norhap":
					if not exists(str(ENIGMA2_PATH_LISTS + "iptosatjsoncard")):
						self.session.open(MessageBox, language.get(lang, "209"), MessageBox.TYPE_INFO, simple=True)
						return
				if exists(CONFIG_PATH) and exists(str(iptosat2conf)):
					move(CONFIG_PATH, iptosatlist1conf)
					move(iptosat2conf, fileconf)
					self.secondSuscription = True
				elif exists(CONFIG_PATH) and exists(str(iptosatlist2conf)):
					move(CONFIG_PATH, iptosatlist1conf)
					move(iptosatlist2conf, fileconf)
					self.secondSuscription = True
				elif exists(CONFIG_PATH) and exists(str(iptosatlist1conf)):
					move(CONFIG_PATH, iptosatlist2conf)
					move(iptosatlist1conf, fileconf)
					self.secondSuscription = False
				if exists(PLAYLIST_PATH) and exists(str(iptosat2json)):
					move(PLAYLIST_PATH, iptosatlist1json)
					move(iptosat2json, filejson)
					self.secondSuscription = True
				elif exists(PLAYLIST_PATH) and exists(str(iptosatlist2json)):
					move(PLAYLIST_PATH, iptosatlist1json)
					move(iptosatlist2json, filejson)
					self.secondSuscription = True
				elif exists(PLAYLIST_PATH) and exists(str(iptosatlist1json)):
					move(PLAYLIST_PATH, iptosatlist2json)
					move(iptosatlist1json, filejson)
					self.secondSuscription = False
				else:
					if exists(str(iptosat2json)):  # user enters the iptosat.json file
						if exists(str(iptosatlist1conf)):
							move(iptosat2json, iptosatlist1json)
						if exists(str(iptosatlist2conf)):
							move(iptosat2json, iptosatlist2json)
						self.secondSuscription = False
				self.getUserData()
				if fileExists(CONFIG_PATH):
					with open(CONFIG_PATH, "r") as f:
						iptosatconfread = f.read()
						host = iptosatconfread.split()[1].split('Host=')[1].split(':')[1].replace("//", "http://") if not fileContains(CONFIG_PATH, "https") else iptosatconfread.split()[1].split('Host=')[1].split(':')[1].replace("//", "https://")
						port = iptosatconfread.split()[1].split(host)[1].replace(":", "")
						user = iptosatconfread.split()[2].split('User=')[1]
						password = iptosatconfread.split()[3].split('Pass=')[1]
						config.plugins.IPToSAT.domain.value = host
						config.plugins.IPToSAT.domain.save()
						config.plugins.IPToSAT.serverport.value = port if port != "port" else language.get(lang, "115")
						config.plugins.IPToSAT.serverport.save()
						config.plugins.IPToSAT.username.value = user
						config.plugins.IPToSAT.username.save()
						config.plugins.IPToSAT.password.value = password
						config.plugins.IPToSAT.password.save()
				self["codestatus"].hide()
			except Exception as err:
				print("ERROR: %s" % str(err))

	def doChangeList(self, answer):
		try:
			iptosatlist1conf = join(self.alternatefolder, "iptosat_LIST1.conf")
			iptosat2change = join(self.changefolder, "iptosat.conf")
			if answer:
				if exists(str(iptosat2change)):
					move(iptosat2change, iptosatlist1conf)
					if config.plugins.IPToSAT.typecategories.value == "all":
						if exists(str(ALL_CATEGORIES)):
							remove(ALL_CATEGORIES)
						if exists(str(WILD_CARD_ALL_CATEGORIES)):
							remove(WILD_CARD_ALL_CATEGORIES)
						if exists(str(WILD_CARD_CATYOURLIST)):
							remove(WILD_CARD_CATYOURLIST)
					else:
						if config.plugins.IPToSAT.usercategories.value:
							config.plugins.IPToSAT.usercategories.value = False
							config.plugins.IPToSAT.usercategories.save()
			else:
				self.session.open(MessageBox, language.get(lang, "46") + "\n\n" + language.get(lang, "42"), MessageBox.TYPE_INFO)
		except Exception as err:
			print("ERROR: %s" % str(err))
		self.toggleSecondList()

	def doChangeList2(self, answer):
		try:
			iptosatlist2conf = join(self.alternatefolder, "iptosat_LIST2.conf")
			iptosat2change = join(self.changefolder, "iptosat.conf")
			if answer:
				move(iptosat2change, iptosatlist2conf)
				if config.plugins.IPToSAT.typecategories.value == "all":
					if exists(str(ALL_CATEGORIES)):
						remove(ALL_CATEGORIES)
					if exists(str(WILD_CARD_ALL_CATEGORIES)):
						remove(WILD_CARD_ALL_CATEGORIES)
					if exists(str(WILD_CARD_CATYOURLIST)):
						remove(WILD_CARD_CATYOURLIST)
				else:
					if config.plugins.IPToSAT.usercategories.value:
						config.plugins.IPToSAT.usercategories.value = False
						config.plugins.IPToSAT.usercategories.save()
			else:
				self.session.open(MessageBox, language.get(lang, "46") + "\n\n" + language.get(lang, "42"), MessageBox.TYPE_INFO)
		except Exception as err:
			print("ERROR: %s" % str(err))
		self.toggleSecondList()

	def setChangeList(self):
		if self.storage:
			try:
				fileconf = join(ENIGMA2_PATH, "iptosat.conf")
				iptosat2change = join(self.changefolder, "iptosat.conf")
				iptosatconf = join(self.alternatefolder, "iptosat.conf")
				iptosatlist1conf = join(self.alternatefolder, "iptosat_LIST1.conf")
				iptosatlist2conf = join(self.alternatefolder, "iptosat_LIST2.conf")
				if not exists(str(self.changefolder)):
					makedirs(self.changefolder)
				if not exists(str(self.alternatefolder)):
					makedirs(self.alternatefolder)
				if exists(str(iptosat2change)) and not exists(str(iptosatlist1conf)) and not exists(str(iptosatlist2conf)) and not exists(str(iptosatconf)):
					move(fileconf, iptosatlist1conf)
					move(iptosat2change, fileconf)
					if config.plugins.IPToSAT.typecategories.value == "all":
						if exists(str(ALL_CATEGORIES)):
							remove(ALL_CATEGORIES)
						if exists(str(WILD_CARD_ALL_CATEGORIES)):
							remove(WILD_CARD_ALL_CATEGORIES)
					else:
						if config.plugins.IPToSAT.usercategories.value:
							config.plugins.IPToSAT.usercategories.value = False
							config.plugins.IPToSAT.usercategories.save()
					self.getUserData()
					with open(fileconf, "r") as f:
						host = f.read()
						self.host = host.split()[1].split('Host=')[1].split(':')[1].replace("//", "http://") if not fileContains(fileconf, "https") else host.split()[1].split('Host=')[1].split(':')[1].replace("//", "https://")
					self.session.openWithCallback(self.doChangeList, MessageBox, language.get(lang, "73") + self.host + "\n\n" + language.get(lang, "59") + self.alternatefolder + "/", MessageBox.TYPE_INFO)
				if not exists(str(iptosat2change)) and not exists(str(iptosatlist1conf)) and not exists(str(iptosatlist2conf)) and not exists(str(iptosatconf)):
					self.session.open(MessageBox, language.get(lang, "49") + self.changefolder + "/" + "\n\n" + language.get(lang, "50"), MessageBox.TYPE_INFO)
				if exists(str(iptosatconf)) and exists(str(iptosat2change)):
					if exists(str(iptosatlist1conf)):
						remove(iptosatconf)
					if exists(str(iptosatlist2conf)):
						remove(iptosatconf)
					if exists(str(iptosatconf)):
						self.session.open(MessageBox, language.get(lang, "53") + "\n\n" + iptosatconf + "\n\n" + language.get(lang, "54") + "\n\n" + iptosat2change + "\n\n" + language.get(lang, "41"), MessageBox.TYPE_INFO)
				if exists(str(iptosatconf)) and not exists(str(iptosat2change)):
					self.session.open(MessageBox, language.get(lang, "49") + self.changefolder + "/", MessageBox.TYPE_INFO)
				if exists(str(iptosatlist1conf)) and exists(str(iptosat2change)):
					with open(fileconf, "r") as f:
						host = f.read()
						self.host = host.split()[1].split('Host=')[1].split(':')[1].replace("//", "http://") if not fileContains(iptosatlist1conf, "https") else host.split()[1].split('Host=')[1].split(':')[1].replace("//", "https://")
					self.session.openWithCallback(self.doChangeList, MessageBox, language.get(lang, "48") + self.host + "\n\n" + language.get(lang, "45"), MessageBox.TYPE_YESNO, default=False)
				if not exists(str(iptosat2change)):
					self.session.open(MessageBox, language.get(lang, "55") + "\n\n" + self.changefolder + "/" + language.get(lang, "56"), MessageBox.TYPE_INFO)
				if exists(str(iptosatlist2conf)) and exists(str(iptosat2change)):
					with open(fileconf, "r") as f:
						host = f.read()
						self.host = host.split()[1].split('Host=')[1].split(':')[1].replace("//", "http://") if not fileContains(iptosatlist2conf, "https") else host.split()[1].split('Host=')[1].split(':')[1].replace("//", "https://")
					self.session.openWithCallback(self.doChangeList2, MessageBox, language.get(lang, "48") + self.host + "\n\n" + language.get(lang, "45"), MessageBox.TYPE_YESNO, default=False)
				self.getUserData()
				self["codestatus"].hide()
			except Exception as err:
				print("ERROR: %s" % str(err))

	def exists(self, sref, playlist):
		try:
			refs = [ref['sref'] for ref in playlist['playlist']]
			return False if sref not in refs else True
		except KeyError:
			pass

	def assignWidget(self, color, text):
		self['assign'].setText(text)
		try:
			self['assign'].instance.setForegroundColor(parseColor(color))
			self['status'].hide()
		except:
			pass

	def assignWidgetScript(self, color, text):
		self['managerlistchannels'].setText(text)
		try:
			self['managerlistchannels'].instance.setForegroundColor(parseColor(color))
		except:
			pass

	def resetWidget(self):
		self['assign'].setText('')

	def getSref(self):
		ref = self.getCurrentSelection()
		return ref.toString()

	def callAPI(self, url, callback):
		self['list2'].hide()
		self["please"].show()
		if self.storage:
			self["please"].setText(language.get(lang, "31"))
		getPage(str.encode(url)).addCallback(callback).addErrback(self.error)

	def suscription(self, url, callback):
		getPage(str.encode(url)).addCallback(callback)

	def error(self, error=None):
		try:
			if error:
				log(error)
				self['list2'].hide()
				self["status"].show()
				if fileContains(CONFIG_PATH, "pass"):
					if self.storage:
						self["status"].setText(language.get(lang, "3"))
						self["please"].hide()
						self["codestatus"].hide()
					else:
						self["description"].hide()
						self["status"].setText(language.get(lang, "72"))
						self["codestatus"].hide()
				else:
					self.assignWidgetScript("#00ff2525", language.get(lang, "4"))
		except Exception as err:
			print("ERROR: %s" % str(err))

	def getData(self, data):
		list = []
		self['list2'].show()
		self["please"].hide()
		self['list2'].l.setList(list)
		self.in_channels = False
		js = loads(data)
		bouquets_categories = []
		self.categories = list
		self.bouquets = bouquets_categories
		if js != []:
			for cat in js:
				list.append((str(cat['category_name']),
					str(cat['category_id'])))
				bouquets_categories.append((str(cat['category_name'].replace(u'\u00f1', '').replace(u'\u00c7', '').replace(u'\u00c2', '').replace(u'\u00da', '').replace(u'\u00cd', '').replace(u'\u00c9', '').replace(u'\u00d3', '').replace(u'\u2b50', '').replace('/', '').replace(u'\u2022', '').replace(u'\u26a1', '').replace(u'\u26bd', '').replace(u'\u00d1', 'N').replace(u'\u00cb', 'E')), str(cat['category_name'])))
		if config.plugins.IPToSAT.typecategories.value != "all" and not config.plugins.IPToSAT.usercategories.value:
			iptosatcategoriesjson = ""
			with open(CONFIG_PATH_CATEGORIES, "w") as catclean:
				catclean.write("null")
			with open(CONFIG_PATH_CATEGORIES, "w") as categories:
				dump(self.bouquets, categories)
			with open(CONFIG_PATH_CATEGORIES, "r") as m3ujsonread:
				iptosatcategoriesjson = m3ujsonread.read()
				with open(CONFIG_PATH_CATEGORIES, "w") as m3ujsonwrite:
					m3ujsonwrite.write("{" + "\n" + '		' + iptosatcategoriesjson.replace('FOR ADULT', 'For Adult').replace('[[', '').replace('["', '"').replace('", "', '":').replace('":', '": ["').replace('"]]', '"]').replace('], "', '],' + "\n" + '        "') + "\n" + "}")

	def getSuscriptionData(self, data):
		try:
			status = ""
			exp_date = ""
			expires = ""
			max_connections = ""
			active_cons = ""
			suscription = loads(data)
			with open(SUSCRIPTION_USER_DATA, "w") as datawrite:
				dump(suscription, datawrite)
			with open(SUSCRIPTION_USER_DATA, "r") as line:
				for userdata in line:
					userdata = userdata.strip()
					status = userdata.split('"status": "')[1].split('", "exp_date"')[0] if not fileContains(SUSCRIPTION_USER_DATA, "Active") else language.get(lang, "110")
					exp_date = userdata.split('"exp_date": "')[1].split('", "is_trial')[0] if not fileContains(SUSCRIPTION_USER_DATA, '"exp_date": null') else "null"
					expires = str(datetime.fromtimestamp(int(exp_date)).strftime("%d-%m-%Y")) if "null" not in exp_date else ""
					max_connections = userdata.split('"max_connections": "')[1].split('", "allowed_output_formats"')[0]
					if '"active_cons": "' in userdata:  # not all lists have the same syntax
						active_cons = userdata.split('"active_cons": "')[1].split('", "created_at"')[0]
					else:
						active_cons = userdata.split('"active_cons": ')[1].split(', "created_at"')[0]
			self['managerlistchannels'].show()
			if "null" not in exp_date:
				if int(time()) < int(exp_date) and "Banned" not in status:
					if int(max_connections) == 1:
						self.assignWidgetScript("#86dc3d", language.get(lang, "105") + " " + expires + "\n" + language.get(lang, "106") + " " + status + " " + language.get(lang, "118") + " " + active_cons + "\n" + language.get(lang, "107") + " " + max_connections + " " + language.get(lang, "119"))
					else:
						if int(max_connections) == 2:
							self.assignWidgetScript("#86dc3d", language.get(lang, "105") + " " + expires + "\n" + language.get(lang, "106") + " " + status + " " + language.get(lang, "118") + " " + active_cons + "\n" + language.get(lang, "107") + " " + max_connections + " " + language.get(lang, "120"))
						else:
							self.assignWidgetScript("#86dc3d", language.get(lang, "105") + " " + expires + "\n" + language.get(lang, "106") + " " + status + " " + language.get(lang, "118") + " " + active_cons + "\n" + language.get(lang, "107") + " " + max_connections + " " + language.get(lang, "121"))
				elif int(time()) < int(exp_date):
					self.assignWidgetScript("#00ff2525", language.get(lang, "105") + " " + expires + "\n" + language.get(lang, "106") + " " + language.get(lang, "117") + "\n" + language.get(lang, "107") + " " + max_connections)
				else:
					self.assignWidgetScript("#00ff2525", language.get(lang, "108") + " " + expires + "\n" + language.get(lang, "106") + " " + status + "\n" + language.get(lang, "107") + " " + max_connections)
			else:
				if "Banned" not in status:
					if int(max_connections) == 1:
						self.assignWidgetScript("#86dc3d", language.get(lang, "109") + " " + expires + "\n" + language.get(lang, "106") + " " + status + " " + language.get(lang, "118") + " " + active_cons + "\n" + language.get(lang, "107") + " " + max_connections + " " + language.get(lang, "119"))
					else:
						if int(max_connections) == 2:
							self.assignWidgetScript("#86dc3d", language.get(lang, "109") + " " + expires + "\n" + language.get(lang, "106") + " " + status + " " + language.get(lang, "118") + " " + active_cons + "\n" + language.get(lang, "107") + " " + max_connections + " " + language.get(lang, "120"))
						else:
							self.assignWidgetScript("#86dc3d", language.get(lang, "109") + " " + expires + "\n" + language.get(lang, "106") + " " + status + " " + language.get(lang, "118") + " " + active_cons + "\n" + language.get(lang, "107") + " " + max_connections + " " + language.get(lang, "121"))
				else:
					self.assignWidgetScript("#00ff2525", language.get(lang, "105") + " " + expires + "\n" + language.get(lang, "106") + " " + language.get(lang, "117") + "\n" + language.get(lang, "107") + " " + max_connections)
			if exists(SUSCRIPTION_USER_DATA):
				remove(SUSCRIPTION_USER_DATA)
		except Exception as err:
			print("ERROR: %s" % str(err))
		try:
			if config.plugins.IPToSAT.typecategories.value == "live":
				with open(CONFIG_PATH_CATEGORIES, "r") as fr:
					with open(WILD_CARD_ALL_CATEGORIES, "a") as fw:
						for lines in fr.readlines():
							if not fileContains(WILD_CARD_ALL_CATEGORIES, lines):
								if "{" not in lines and "}" not in lines and "null" not in lines:
									fw.write(lines)
			if config.plugins.IPToSAT.typecategories.value == "vod":
				with open(CONFIG_PATH_CATEGORIES, "r") as fr:
					with open(WILD_CARD_ALL_CATEGORIES, "a") as fw:
						for lines in fr.readlines():
							if not fileContains(WILD_CARD_ALL_CATEGORIES, lines):
								if "{" not in lines and "}" not in lines and "null" not in lines:
									fw.write(lines)
			if config.plugins.IPToSAT.typecategories.value == "series":
				with open(CONFIG_PATH_CATEGORIES, "r") as fr:
					with open(WILD_CARD_ALL_CATEGORIES, "a") as fw:
						for lines in fr.readlines():
							if not fileContains(WILD_CARD_ALL_CATEGORIES, lines):
								if "{" not in lines and "}" not in lines and "null" not in lines:
									fw.write(lines)
			with open(WILD_CARD_ALL_CATEGORIES, "r") as fr:
				with open(ALL_CATEGORIES, "w") as fw:
					fw.write("{" + '\n')
				with open(ALL_CATEGORIES, "a") as fw:
					for lines in fr.readlines():
						lines = lines.replace("]", "],").replace("],,", "],")
						fw.write(lines)
				with open(ALL_CATEGORIES, "r") as fwildcardread:
					with open(ALL_CATEGORIES, "a") as fwildcardwrite:
						for last in fwildcardread.readlines()[-2]:
							last = last.replace(",", "")
							fwildcardwrite.write(last)
				with open(ALL_CATEGORIES, "a") as fw:
					fw.write("}")
		except Exception:
			pass

	def getChannels(self, data):
		sref = str(self.getSref())
		channel_satellite = str(ServiceReference(sref).getServiceName())
		search_name = channel_satellite[2:6]
		list = []
		js = loads(data)
		if js != []:
			for match in js:
				if str(channel_satellite[0:6].upper()) in str(match['name'][0:12].upper()):
					list.append((str(match['name']), str(match['stream_id'])))
			if list == []:
				for match in js:
					if str(search_name) in str(match['epg_channel_id']):
						list.append((str(match['name']), str(match['stream_id'])))
			if list == []:
				for match in js:
					if str(channel_satellite[2:5].lower()) in str(match['name']):
						list.append((str(match['name']), str(match['stream_id'])))
			if list == []:
				for match in js:
					if str(channel_satellite[1:4]) in str(match['name']):
						list.append((str(match['name']), str(match['stream_id'])))
			if list == []:
				for match in js:
					list.append((str(match['name']), str(match['stream_id'])))
		self["status"].hide()
		self['list2'].show()
		self["please"].hide()
		self['list2'].l.setList(list)
		self["list2"].moveToIndex(0)
		self.channels = list
		self.in_channels = True
		self.left()
		sleep(0.2)
		self.right()

	def getChannelsForce(self, data):
		list = []
		js = loads(data)
		if js != []:
			for ch in js:
				list.append((str(ch['name']), str(ch['stream_id'])))
		self["status"].hide()
		self['list2'].show()
		self["please"].hide()
		self['list2'].l.setList(list)
		self["list2"].moveToIndex(0)
		self.channels = list
		self.in_channels = True
		self.left()
		sleep(0.2)
		self.right()

	def exit(self, ret=None):
		if ret:
			self.close(True)
		if self.selectedList == self['list'] and self.in_bouquets:
			self.showFavourites()
			self.in_bouquets = False
		elif self.selectedList == self["list2"] and self.in_channels and not fileContains(CONFIG_PATH, "pass"):
			self.getCategories(self.url)
		else:
			self.close(True)


class EditPlaylist(Screen):
	skin = """
	<screen name="PlaylistEditPlaylistIPToSAT" position="center,center" size="1400,650" title="IPToSAT - Edit">
		<widget name="list" itemHeight="40" position="18,22" size="1364,520" font="Regular;24" scrollbarMode="showOnDemand" scrollbarForegroundColor="#0044a2ff" scrollbarBorderColor="#0044a2ff" />
		<widget source="key_red" render="Label" objectTypes="key_red,StaticText" position="7,583" zPosition="2" size="165,52" backgroundColor="key_red" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
			<convert type="ConditionalShowHide"/>
		</widget>
		<widget source="key_green" render="Label" objectTypes="key_red,StaticText" position="183,583" zPosition="2" size="165,52" backgroundColor="key_green" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
			<convert type="ConditionalShowHide"/>
		</widget>
		<widget source="key_yellow" render="Label" objectTypes="key_red,StaticText" position="359,583" zPosition="2" size="165,52" backgroundColor="key_yellow" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
			<convert type="ConditionalShowHide"/>
		</widget>
		<widget name="status" position="534,562" size="830,89" font="Regular;20" horizontalAlignment="left" verticalAlignment="center" zPosition="3"/>
		<widget name="HelpWindow" position="0,0" size="0,0" alphaTest="blend" conditional="HelpWindow" transparent="1" zPosition="+1" />
	</screen>"""

	def __init__(self, session, *args):
		self.session = session
		Screen.__init__(self, session)
		self.skinName = ["EditPlaylistIPToSAT"]
		self.setTitle(language.get(lang, "16"))
		self['list'] = MenuList([])
		self["key_red"] = StaticText("")
		self["key_green"] = StaticText("")
		self["key_yellow"] = StaticText("")
		self["status"] = Label()
		self["iptosatactions"] = ActionMap(["IPToSATActions"],
		{
			"back": self.close,
			"cancel": self.exit,
			"red": self.keyRed,
			"green": self.keyGreen,
			"yellow": self.keyYellow,
			"ok": self.keyGreen,
			"left": self.goLeft,
			"right": self.goRight,
			"down": self.moveDown,
			"up": self.moveUp,
			"pageUp": self.pageUp,
			"pageDown": self.pageDown,
		}, -2)
		self.channels = []
		self.playlist = getPlaylist()
		self.iniMenu()
		self.clearPlayList()

	def clearPlayList(self):
		try:
			index = self['list'].getSelectionIndex()
			playlist = self.playlist['playlist']
			if self.playlist and range(len(self.channels)):
				for index, name in enumerate(playlist):
					if "sref" not in name or "channel" not in name or "url" not in name:
						del playlist[index]
						print(index)
						with open(PLAYLIST_PATH, 'w') as f:
							dump(self.playlist, f, indent=4)
					self.iniMenu()
		except Exception:
			if exists(PLAYLIST_PATH):
				with open(PLAYLIST_PATH, 'w') as fw:
					fw.write("{" + "\n" + '	"playlist": []' + "\n" + "}")
				self["status"].setText(language.get(lang, "96"))
			else:
				with open(PLAYLIST_PATH, 'w') as fw:
					fw.write("{" + "\n" + '	"playlist": []' + "\n" + "}")
				self["status"].setText(language.get(lang, "97"))

	def iniMenu(self):
		if self.playlist:
			list = []
			try:
				for channel in self.playlist['playlist']:
					reference = channel['sref'][7:11] if ":" not in channel['sref'][7:11] else channel['sref'][6:10]
					list.append(str(channel['channel'] + "   " + reference))
			except Exception:
				pass
			if len(list) > 0:
				self['list'].l.setList(list)
				self.channels = sorted(list)
				self["status"].hide()
				self["key_red"].setText(language.get(lang, "137"))
				self["key_green"].setText(language.get(lang, "28"))
				self["key_yellow"].setText(language.get(lang, "27"))
				self["status"].show()
				self["status"].setText(language.get(lang, "95"))
			else:
				self["status"].setText(language.get(lang, "29"))
				self["status"].show()
				self['list'].hide()
				self["key_red"].setText(language.get(lang, "137"))
				self["key_green"].setText("")
				self["key_yellow"].setText("")
		else:
			self["status"].setText(language.get(lang, "30"))
			self["status"].show()
			self['list'].hide()

	def keyGreen(self):
		index = self['list'].getCurrent()
		message = language.get(lang, "104")
		if index and not fileContains(PLAYLIST_PATH, '": []'):
			self.session.openWithCallback(self.deleteChannel, MessageBox, message + str(index), MessageBox.TYPE_YESNO, default=False)

	def deleteChannel(self, answer):
		if answer:
			index = self['list'].getSelectionIndex()
			playlist = self.playlist['playlist']
			try:
				if self.playlist and range(len(self.channels)):
					del playlist[index]
					with open(PLAYLIST_PATH, 'w') as f:
						dump(self.playlist, f, indent=4)
				self.iniMenu()
			except Exception as err:
				print("ERROR: %s" % str(err))

	def deleteChannelsList(self, answer):
		if answer:
			self.playlist['playlist'] = []
			with open(PLAYLIST_PATH, 'w') as f:
				dump(self.playlist, f, indent=4)
			self.iniMenu()
		else:
			self.iniMenu()

	def keyYellow(self):
		message = language.get(lang, "7")
		if self.playlist and len(self.channels) > 0 and not fileContains(PLAYLIST_PATH, '": []'):
			self.session.openWithCallback(self.deleteChannelsList, MessageBox, message, MessageBox.TYPE_YESNO, default=False)

	def keyRed(self, ret=None):
		self.close(True)

	def exit(self, ret=None):
		self.close(True)

	def goRight(self):
		self["list"].pageDown()

	def goLeft(self):
		self["list"].pageUp()

	def moveUp(self):
		self["list"].up()

	def moveDown(self):
		self["list"].down()

	def pageUp(self):
		self["list"].self["list"].instance.pageUp

	def pageDown(self):
		self["list"].self["list"].instance.pageDown


class EditCategories(Screen):
	skin = """
	<screen name="EditCategories" position="center,center" size="1600,960" title="IPToSAT - Edit">
		<widget name="list" itemHeight="41" position="18,14" size="1566,698" font="Regular;27" scrollbarMode="showOnDemand" scrollbarForegroundColor="#0044a2ff" scrollbarBorderColor="#0044a2ff" />
		<widget source="key_red" render="Label" objectTypes="key_red,StaticText" position="7,895" zPosition="2" size="165,57" backgroundColor="key_red" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
			<convert type="ConditionalShowHide"/>
		</widget>
		<widget source="key_green" render="Label" objectTypes="key_green,StaticText" position="183,895" zPosition="2" size="165,57" backgroundColor="key_green" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
			<convert type="ConditionalShowHide"/>
		</widget>
		<widget source="key_yellow" render="Label" objectTypes="key_yellow,StaticText" position="359,895" zPosition="2" size="165,57" backgroundColor="key_yellow" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
			<convert type="ConditionalShowHide"/>
		</widget>
		<widget source="key_blue" render="Label" objectTypes="key_blue,StaticText" position="535,895" zPosition="2" size="165,57" backgroundColor="key_blue" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
			<convert type="ConditionalShowHide"/>
		</widget>
		<widget source="key_0" render="Label" position="7,860" size="80,25" zPosition="12" backgroundColor="key_back" font="Regular;18" horizontalAlignment="center" verticalAlignment="center">
			<convert type="ConditionalShowHide"/>
		</widget>
		<widget source="key_1" render="Label" position="92,860" size="80,25" zPosition="12" backgroundColor="key_back" font="Regular;18" horizontalAlignment="center" verticalAlignment="center">
			<convert type="ConditionalShowHide"/>
		</widget>
		<widget name="footnote" conditional="footnote" position="18,712" size="1566,70" foregroundColor="#e5e619" font="Regular;24" zPosition="3" />
		<widget name="status" position="755,783" size="830,175" font="Regular;23" horizontalAlignment="left" verticalAlignment="center" zPosition="3"/>
		<widget name="HelpWindow" position="0,0" size="0,0" alphaTest="blend" conditional="HelpWindow" transparent="1" zPosition="+1" />
	</screen>"""

	def __init__(self, session, *args):
		self.session = session
		Screen.__init__(self, session)
		self.skinName = ["EditCategories"]
		self.setTitle(typeselectcategorie())
		self['list'] = MenuList([])
		self["key_red"] = StaticText("")
		self["key_green"] = StaticText("")
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("")
		self["key_0"] = StaticText("")
		self["key_1"] = StaticText("")
		self["status"] = Label()
		self["footnote"] = Label()
		self.folderBackupCategories = None
		self.backup_categories = None
		self.path = None
		self.storage = False
		self["iptosatactions"] = ActionMap(["IPToSATActions"],
		{
			"back": self.close,
			"cancel": self.exit,
			"red": self.keyRed,
			"green": self.keyGreen,
			"yellow": self.keyYellow,
			"blue": self.keyBlue,
			"ok": self.keyGreen,
			"left": self.goLeft,
			"right": self.goRight,
			"down": self.moveDown,
			"up": self.moveUp,
			"pageUp": self.pageUp,
			"pageDown": self.pageDown,
			"0": self.restoreCategories,
			"1": self.deleteBackupCategories,
		}, -2)
		self.chekScenarioToBackup()
		self.bouquets = []
		self.categories = getCategories()
		self.iniMenu()

	def chekScenarioToBackup(self):
		for partition in harddiskmanager.getMountedPartitions():
			self.path = normpath(partition.mountpoint)
			if self.path != "/" and "net" not in self.path and "autofs" not in self.path:
				self.storage = True
				self.folderBackupCategories = join(self.path, f"IPToSAT/{MODEL}/BackupChannelsList")
				self.backup_categories = join(self.folderBackupCategories, BACKUP_CATEGORIES)

	def iniMenu(self):
		list = []
		if self.categories:
			try:
				for bouquets in self.categories:
					list.append(str(bouquets))
			except Exception:
				pass
			if len(list) > 0:
				self['list'].l.setList(list)
				self.bouquets = sorted(list)
				self["key_red"].setText(language.get(lang, "137"))
				self["key_green"].setText(language.get(lang, "138"))
				self["key_yellow"].setText(language.get(lang, "27"))
				self["key_blue"].setText(language.get(lang, "161"))
				if len(list) < 7:
					self["footnote"] = Label(language.get(lang, "185"))
				if fileContains(WILD_CARD_CATYOURLIST, ":") and self.storage or exists(str(self.backup_categories)):
					self["key_0"].setText("0")
				if exists(str(self.backup_categories)):
					self["key_1"].setText("1")
				if config.plugins.IPToSAT.typecategories.value != "all":
					if not config.plugins.IPToSAT.usercategories.value:
						if not self.storage:
							self["status"].setText(language.get(lang, "139"))
						else:
							if exists(str(self.backup_categories)):
								self["status"].setText(language.get(lang, "175"))
							else:
								if fileContains(WILD_CARD_CATYOURLIST, ":"):
									self["status"].setText(language.get(lang, "180"))
								else:
									self["status"].setText(language.get(lang, "169"))
					else:
						if not self.storage:
							self["status"].setText(language.get(lang, "173"))
						else:
							if exists(str(self.backup_categories)):
								self["status"].setText(language.get(lang, "175"))
							else:
								if fileContains(WILD_CARD_CATYOURLIST, ":"):
									self["status"].setText(language.get(lang, "180"))
								else:
									self["status"].setText(language.get(lang, "169"))
				else:
					if not self.storage:
						self["status"].setText(language.get(lang, "169"))
					else:
						if exists(str(self.backup_categories)):
							self["status"].setText(language.get(lang, "175"))
						else:
							if fileContains(WILD_CARD_CATYOURLIST, ":"):
								self["status"].setText(language.get(lang, "180"))
							else:
								self["status"].setText(language.get(lang, "169"))
			else:
				self["status"].setText(language.get(lang, "140"))
				self['list'].hide()
		else:
			try:
				if fileContains(CONFIG_PATH_CATEGORIES, ":"):
					index = self['list'].getCurrent()
					with open(CONFIG_PATH_CATEGORIES, "r") as categoriesjsonread:
						with open(WILD_CARD_CATEGORIES_FILE, "w") as fwildcardwrite:
							for bouquet in categoriesjsonread.readlines():
								if str(index) not in bouquet and "}" not in bouquet:
									fwildcardwrite.write(bouquet)
					with open(WILD_CARD_CATEGORIES_FILE, "r") as frwildcardread:
						with open(WILD_CARD_CATEGORIES_FILE, "a") as fwildcardwrite:
							for last in frwildcardread.readlines()[-2]:
								last = last.replace("}", "").replace(",", "")
								fwildcardwrite.write(last)
					with open(WILD_CARD_CATEGORIES_FILE, "r") as frwildcardread:
						with open(WILD_CARD_CATEGORIES_FILE, "a") as fwildcardwrite:
							for last in frwildcardread.readlines()[-2]:
								last = last.replace(last, "")
								fwildcardwrite.write(last)
						with open(WILD_CARD_CATEGORIES_FILE, "a") as fwildcardwrite:
							fwildcardwrite.write("}")
					move(WILD_CARD_CATEGORIES_FILE, CONFIG_PATH_CATEGORIES)
			except Exception:
				pass
			try:
				for bouquets in getCategories():
					list.append(str(bouquets))
			except Exception:
				pass
			if len(list) > 0:
				self['list'].l.setList(list)
				self["key_green"].setText(language.get(lang, "138"))
				if fileContains(CONFIG_PATH_CATEGORIES, ":"):
					self["key_blue"].setText(language.get(lang, "161"))
				if fileContains(WILD_CARD_CATYOURLIST, ":") and self.storage:
					self["key_0"].setText("0")
				self["status"].show()
				self["key_red"].setText(language.get(lang, "137"))
				self["status"].setText(language.get(lang, "136"))
			else:
				if not fileContains(CONFIG_PATH_CATEGORIES, "null"):
					if not exists(str(self.backup_categories)):
						self["status"].setText(language.get(lang, "134"))
					else:
						self["status"].setText(language.get(lang, "177"))
					self["key_red"].setText(language.get(lang, "137"))
					with open(CONFIG_PATH_CATEGORIES, "w") as catclean:
						catclean.write("null")
				else:
					if config.plugins.IPToSAT.typecategories.value != "all":
						with open(CONFIG_PATH_CATEGORIES, "w") as catclean:
							catclean.write("null")
						if not config.plugins.IPToSAT.usercategories.value:
							self["status"].setText(language.get(lang, "143"))
						else:
							config.plugins.IPToSAT.usercategories.value = False
							config.plugins.IPToSAT.usercategories.save()
							AssignService(self.session)
					else:
						if not exists(str(self.backup_categories)):
							if not fileContains(WILD_CARD_CATYOURLIST, ":"):
								self["status"].setText(language.get(lang, "134"))
							else:
								self["status"].setText(language.get(lang, "183"))
						else:
							self["status"].setText(language.get(lang, "177"))
				AssignService(self.session)
				self["status"].show()
				self['list'].hide()
				self["key_red"].setText(language.get(lang, "137"))
				self["key_green"].setText("")
				self["key_yellow"].setText("")
				if fileContains(CONFIG_PATH_CATEGORIES, ":") and fileContains(WILD_CARD_CATYOURLIST, ":"):
					self["key_blue"].setText(language.get(lang, "161"))
				else:
					self["key_blue"].setText("")
				if fileContains(WILD_CARD_CATYOURLIST, ":") and self.storage:
					self["key_0"].setText("0")
				if fileContains(WILD_CARD_CATYOURLIST, ":") and fileContains(WILD_CARD_CATEGORIES_FILE, ":"):
					if not self.storage:
						self["status"].setText(language.get(lang, "165"))
						self["key_blue"].setText(language.get(lang, "161"))
					else:
						self["key_blue"].setText(language.get(lang, "161"))
						if not exists(str(self.backup_categories)):
							self["status"].setText(language.get(lang, "176"))
						else:
							self["status"].setText(language.get(lang, "181"))
				else:
					if config.plugins.IPToSAT.typecategories.value == "all":
						if fileContains(WILD_CARD_CATYOURLIST, ":"):
							with open(WILD_CARD_CATYOURLIST, "r") as f:
								for line in f.readlines():
									if len(line) > 2 and fileContains(WILD_CARD_CATYOURLIST, "}"):
										if not self.storage:
											self["key_blue"].setText(language.get(lang, "161"))
											self["status"].setText(language.get(lang, "165"))
										else:
											self["key_blue"].setText(language.get(lang, "161"))
											if not exists(str(self.backup_categories)):
												self["status"].setText(language.get(lang, "176"))
											else:
												self["status"].setText(language.get(lang, "181"))
						else:
							self["key_blue"].setText("")
							if not exists(str(self.backup_categories)):
								self["status"].setText(language.get(lang, "123"))
							else:
								self["key_0"].setText("0")
								self["key_1"].setText("1")
								self["status"].setText(language.get(lang, "178"))
					else:
						if not config.plugins.IPToSAT.usercategories.value:
							self["status"].setText(language.get(lang, "143"))
						else:
							self["status"].setText(language.get(lang, "143"))
							config.plugins.IPToSAT.usercategories.value = False
							config.plugins.IPToSAT.usercategories.save()
						AssignService(self.session)

	def keyGreen(self):
		index = self['list'].getCurrent()
		if fileContains(WILD_CARD_CATYOURLIST, ":") and config.plugins.IPToSAT.typecategories.value != "all":
			message = language.get(lang, "135") + "\n" + "iptosat_norhap_" + str(index) + "\n\n" + language.get(lang, "155")
		else:
			if config.plugins.IPToSAT.typecategories.value == "all":
				message = language.get(lang, "135") + "\n" + "iptosat_norhap_" + str(index) + "\n\n" + language.get(lang, "166")
			else:
				message = language.get(lang, "135") + "\n" + "iptosat_norhap_" + str(index)
		if index and not fileContains(CONFIG_PATH_CATEGORIES, "null"):
			self.session.openWithCallback(self.deleteBouquet, MessageBox, message, MessageBox.TYPE_YESNO, default=False)

	def deleteBouquet(self, answer):
		if answer:
			try:
				index = self['list'].getCurrent()
				with open(CONFIG_PATH_CATEGORIES, "r") as categoriesjsonread:
					with open(WILD_CARD_CATEGORIES_FILE, "w") as fwildcardwrite:
						for bouquet in categoriesjsonread.readlines():
							if str(index) not in bouquet:
								if "EU | GR " in bouquet or "AR| " in bouquet:  # remove global for flags AR and GR unicode characters in CONFIG_PATH_CATEGORIES
									fwildcardwrite.write(bouquet.replace(bouquet, ""))
								else:
									fwildcardwrite.write(bouquet)
				if config.plugins.IPToSAT.typecategories.value == "all":
					with open(CONFIG_PATH_CATEGORIES, "r") as fr:
						with open(WILD_CARD_CATYOURLIST, "w") as fw:
							for lines in fr.readlines():
								if "{" not in lines and "}" not in lines and "null" not in lines or "," in lines and "{" not in lines and "}" not in lines:
									fw.write(lines)
			except Exception:
				pass
			move(WILD_CARD_CATEGORIES_FILE, CONFIG_PATH_CATEGORIES)
			if config.plugins.IPToSAT.typecategories.value != "all":
				if not config.plugins.IPToSAT.usercategories.value:
					config.plugins.IPToSAT.usercategories.value = True
					config.plugins.IPToSAT.usercategories.save()
			try:
				self.session.openWithCallback(self.exit, EditCategories)
			except Exception:
				pass

	def deleteBouquetsList(self, answer):
		if answer:
			self.categories = None
			with open(CONFIG_PATH_CATEGORIES, 'w') as f:
				dump(self.categories, f)
			if config.plugins.IPToSAT.typecategories.value == "all":
				if exists(str(ALL_CATEGORIES)):
					remove(ALL_CATEGORIES)
				if exists(str(WILD_CARD_ALL_CATEGORIES)):
					remove(WILD_CARD_ALL_CATEGORIES)
				if exists(str(WILD_CARD_CATYOURLIST)):
					remove(WILD_CARD_CATYOURLIST)
			else:
				if exists(str(CONFIG_PATH_CATEGORIES)):
					with open(CONFIG_PATH_CATEGORIES, "r") as fr:
						with open(WILD_CARD_CATYOURLIST, "w") as fw:
							for lines in fr.readlines():
								if "{" not in lines and "}" not in lines and "null" not in lines:
									fw.write(lines)
			self.iniMenu()
		else:
			self.iniMenu()

	def keyYellow(self):
		if config.plugins.IPToSAT.typecategories.value != "all":
			message = language.get(lang, "26")
		else:
			message = language.get(lang, "162")
		if self.categories and len(self.bouquets) > 0 and not fileContains(CONFIG_PATH_CATEGORIES, "null"):
			self.session.openWithCallback(self.deleteBouquetsList, MessageBox, message, MessageBox.TYPE_YESNO, default=False)

	def restoreYourList(self, answer):
		if answer:
			try:
				if not fileContains(WILD_CARD_CATYOURLIST, ":"):
					with open(CONFIG_PATH_CATEGORIES, "r") as fr:
						with open(WILD_CARD_CATYOURLIST, "a") as fw:
							for lines in fr.readlines():
								if "{" not in lines and "}" not in lines and "null" not in lines:
									fw.write(lines)
						with open(WILD_CARD_CATYOURLIST, "a") as fw:
							for lines in fr.readlines():
								lines = lines.replace("]", "],").replace("],,", "],")
								fw.write(lines)
				if config.plugins.IPToSAT.typecategories.value != "all":
					with open(CONFIG_PATH_CATEGORIES, "r") as fr:
						with open(WILD_CARD_CATYOURLIST, "a") as fw:
							for lines in fr.readlines():
								if not fileContains(WILD_CARD_CATYOURLIST, lines):
									if "{" not in lines and "}" not in lines and "null" not in lines:
										fw.write(lines)
				else:
					with open(CONFIG_PATH_CATEGORIES, "r") as fr:
						with open(WILD_CARD_CATYOURLIST, "w") as fw:
							for lines in fr.readlines():
								if "{" not in lines and "}" not in lines and "null" not in lines:
									fw.write(lines)
				with open(WILD_CARD_CATYOURLIST, "r") as fr:
					with open(CONFIG_PATH_CATEGORIES, "w") as fw:
						fw.write("{" + '\n')
					with open(CONFIG_PATH_CATEGORIES, "a") as fw:
						for lines in fr.readlines():
							lines = lines.replace("]", "],").replace("],,", "],")
							fw.write(lines)
					with open(CONFIG_PATH_CATEGORIES, "r") as fwildcardread:
						with open(CONFIG_PATH_CATEGORIES, "a") as fwildcardwrite:
							readcategoriesjson = fwildcardread.readlines()
							if len(readcategoriesjson) > 1:
								for last in readcategoriesjson[-2]:
									last = last.replace(",", "")
									fwildcardwrite.write(last)
					with open(CONFIG_PATH_CATEGORIES, "a") as fw:
						fw.write("}")
				if config.plugins.IPToSAT.typecategories.value != "all":
					config.plugins.IPToSAT.typecategories.value = "all"
					config.plugins.IPToSAT.typecategories.save()
			except Exception:
				self.exit()
			self.exit()

	def keyBlue(self):
		message = language.get(lang, "164")
		with open(CONFIG_PATH_CATEGORIES, "r") as fr:
			readcategoriesjson = fr.readlines()
			if len(readcategoriesjson) > 3:
				if fileContains(CONFIG_PATH_CATEGORIES, ":") and fileContains(WILD_CARD_CATYOURLIST, ":"):
					self.session.openWithCallback(self.restoreYourList, MessageBox, message, MessageBox.TYPE_YESNO, default=False)
					return
			if len(readcategoriesjson) > 0:
				if fileContains(CONFIG_PATH_CATEGORIES, ":") and fileContains(ALL_CATEGORIES, ":"):
					copy(CONFIG_PATH_CATEGORIES, ALL_CATEGORIES)
					if not fileContains(WILD_CARD_CATYOURLIST, ":"):
						with open(CONFIG_PATH_CATEGORIES, "r") as fr:
							with open(WILD_CARD_CATYOURLIST, "a") as fw:
								for lines in fr.readlines():
									if "{" not in lines and "}" not in lines and "null" not in lines:
										fw.write(lines)
							with open(WILD_CARD_CATYOURLIST, "a") as fw:
								for lines in fr.readlines():
									lines = lines.replace("]", "],").replace("],,", "],")
									fw.write(lines)
								if config.plugins.IPToSAT.typecategories.value != "all":
									config.plugins.IPToSAT.typecategories.value = "all"
									config.plugins.IPToSAT.typecategories.save()
					self.session.openWithCallback(self.restoreYourList, MessageBox, message, MessageBox.TYPE_YESNO, default=False)
					return

	def doRestorecategories(self, answer):
		if answer:
			try:
				if not exists(str(self.backup_categories)) and fileContains(WILD_CARD_CATYOURLIST, ":"):
					copy(WILD_CARD_CATYOURLIST, self.backup_categories)
				else:
					if exists(str(self.backup_categories)):
						copy(self.backup_categories, WILD_CARD_CATYOURLIST)
						with open(self.backup_categories, "r") as fr:
							with open(CONFIG_PATH_CATEGORIES, "w") as fw:
								fw.write("{" + '\n')
							with open(CONFIG_PATH_CATEGORIES, "a") as fw:
								for lines in fr.readlines():
									lines = lines.replace("]", "],").replace("],,", "],")
									fw.write(lines)
							with open(CONFIG_PATH_CATEGORIES, "r") as fwildcardread:
								with open(CONFIG_PATH_CATEGORIES, "a") as fwildcardwrite:
									readcategoriesjson = fwildcardread.readlines()
									if len(readcategoriesjson) > 1:
										for last in readcategoriesjson[-2]:
											last = last.replace(",", "")
											fwildcardwrite.write(last)
							with open(CONFIG_PATH_CATEGORIES, "a") as fw:
								fw.write("}")
						if config.plugins.IPToSAT.typecategories.value != "all":
							config.plugins.IPToSAT.typecategories.value = "all"
							config.plugins.IPToSAT.typecategories.save()
			except Exception:
				self.exit()
			self.exit()

	def restoreCategories(self):
		message = ""
		if self.folderBackupCategories:
			if not exists(str(self.folderBackupCategories)):
				makedirs(self.folderBackupCategories)
			if fileContains(WILD_CARD_CATYOURLIST, ":") and not exists(str(self.backup_categories)) or exists(str(self.backup_categories)):
				if exists(str(self.backup_categories)):
					message = language.get(lang, "182")
				else:
					message = language.get(lang, "174")
				self.session.openWithCallback(self.doRestorecategories, MessageBox, message, MessageBox.TYPE_YESNO, default=False)
				return

	def deleteBackupCategories(self):
		if exists(str(self.backup_categories)):
			remove(self.backup_categories)
			self.exit()

	def keyRed(self, ret=None):
		self.close(True)

	def exit(self, ret=None):
		self.close(True)

	def goRight(self):
		self["list"].pageDown()

	def goLeft(self):
		self["list"].pageUp()

	def moveUp(self):
		self["list"].up()

	def moveDown(self):
		self["list"].down()

	def pageUp(self):
		self["list"].self["list"].instance.pageUp

	def pageDown(self):
		self["list"].self["list"].instance.pageDown


class InstallChannelsLists(Screen):
	skin = """
	<screen name="InstallChannelsListsIPToSAT" position="center,center" size="1400,701" title="IPToSAT - Install Channels Lists">
		<widget name="list" itemHeight="40" position="18,22" size="1364,520" font="Regular;25" scrollbarMode="showOnDemand"/>
		<widget source="key_red" render="Label" objectTypes="key_red,StaticText" position="7,618" zPosition="2" size="165,52" backgroundColor="key_red" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
			<convert type="ConditionalShowHide"/>
		</widget>
		<widget source="key_green" render="Label" objectTypes="key_green,StaticText" position="183,618" zPosition="2" size="165,52" backgroundColor="key_green" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
			<convert type="ConditionalShowHide"/>
		</widget>
		<widget source="key_yellow" render="Label" objectTypes="key_yellow,StaticText" position="359,618" zPosition="2" size="165,52" backgroundColor="key_yellow" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
			<convert type="ConditionalShowHide"/>
		</widget>
		<widget source="key_blue" render="Label" objectTypes="key_blue,StaticText" position="535,618" zPosition="2" size="165,52" backgroundColor="key_blue" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
			<convert type="ConditionalShowHide"/>
		</widget>
		<widget name="status" position="712,565" size="684,135" font="Regular;20" horizontalAlignment="left" verticalAlignment="center" zPosition="3"/>
		<widget name="HelpWindow" position="0,0" size="0,0" alphaTest="blend" conditional="HelpWindow" transparent="1" zPosition="+1" />
	</screen>"""

	def __init__(self, session, *args):
		self.session = session
		Screen.__init__(self, session)
		self.storage = False
		self.folderlistchannels = None
		self.zip_jungle = None
		self.zip_sorys_vuplusmania = None
		self.path = None
		self.tuxboxxml = 'https://github.com/OpenPLi/tuxbox-xml/archive/refs/heads/master.zip'
		self.skinName = ["InstallChannelsListsIPToSAT"]
		self.setTitle(language.get(lang, "88"))
		self['list'] = MenuList([])
		self["key_red"] = StaticText("")
		self["key_green"] = StaticText("")
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText(language.get(lang, "102"))
		self["status"] = Label()
		self["iptosatactions"] = ActionMap(["IPToSATActions"],
		{
			"back": self.close,
			"cancel": self.exit,
			"red": self.keyRed,
			"green": self.keyGreen,
			"ok": self.keyGreen,
			"yellow": self.getListsRepositories,
			"blue": self.getSourceUpdated,
			"left": self.goLeft,
			"right": self.goRight,
			"down": self.moveDown,
			"up": self.moveUp,
			"pageUp": self.pageUp,
			"pageDown": self.pageDown,
		}, -2)
		self.listChannels = getChannelsLists()
		self.chekScenarioToInstall()
		self.iniMenu()

	def chekScenarioToInstall(self):
		for partition in harddiskmanager.getMountedPartitions():
			self.path = normpath(partition.mountpoint)
			if self.path != "/" and "net" not in self.path and "autofs" not in self.path:
				self.storage = True
				self.folderlistchannels = join(self.path, f"IPToSAT/{MODEL}/ChannelsLists")
				self.zip_jungle = join(self.folderlistchannels, "jungle.zip")
				self.zip_sorys_vuplusmania = join(self.folderlistchannels, "sorys_vuplusmania.zip")
				self.zip_tuxbox_xml = join(self.folderlistchannels, "tuxbox-xml-master.zip")
				if not exists(str(self.folderlistchannels)):
					makedirs(self.folderlistchannels)
				workdirectory = self.folderlistchannels + '/*'
				for dirfiles in glob(workdirectory, recursive=True):
					if exists(str(dirfiles)):
						eConsoleAppContainer().execute('rm -rf ' + dirfiles)

	def iniMenu(self):
		if not exists(CHANNELS_LISTS_PATH):
			with open(CHANNELS_LISTS_PATH, 'w') as fw:
				fw.write("{" + "\n" + '	"channelslists": []' + "\n" + "}")
				if exists(CHANNELS_LISTS_PATH):
					self["key_yellow"].setText(language.get(lang, "92"))
					self["key_red"].setText(language.get(lang, "89"))
					self["status"].setText(language.get(lang, "184"))
		if self.listChannels:
			list = []
			for listtype in self.listChannels['channelslists']:
				try:
					list.append(str(listtype['listtype']))
				except KeyError:
					pass
			if len(list) > 0:
				self['list'].l.setList(list)
				self["status"].setText(language.get(lang, "92"))
				self["key_red"].setText(language.get(lang, "89"))
				self["key_green"].setText(language.get(lang, "90"))
				self["key_yellow"].setText(language.get(lang, "92"))
				self["status"].setText(language.get(lang, "2"))
			else:
				self["key_red"].setText(language.get(lang, "89"))
				self["key_yellow"].setText(language.get(lang, "92"))
				self["status"].setText(language.get(lang, "184"))

	def keyGreen(self):
		channelslists = self["list"].getCurrent()
		if channelslists and self.storage:
			self.session.openWithCallback(self.doInstallChannelsList, MessageBox, language.get(lang, "91") + " " + channelslists, MessageBox.TYPE_YESNO)

	def keyRed(self):
		self.close(True)

	def exit(self, ret=None):
		self.close(True)

	def doindexListsRepositories(self, answer):
		from zipfile import ZipFile
		if answer:
			try:
				urljungle = 'https://github.com/jungla-team/Canales-enigma2/archive/refs/heads/main.zip'
				urlnorhap = 'https://github.com/norhap/channelslists/archive/refs/heads/main.zip'
				junglerepository = get(urljungle, timeout=10)
				norhaprepository = get(urlnorhap, timeout=10)
				tuxboxrepository = get(self.tuxboxxml, timeout=10)
				with open(CHANNELS_LISTS_PATH, 'w') as fw:
					fw.write("{" + "\n" + '	"channelslists": []' + "\n" + "}")
				with open(str(self.zip_jungle), "wb") as jungle:
					jungle.write(junglerepository.content)
				with open(str(self.zip_sorys_vuplusmania), "wb") as norhap:
					norhap.write(norhaprepository.content)
				with open(str(self.zip_tuxbox_xml), "wb") as xml:
					xml.write(tuxboxrepository.content)
				if exists(str(self.zip_tuxbox_xml)):
					with ZipFile(self.zip_tuxbox_xml, 'r') as zipfile:
						zipfile.extractall(self.folderlistchannels)
				# TUXBOX FILES UPDATE REPOSITORY OPenPLi
				eConsoleAppContainer().execute('cp -a ' + self.folderlistchannels + '/tuxbox-xml-master/xml/*.xml ' + FILES_TUXBOX + '/')
				# JUNGLE TEAM
				if exists(str(self.zip_jungle)):
					with ZipFile(self.zip_jungle, 'r') as zipfile:
						zipfile.extractall(self.folderlistchannels)
				junglerepo = self.folderlistchannels + '/*/*Jungle-*'
				jungleupdatefile = self.folderlistchannels + '/**/*actualizacion*'
				junglelists = ""
				index = ""
				for file in glob(jungleupdatefile, recursive=True):
					with open(file, 'r') as fr:
						update = fr.readlines()
						for index in update:
							index = index.replace("[", "")
				for folders in glob(junglerepo, recursive=True):
					junglelists = str([folders.split('main/')[1], index])[1:-1].replace('\'', '').replace(',', '   ')
					indexlistssources = getChannelsLists()
					indexlistssources['channelslists'].append({'listtype': junglelists})
					with open(CHANNELS_LISTS_PATH, 'w') as f:
						dump(indexlistssources, f, indent=4)
				# SORYS VUPLUSMANIA REPOSITORY CHANNELSLISTS NORHAP
				if exists(str(self.zip_sorys_vuplusmania)):
					with ZipFile(self.zip_sorys_vuplusmania, 'r') as zipfile:
						zipfile.extractall(self.folderlistchannels)
				sorysrepository = self.folderlistchannels + '/*/*Sorys-*'
				sorysupdatefile = self.folderlistchannels + '/*/*Sorys-*/*actualizacion*'
				soryslists = ""
				index = ""
				for file in glob(sorysupdatefile, recursive=True):
					with open(file, 'r') as fr:
						update = fr.readlines()
						for index in update:
							index = index.replace("[", "")
				for folders in glob(sorysrepository, recursive=True):
					soryslists = str([folders.split('main/')[1], index])[1:-1].replace('\'', '').replace(',', '   ')
					indexlistssources = getChannelsLists()
					indexlistssources['channelslists'].append({'listtype': soryslists})
					with open(CHANNELS_LISTS_PATH, 'w') as f:
						dump(indexlistssources, f, indent=4)
				vuplusmaniarepository = self.folderlistchannels + '/*/*Vuplusmania-*'
				vuplusmaniaupdatefile = self.folderlistchannels + '/*/*Vuplusmania-*/*actualizacion*'
				vuplusmanialists = ""
				index = ""
				for file in glob(vuplusmaniaupdatefile, recursive=True):
					with open(file, 'r') as fr:
						update = fr.readlines()
						for index in update:
							index = index.replace("[", "")
				for folders in glob(vuplusmaniarepository, recursive=True):
					vuplusmanialists = str([folders.split('main/')[1], index])[1:-1].replace('\'', '').replace(',', '   ')
					indexlistssources = getChannelsLists()
					indexlistssources['channelslists'].append({'listtype': vuplusmanialists})
					with open(CHANNELS_LISTS_PATH, 'w') as f:
						dump(indexlistssources, f, indent=4)
				sleep(5)  # TODO
				self.listChannels = getChannelsLists()
				workdirectory = self.folderlistchannels + '/*'
				for dirfiles in glob(workdirectory, recursive=True):
					if exists(str(dirfiles)):
						eConsoleAppContainer().execute('rm -rf ' + dirfiles)
				self.iniMenu()
			except Exception as err:
				print("ERROR: %s" % str(err))

	def getListsRepositories(self):
		if self.storage:
			self.session.openWithCallback(self.doindexListsRepositories, MessageBox, language.get(lang, "87"), MessageBox.TYPE_YESNO)

	def getSourceUpdated(self):
		if self.storage:
			self.session.openWithCallback(self.dogetSourceUpdated, MessageBox, language.get(lang, "101"), MessageBox.TYPE_YESNO)

	def dogetSourceUpdated(self, answer):
		try:
			urlnorhap = 'https://github.com/norhap/IPtoSAT/archive/refs/heads/main.zip'
			norhaprepository = get(urlnorhap, timeout=10)
			if answer:
				if exists(str(BUILDBOUQUETS_SOURCE)):
					move(BUILDBOUQUETS_SOURCE, BUILDBOUQUETS_FILE)
				self.session.open(MessageBox, language.get(lang, "103"), MessageBox.TYPE_INFO, simple=True)
				with open(str(self.folderlistchannels) + "/" + "IPtoSAT-main.zip", "wb") as source:
					source.write(norhaprepository.content)
				eConsoleAppContainer().execute('cd ' + self.folderlistchannels + ' && unzip IPtoSAT-main.zip && rm -f ' + SOURCE_PATH + "keymap.xml" + " " + SOURCE_PATH + "icon.png" + " " + SOURCE_PATH + "buildbouquets" + " " + LANGUAGE_PATH + " " + VERSION_PATH + ' && cp -f ' + self.folderlistchannels + '/IPtoSAT-main/src/etc/enigma2/iptosatreferences ' + ENIGMA2_PATH + '/ && cp -f ' + self.folderlistchannels + '/IPtoSAT-main/src/IPtoSAT/* ' + SOURCE_PATH + ' && /sbin/init 4 && sleep 5 && /sbin/init 3 && sleep 35 && rm -rf ' + self.folderlistchannels + "/* " + SOURCE_PATH + '*.py')
		except Exception as err:
			self.session.open(MessageBox, "ERROR: %s" % str(err), MessageBox.TYPE_ERROR, default=False, timeout=10)

	def doInstallChannelsList(self, answer):
		from zipfile import ZipFile
		channelslists = self["list"].getCurrent()
		if answer:
			self.session.open(MessageBox, language.get(lang, "77") + str(channelslists), MessageBox.TYPE_INFO, simple=True)
			dirpath = ""
			try:
				urljungle = 'https://github.com/jungla-team/Canales-enigma2/archive/refs/heads/main.zip'
				urlnorhap = 'https://github.com/norhap/channelslists/archive/refs/heads/main.zip'
				junglerepository = get(urljungle, timeout=10)
				norhaprepository = get(urlnorhap, timeout=10)
				tuxboxrepository = get(self.tuxboxxml, timeout=10)
				with open(str(self.zip_tuxbox_xml), "wb") as xml:
					xml.write(tuxboxrepository.content)
				if exists(str(self.zip_tuxbox_xml)):
					with ZipFile(self.zip_tuxbox_xml, 'r') as zipfile:
						zipfile.extractall(self.folderlistchannels)
				with open(CHANNELS_LISTS_PATH, 'w') as fw:
					fw.write("{" + "\n" + '	"channelslists": []' + "\n" + "}")
				if "Jungle-" in channelslists:
					dirpath = self.folderlistchannels + '/**/' + channelslists.split()[0] + '/etc/enigma2'
					with open(str(self.zip_jungle), "wb") as jungle:
						jungle.write(junglerepository.content)
					with ZipFile(self.zip_jungle, 'r') as zipfile:
						zipfile.extractall(self.folderlistchannels)
				if "Sorys-" in channelslists or "Vuplusmania-" in channelslists:
					dirpath = self.folderlistchannels + '/**/' + channelslists.split()[0]
					with open(str(self.zip_sorys_vuplusmania), "wb") as norhap:
						norhap.write(norhaprepository.content)
					with ZipFile(self.zip_sorys_vuplusmania, 'r') as zipfile:
						zipfile.extractall(self.folderlistchannels)
				for dirnewlist in glob(dirpath, recursive=True):
					for files in [x for x in listdir(dirnewlist) if x.endswith("actualizacion")]:
						updatefiles = join(dirnewlist, files)
						if exists(str(updatefiles)):
							remove(updatefiles)
						for installedlist in [x for x in listdir(ENIGMA2_PATH) if "alternatives." in x or "whitelist" in x or "lamedb" in x or "satellites.xml" in x or "atsc.xml" in x or "terrestrial.xml" in x or ".radio" in x or ".tv" in x or "blacklist" in x]:
							installedfiles = join(ENIGMA2_PATH, installedlist)
							if installedfiles:
								remove(installedfiles)
					if exists(self.folderlistchannels + '/tuxbox-xml-master'):
						eConsoleAppContainer().execute('init 4 && sleep 10 && mv -f ' + dirnewlist + '/*.xml' + " " + FILES_TUXBOX + '/ && cp -a ' + dirnewlist + '/*' + " " + ENIGMA2_PATH_LISTS + ' && cp -a ' + self.folderlistchannels + '/tuxbox-xml-master/xml/*.xml ' + FILES_TUXBOX + '/ && init 3')
					else:
						eConsoleAppContainer().execute('init 4 && sleep 10 && mv -f ' + dirnewlist + '/*.xml' + " " + FILES_TUXBOX + '/ && cp -a ' + dirnewlist + '/*' + " " + ENIGMA2_PATH_LISTS + ' && init 3')
				workdirectory = self.folderlistchannels + '/*'
				for dirfiles in glob(workdirectory, recursive=True):
					if exists(str(dirfiles)):
						eConsoleAppContainer().execute('sleep 15 && rm -rf ' + dirfiles)
			except Exception as err:
				self.session.open(MessageBox, "ERROR: %s" % str(err), MessageBox.TYPE_ERROR, default=False, timeout=10)

	def goRight(self):
		self["list"].pageDown()

	def goLeft(self):
		self["list"].pageUp()

	def moveUp(self):
		self["list"].up()

	def moveDown(self):
		self["list"].down()

	def pageUp(self):
		self["list"].pageUp()

	def pageDown(self):
		self["list"].pageDown()


def startMainMenu(menuid, **kwargs):
	if menuid != "mainmenu":
		return []
	return [("IPToSAT", iptosatSetup, "iptosat_menu", 1)]


def autostart(reason, **kwargs):
	if reason == 0:
		if config.plugins.IPToSAT.enable.value:
			if fileExists('/usr/bin/{}'.format(config.plugins.IPToSAT.player.value)):
				IPToSAT(kwargs["session"])
			else:
				log("Cannot start IPToSAT, {} not found".format(config.plugins.IPToSAT.player.value))


def iptosatSetup(session, **kwargs):
	session.open(IPToSATSetup)


def Plugins(**kwargs):
	Descriptors = []
	Descriptors.append(PluginDescriptor(where=[PluginDescriptor.WHERE_SESSIONSTART], fnc=autostart))
	Descriptors.append(PluginDescriptor(name="IPToSAT", description=language.get(lang, "Synchronize and view satellite channels through IPTV. Setup" + " " + "{}".format(VERSION) + " " + "by norhap"), icon="icon.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=iptosatSetup))
	if config.plugins.IPToSAT.mainmenu.value:
		Descriptors.append(PluginDescriptor(where=[PluginDescriptor.WHERE_MENU], fnc=startMainMenu))
	return Descriptors
