from enigma import iPlayableService, iServiceInformation, iFrontendInformation, eDVBDB, eTimer, gRGB, eConsoleAppContainer, getDesktop
from boxbranding import getBoxType  # MODEL import from getBoxType for all images OE
from requests import get
from urllib.request import urlopen, Request
from urllib.parse import urlparse
from twisted.web.client import getPage
from datetime import datetime
from json import dump, loads
from glob import glob
from os import listdir, makedirs, remove, unlink, symlink
from os.path import join, exists, normpath, islink
from configparser import ConfigParser
from time import sleep, localtime, mktime, time
from shutil import move, copy
from re import search
from sys import stdout, version_info
from RecordTimer import RecordTimerEntry
from ServiceReference import ServiceReference
from timer import TimerEntry
from Tools.Directories import SCOPE_CONFIG, SCOPE_PLUGINS, fileContains, fileExists, isPluginInstalled, resolveFilename
from Tools.Notifications import AddPopup
from Plugins.Plugin import PluginDescriptor
from Components.config import config, getConfigListEntry, ConfigClock, ConfigSelection, ConfigYesNo, ConfigText, ConfigSubsection, ConfigEnableDisable, ConfigSubDict
from Components.ActionMap import ActionMap
from Components.ServiceEventTracker import ServiceEventTracker
from Components.ConfigList import ConfigListScreen
from Components.MenuList import MenuList
from Components.Label import Label
from Components.SystemInfo import BoxInfo, SystemInfo
from Components.Sources.StaticText import StaticText
from Components.Console import Console
from Components.Harddisk import harddiskmanager
from Screens.Screen import Screen
from Screens.ChannelSelection import ChannelSelectionBase
from Screens.MessageBox import MessageBox
from Screens.Standby import TryQuitMainloop
import NavigationInstance

refSat = None
notresetchannels = False
clearCacheEPG = False

# HTTPS twisted client
try:
	from twisted.internet import ssl
	from twisted.internet._sslverify import ClientTLSOptions
	sslverify = True
except ImportError:
	sslverify = False


if sslverify:
	class SSLFactory(ssl.ClientContextFactory):
		def __init__(self, hostname=None):
			self.hostname = hostname

		def getContext(self):
			context = self._contextFactory(self.method)
			if self.hostname:
				ClientTLSOptions(self.hostname, context)
			return context
# END HTTPS twisted client


def playersList():
	if not fileExists('/var/lib/dpkg/status'):
		# Fixed DreamOS by. audi06_19 , gst-play-1.0
		return [("exteplayer3", "ExtEplayer3"), ("gstplayer", "GstPlayer"),]
	else:
		return [("gst-play-1.0", "OE-2.5 Player"), ("exteplayer3", "ExtEplayer3"),]


LANGUAGE_PATH = resolveFilename(SCOPE_PLUGINS, "Extensions/IPToSAT/languages")
lang = config.osd.language.value[:-3] if fileContains(LANGUAGE_PATH, "[" + config.osd.language.value[:-3] + "]") else "en"
language = ConfigParser()
language.read(LANGUAGE_PATH, encoding="utf8")
screenWidth = getDesktop(0).size().width()
MODEL = getBoxType()
PLAYLIST_PATH = resolveFilename(SCOPE_CONFIG, "iptosat.json")
CHANNELS_LISTS_PATH = resolveFilename(SCOPE_CONFIG, "iptosatchlist.json")
SUSCRIPTION_USER_DATA = resolveFilename(SCOPE_CONFIG, "suscriptiondata")
BUILDBOUQUETS_FILE = resolveFilename(SCOPE_PLUGINS, "Extensions/IPToSAT/buildbouquets")
BUILDBOUQUETS_SOURCE = resolveFilename(SCOPE_PLUGINS, "Extensions/IPToSAT/buildbouquets.py")
EPG_CHANNELS_XML = resolveFilename(SCOPE_PLUGINS, "Extensions/IPToSAT/iptosat.channels.xml")
EPG_SOURCES_XML = resolveFilename(SCOPE_PLUGINS, "Extensions/IPToSAT/iptosat.sources.xml")
EPG_CONFIG = resolveFilename(SCOPE_PLUGINS, "Extensions/IPToSAT/epgimport.conf")
FOLDER_EPGIMPORT = "/etc/epgimport/"
ENIGMA2_PATH = "/etc/enigma2"
EPG_IMPORT_CONFIG = ENIGMA2_PATH + "/epgimport.conf"
EPG_IMPORT_CONFIG_BACK = ENIGMA2_PATH + "/epgimport.conf.back"
REFERENCES_FILE = resolveFilename(SCOPE_CONFIG, "iptosatreferences")
CONFIG_PATH_CATEGORIES = resolveFilename(SCOPE_CONFIG, "iptosatcategories.json")
WILD_CARD_ALL_CATEGORIES = resolveFilename(SCOPE_CONFIG, "iptosatcatall")
WILD_CARD_CATYOURLIST = resolveFilename(SCOPE_CONFIG, "iptosatyourcatall")
BACKUP_CATEGORIES = "iptosatyourcatbackup"
WILD_CARD_CATEGORIES_FILE = resolveFilename(SCOPE_CONFIG, "wildcardcategories")
ALL_CATEGORIES = resolveFilename(SCOPE_CONFIG, "iptosatcategoriesall.json")
CATEGORIES_TIMER_OK = "/tmp/timercatiptosat.log"
TIMER_OK = ""
CATEGORIES_TIMER_ERROR = "/tmp/timercatiptosat_error.log"
TIMER_ERROR = ""
USER_LIST_CATEGORIE_CHOSEN = ""
USER_EDIT_CATEGORIE = ""
CONFIG_PATH = resolveFilename(SCOPE_CONFIG, "iptosat.conf")
SOURCE_PATH = resolveFilename(SCOPE_PLUGINS, "Extensions/IPToSAT")
VERSION_PATH = resolveFilename(SCOPE_PLUGINS, "Extensions/IPToSAT/version")
IPToSAT_EPG_PATH = resolveFilename(SCOPE_CONFIG, "userbouquet.iptosat_epg.tv")
FILE_IPToSAT_EPG = "userbouquet.iptosat_epg.tv"
BOUQUETS_TV = resolveFilename(SCOPE_CONFIG, "bouquets.tv")
BOUQUET_IPTV_NORHAP = resolveFilename(SCOPE_CONFIG, "userbouquet.iptosat_norhap.tv")
WILD_CARD_EPG_FILE = resolveFilename(SCOPE_CONFIG, "wildcardepg")
WILD_CARD_BOUQUETSTV = resolveFilename(SCOPE_CONFIG, "wildcardbouquetstv")
ENIGMA2_PATH_LISTS = resolveFilename(SCOPE_CONFIG)
FILES_TUXBOX = "/etc/tuxbox"
FOLDER_OSCAM = ""
SCRIPT_OSCAM = ""
FILES_TUXBOX_CONFIG = "/etc/tuxbox/config"
USR_SCRIPT = "/usr/script"
ETC_INITD = "/etc/init.d"

if isPluginInstalled("EPGImport") and not exists(FOLDER_EPGIMPORT + "iptosat.channels.xml") and exists(FOLDER_EPGIMPORT + "rytec.sources.xml") and lang == "es":
	eConsoleAppContainer().execute('cp -f ' + EPG_CHANNELS_XML + " " + FOLDER_EPGIMPORT + ' ; cp -f ' + EPG_SOURCES_XML + " " + FOLDER_EPGIMPORT)

if exists(FILES_TUXBOX_CONFIG):
	for oscamfolder in [x for x in listdir(FILES_TUXBOX_CONFIG) if "oscam" in x]:
		FOLDER_OSCAM = FILES_TUXBOX_CONFIG + "/" + oscamfolder
		continue
if BoxInfo.getItem("distro") != "openspa":
	for oscamscript in [x for x in listdir(ETC_INITD) if "softcam.oscam" in x]:
		SCRIPT_OSCAM = ETC_INITD + "/" + oscamscript
		continue
elif exists(USR_SCRIPT):
	for oscamscript in [x for x in listdir(USR_SCRIPT) if "Oscam" in x]:
		SCRIPT_OSCAM = USR_SCRIPT + "/" + oscamscript
		continue

RESTART_OSCAM = str(SCRIPT_OSCAM) + " stop && " + str(SCRIPT_OSCAM) + " start"
OSCAM_PATH = FOLDER_OSCAM + "/"
OSCAM_SERVER = OSCAM_PATH + "oscam.server"
OSCAM_SERVICES = OSCAM_PATH + "oscam.services"
OSCAM_CARD = OSCAM_PATH + "oscam.services.card"
OSCAM_NO_CARD = OSCAM_PATH + "oscam.services.no.card"
OSCAM_SERVICES_IPTOSAT = resolveFilename(SCOPE_PLUGINS, "Extensions/IPToSAT/oscam.services.no.card")
OSCAM_SERVICES_CARD = resolveFilename(SCOPE_PLUGINS, "Extensions/IPToSAT/oscam.services.card")
TOKEN_ZEROTIER = "/var/lib/zerotier-one/authtoken.secret"
FOLDER_TOKEN_ZEROTIER = "/var/lib/zerotier-one"

config.plugins.IPToSAT = ConfigSubsection()
config.plugins.IPToSAT.enable = ConfigYesNo(default=True) if fileContains(PLAYLIST_PATH, '"sref": "') else ConfigYesNo(default=False)
config.plugins.IPToSAT.mainmenu = ConfigYesNo(default=False)
config.plugins.IPToSAT.showuserdata = ConfigYesNo(default=True)
config.plugins.IPToSAT.usercategories = ConfigYesNo(default=False)
config.plugins.IPToSAT.deletecategories = ConfigYesNo(default=False)
config.plugins.IPToSAT.autotimerbouquets = ConfigYesNo(default=False)
config.plugins.IPToSAT.player = ConfigSelection(default="exteplayer3", choices=playersList())
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
if BoxInfo.getItem("distro") in ("norhap", "openspa"):
	config.plugins.IPToSAT.sequencetimers = ConfigYesNo(default=False)
	config.plugins.IPToSAT.timerscard = ConfigYesNo(default=False)
	config.plugins.IPToSAT.timecardon = ConfigSubDict()
	config.plugins.IPToSAT.timecardoff = ConfigSubDict()
	config.plugins.IPToSAT.cardday = ConfigSubDict()
	for day in range(0, 2):
		config.plugins.IPToSAT.cardday[day] = ConfigEnableDisable(default=False)
		config.plugins.IPToSAT.timecardon[day] = ConfigClock(default=((23 * 60) * 60))
		config.plugins.IPToSAT.timecardoff[day] = ConfigClock(default=((20 * 60 + 5) * 60))
	for day in range(1, 5):
		config.plugins.IPToSAT.cardday[day] = ConfigEnableDisable(default=False)
		config.plugins.IPToSAT.timecardon[day] = ConfigClock(default=((23 * 60) * 60))
		config.plugins.IPToSAT.timecardoff[day] = ConfigClock(default=((19 * 60 + 30) * 60))
	for day in range(5, 7):
		config.plugins.IPToSAT.cardday[day] = ConfigEnableDisable(default=False)
		config.plugins.IPToSAT.timecardon[day] = ConfigClock(default=((23 * 60) * 60))
		config.plugins.IPToSAT.timecardoff[day] = ConfigClock(default=((11 * 60) * 60))


def getTokenZerotier():
	with open(TOKEN_ZEROTIER, "r") as token:
		return token.read()


def getDataZerotier(data):
	network = get("http://127.0.0.1:9993/" + data, headers={'X-ZT1-Auth': getTokenZerotier(), 'Content-Type': 'application/json'}).text
	return network


def checkZerotierMember():
	zerotierdata = loads(getDataZerotier("network"))
	for data in zerotierdata:
		status = data.get("status")
		return True if str(status).upper() == "OK" else False


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


def allowsMultipleRecordings():
	if exists(SUSCRIPTION_USER_DATA):
		with open(SUSCRIPTION_USER_DATA, "r") as line:
			for userdata in line:
				max_connections = userdata.split('"max_connections": "')[1].split('", "allowed_output_formats"')[0]
				if int(max_connections) > 1:
					return True
			return False


def isIPToSAT():
	try:
		if PLAYLIST_PATH and config.plugins.IPToSAT.enable.value:
			with open(PLAYLIST_PATH, "r") as fr:
				for refiptosat in fr.readlines():
					currentService = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
					if currentService:
						if currentService.toString() in refiptosat:
							return True
				return False
	except Exception:
		pass


def getUserDataSuscription():
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


def killActivePlayer():
	from process import ProcessList  # noqa: E402
	exteplayer3 = str(ProcessList().named("exteplayer3")).strip("[]")
	gstplayer = str(ProcessList().named("gstplayer")).strip("[]")
	if exteplayer3:
		Console().ePopen(f'kill -9 {exteplayer3}')
	elif gstplayer:
		Console().ePopen(f'kill -9 {gstplayer}')


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
		<widget source="key_blue" conditional="key_blue" render="Label" objectTypes="key_blue,StaticText" position="720,872" zPosition="2" size="190,52" backgroundColor="key_blue" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
			<convert type="ConditionalShowHide"/>
		</widget>
		<widget source="VKeyIcon" text="TEXT" render="Label" position="543,872" size="165,52" zPosition="2" backgroundColor="key_back" conditional="VKeyIcon" font="Regular;22" foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="session.VideoPicture" render="Pig" position="985,10" size="870,500" zPosition="1" backgroundColor="#df0b1300"/>
		<widget name="HelpWindow" position="1010,855" size="0,0" alphaTest="blend" conditional="HelpWindow" transparent="1" zPosition="+1" />
		<widget name="description" font="Regular;26" position="985,520" size="860,280" foregroundColor="#00e5e619" transparent="1" verticalAlignment="top"/>
		<widget name="footnote" conditional="footnote" position="985,802" size="860,120" foregroundColor="#0086dc3d" font="Regular;25" transparent="1" zPosition="3" />
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
		try:
			self.currentservice = self.session.nav.getCurrentlyPlayingServiceReference().toString()
		except:
			self.currentservice = False
		self.timerupdatebouquets = config.plugins.IPToSAT.timebouquets.value[0] + config.plugins.IPToSAT.timebouquets.value[1]
		self.typecategories = config.plugins.IPToSAT.typecategories.value
		self.onLayoutFinish.append(self.layoutFinished)
		for partition in harddiskmanager.getMountedPartitions():
			self.path = normpath(partition.mountpoint)
			if self.path != "/" and "net" not in self.path and "autofs" not in self.path:
				if exists(str(self.path)) and listdir(self.path):
					self.storage = True
		if BoxInfo.getItem("distro") in ("norhap", "openspa") and exists(PLAYLIST_PATH):
			if not exists(ENIGMA2_PATH_LISTS + "iptosatjsonall") and not exists(ENIGMA2_PATH_LISTS + "iptosatjsoncard") and exists(str(OSCAM_SERVER)):
				copy(PLAYLIST_PATH, ENIGMA2_PATH_LISTS + "iptosatjsoncard")
				copy(OSCAM_SERVICES_CARD, OSCAM_PATH)
				copy(OSCAM_SERVICES_IPTOSAT, OSCAM_SERVICES)
			if exists(str(OSCAM_SERVER)):
				if exists(ENIGMA2_PATH_LISTS + "iptosatjsoncard") and exists(ENIGMA2_PATH_LISTS + "iptosatjsonall") and exists(str(OSCAM_NO_CARD)):
					self["key_blue"].setText(language.get(lang, "194"))  # noqa: F821
				elif exists(ENIGMA2_PATH_LISTS + "iptosatjsoncard"):
					self["key_blue"].setText(language.get(lang, "195"))  # noqa: F821
				elif exists(ENIGMA2_PATH_LISTS + "iptosatjsonall"):
					self["key_blue"].setText(language.get(lang, "194"))  # noqa: F821
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
		if BoxInfo.getItem("distro") in ("norhap", "openspa") and exists(str(OSCAM_SERVER)):
			self.list.append(getConfigListEntry(language.get(lang, "209"),
				config.plugins.IPToSAT.timerscard))
			if config.plugins.IPToSAT.timerscard.value:
				if BoxInfo.getItem("distro") == "norhap":
					if SystemInfo["FbcTunerPowerAlwaysOn"]:
						self.list.append(getConfigListEntry(language.get(lang, "210"),
							config.plugins.IPToSAT.sequencetimers, language.get(lang, "211")))
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
		self.list.append(getConfigListEntry(language.get(lang, "17"),
			config.plugins.IPToSAT.player, language.get(lang, "38")))
		self.list.append(getConfigListEntry(language.get(lang, "98"),
			config.plugins.IPToSAT.mainmenu, language.get(lang, "38")))
		self.list.append(getConfigListEntry(language.get(lang, "116"), config.plugins.IPToSAT.showuserdata))
		self["config"].list = self.list
		self["config"].setList(self.list)
		self.saveConfig()
		if TimerEntry.StateEnded < int(time()) and BoxInfo.getItem("distro") == "norhap":
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
		if not self.session.nav.getRecordings():
			if exists(resolveFilename(SCOPE_PLUGINS, "Extensions/IPToSAT/lamedb")) and exists(resolveFilename(SCOPE_PLUGINS, "Extensions/IPToSAT/lamedb5")):
				eConsoleAppContainer().execute('init 4 && sleep 5 && mv -f ' + resolveFilename(SCOPE_PLUGINS, "Extensions/IPToSAT/lamedb") + ' ' + resolveFilename(SCOPE_CONFIG, "lamedb") + ' && mv -f ' + resolveFilename(SCOPE_PLUGINS, "Extensions/IPToSAT/lamedb5") + ' ' + resolveFilename(SCOPE_CONFIG, "lamedb5") + ' && init 3')

	def saveConfig(self):
		if fileExists(CONFIG_PATH):
			getUserDataSuscription()
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
		global notresetchannels
		if config.plugins.IPToSAT.typecategories.value == "none":
			self.deleteBouquetsNorhap()
		if self.timerupdatebouquets != config.plugins.IPToSAT.timebouquets.value[0] + config.plugins.IPToSAT.timebouquets.value[1]:
			if exists(str(CATEGORIES_TIMER_ERROR)):
				remove(CATEGORIES_TIMER_ERROR)
			notresetchannels = True
			IPToSAT(self.session)  # update category timer initializer.
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
		AssignService(self)
		self.saveiptosatconf()
		ConfigListScreen.keySave(self)

	def joinZeroTier(self):
		if config.plugins.IPToSAT.showuserdata.value:
			if exists("/usr/sbin/zerotier-one"):
				if not exists(TOKEN_ZEROTIER):
					from process import ProcessList  # noqa: E402
					zerotier_process = str(ProcessList().named('zerotier-one')).strip('[]')
					zerotier_auto = glob("/etc/rc2.d/S*zerotier")
					if not zerotier_process:
						eConsoleAppContainer().execute("/etc/init.d/zerotier start")
					if not zerotier_auto:
						eConsoleAppContainer().execute("update-rc.d -f zerotier defaults")
					if config.plugins.IPToSAT.networkidzerotier.value != config.plugins.IPToSAT.networkidzerotier.default:
						eConsoleAppContainer().execute('sleep 15; zerotier-cli join {}' .format(config.plugins.IPToSAT.networkidzerotier.value))
						self.session.openWithCallback(self.close, MessageBox, language.get(lang, "190"), MessageBox.TYPE_INFO, simple=True, timeout=15)
					else:
						self.session.open(MessageBox, language.get(lang, "192"), MessageBox.TYPE_ERROR, simple=True)
				else:
					if checkZerotierMember():
						self.session.open(MessageBox, language.get(lang, "121"), MessageBox.TYPE_INFO, simple=True)
			else:
				self.session.open(MessageBox, language.get(lang, "193"), MessageBox.TYPE_ERROR, simple=True)

	def IPToSATWithCardOrFull(self):
		if not self.session.nav.getRecordings():
			if BoxInfo.getItem("distro") in ("norhap", "openspa") and exists(str(OSCAM_SERVER)):
				if exists(str(PLAYLIST_PATH)) and exists(str(OSCAM_SERVICES)):
					if exists(str(ENIGMA2_PATH_LISTS + "iptosatjsonall")):
						if exists(str(OSCAM_NO_CARD)):
							self["footnote"].setText(language.get(lang, "212"))
							move(PLAYLIST_PATH, ENIGMA2_PATH_LISTS + "iptosatjsoncard")
							move(ENIGMA2_PATH_LISTS + "iptosatjsonall", PLAYLIST_PATH)
							move(OSCAM_SERVICES, OSCAM_CARD)
							move(OSCAM_NO_CARD, OSCAM_SERVICES)
							self["key_blue"].setText(language.get(lang, "195"))
							if self.currentservice:
								if "http" not in self.currentservice:
									self.session.nav.stopService()
									eConsoleAppContainer().execute('sleep 3 && ' + RESTART_OSCAM + f' && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={self.currentservice}')
									return
						else:
							move(OSCAM_SERVICES, OSCAM_NO_CARD)
							move(OSCAM_CARD, OSCAM_SERVICES)
							if exists(str(OSCAM_NO_CARD)):
								move(PLAYLIST_PATH, ENIGMA2_PATH_LISTS + "iptosatjsoncard")
								move(ENIGMA2_PATH_LISTS + "iptosatjsonall", PLAYLIST_PATH)
								move(OSCAM_SERVICES, OSCAM_CARD)
								move(OSCAM_NO_CARD, OSCAM_SERVICES)
								self["key_blue"].setText(language.get(lang, "195"))
								eConsoleAppContainer().execute("sleep 1 && " + RESTART_OSCAM)
								return
					elif exists(str(ENIGMA2_PATH_LISTS + "iptosatjsoncard")):
						if exists(str(OSCAM_CARD)):
							self["footnote"].setText(language.get(lang, "213"))
							move(PLAYLIST_PATH, ENIGMA2_PATH_LISTS + "iptosatjsonall")
							move(ENIGMA2_PATH_LISTS + "iptosatjsoncard", PLAYLIST_PATH)
							move(OSCAM_SERVICES, OSCAM_NO_CARD)
							move(OSCAM_CARD, OSCAM_SERVICES)
							self["key_blue"].setText(language.get(lang, "194"))
							if self.currentservice:
								if "http" not in self.currentservice:
									self.session.nav.stopService()
									eConsoleAppContainer().execute('sleep 1 && ' + RESTART_OSCAM + f' && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={self.currentservice}')
									return
						else:
							move(OSCAM_SERVICES, OSCAM_CARD)
							move(OSCAM_NO_CARD, OSCAM_SERVICES)
							if exists(str(OSCAM_CARD)):
								move(PLAYLIST_PATH, ENIGMA2_PATH_LISTS + "iptosatjsonall")
								move(ENIGMA2_PATH_LISTS + "iptosatjsoncard", PLAYLIST_PATH)
								move(OSCAM_SERVICES, OSCAM_NO_CARD)
								move(OSCAM_CARD, OSCAM_SERVICES)
								self["key_blue"].setText(language.get(lang, "194"))
								eConsoleAppContainer().execute("sleep 1 && " + RESTART_OSCAM)
		else:
			if BoxInfo.getItem("distro") in ("norhap", "openspa"):
				self.session.open(MessageBox, language.get(lang, "208"), MessageBox.TYPE_INFO, simple=True)

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
		if BoxInfo.getItem("distro") in ("norhap", "openspa"):
			now = localtime(time())
			current_day = int(now.tm_wday)
			if config.plugins.IPToSAT.timerscard.value:
				if config.plugins.IPToSAT.timecardon[current_day].value:  # ignore timer ON for not current day
					self.timercardOn = TimerOnCard()  # card ON timer start
				if config.plugins.IPToSAT.timecardoff[current_day].value:  # ignore timer OFF for not current day
					self.timercardOff = TimerOffCard()  # card OFF timer start
		if exists(CONFIG_PATH):
			with open(CONFIG_PATH, 'w') as self.iptosatconfalternate:
				self.iptosatconfalternate.write("[IPToSAT]" + "\n" + 'Host=' + config.plugins.IPToSAT.domain.value + ":" + config.plugins.IPToSAT.serverport.value + "\n" + "User=" + config.plugins.IPToSAT.username.value + "\n" + "Pass=" + config.plugins.IPToSAT.password.value)
		else:
			with open(CONFIG_PATH, 'w') as self.iptosatconfalternate:
				self.iptosatconfalternate.write("[IPToSAT]" + "\n" + 'Host=http://domain:port' + "\n" + "User=user" + "\n" + "Pass=pass")
		if config.plugins.IPToSAT.showuserdata.value:
			self["key_yellow"] = StaticText(language.get(lang, "189") if exists("/usr/sbin/zerotier-one") else "")  # noqa: F821
			if exists(TOKEN_ZEROTIER):
				self["key_yellow"] = StaticText("" if checkZerotierMember() else language.get(lang, "189"))  # noqa: F821

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
		eConsoleAppContainer().execute('sleep 3 ; wget -qO - http://127.0.0.1/web/servicelistreload?mode=2')


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
		self.Console = Console()
		self.categoriestimer.stop()
		now = int(time())
		wake = self.getTimeDownloadCategories()
		self.m3ufile = join(ENIGMA2_PATH, "iptosat_norhap.m3u")
		m3u = ""
		hostport = config.plugins.IPToSAT.domain.value + ":" + config.plugins.IPToSAT.serverport.value
		# try:
		# 	urlm3u = str(hostport) + '/get.php?username=' + str(config.plugins.IPToSAT.username.value) + '&password=' + str(config.plugins.IPToSAT.password.value) + '&type=m3u_plus&output=ts'
		# 	m3u = get(urlm3u, allow_redirects=True)
		# except Exception:
		# 	try:
		# 		urlm3u = str(hostport) + '/get.php?username=' + str(config.plugins.IPToSAT.username.value) + '&password=' + str(config.plugins.IPToSAT.password.value) + '&type=m3u_plus&output=m3u8'
		# 		m3u = get(urlm3u, allow_redirects=True)
		url = str(hostport) + '/get.php?username=' + str(config.plugins.IPToSAT.username.value) + '&password=' + str(config.plugins.IPToSAT.password.value) + '&type=m3u_plus&output=ts'
		user_agent = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'
		headers = {'User-Agent': user_agent}
		request = Request(url, None, headers)
		try:
			with urlopen(request) as response:
				m3u = response.read()
		except Exception as err:
			with open(CATEGORIES_TIMER_ERROR, "w") as fw:
				fw.write(str(err))
		if wake - now < 60 and config.plugins.IPToSAT.autotimerbouquets.value:
			if exists(str(CATEGORIES_TIMER_ERROR)):
				remove(CATEGORIES_TIMER_ERROR)
			if exists(str(CATEGORIES_TIMER_OK)):
				remove(CATEGORIES_TIMER_OK)
			try:
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
					with open(str(self.m3ufile), "wb") as m3ufile:
						m3ufile.write(m3u)  # m3ufile.write(m3u.content) with get
					with open(str(self.m3ufile), "r") as m3uread:
						charactertoreplace = m3uread.readlines()
						with open(str(self.m3ufile), "w") as m3uw:
							for line in charactertoreplace:
								if '[' in line and ']' in line and '|' in line:
									line = line.replace('[', '').replace(']', '|')
								if '|  ' in line:
									line = line.replace('|  ', '| ')
								m3uw.write(line)
					if exists(str(BUILDBOUQUETS_FILE)):
						move(BUILDBOUQUETS_FILE, BUILDBOUQUETS_SOURCE)
					with open(CATEGORIES_TIMER_OK, "w") as fw:
						now = datetime.now().strftime("%A %-d %B") + " " + language.get(lang, "170") + " " + datetime.now().strftime("%H:%M")
						fw.write(now)
					eConsoleAppContainer().execute('sleep 3 ; python' + str(version_info.major) + ' ' + str(BUILDBOUQUETS_SOURCE) + " ; mv " + str(BOUQUET_IPTV_NORHAP) + ".del" + " " + str(BOUQUET_IPTV_NORHAP) + " ; wget -qO - http://127.0.0.1/web/servicelistreload?mode=2 ; rm -f " + str(self.m3ufile) + " ; mv " + str(BUILDBOUQUETS_SOURCE) + " " + str(BUILDBOUQUETS_FILE) + " ; echo 1 > /proc/sys/vm/drop_caches ; echo 2 > /proc/sys/vm/drop_caches ; echo 3 > /proc/sys/vm/drop_caches")
					if isPluginInstalled("EPGImport") and exists(FOLDER_EPGIMPORT + "iptosat.channels.xml") and exists(EPG_CHANNELS_XML):
						self.Console.ePopen(['sleep 0'], self.runEPGIMPORT)
					if self.storage:
						eConsoleAppContainer().execute('rm -f ' + str(self.m3ustoragefile) + " ; cp " + str(self.m3ufile) + " " + str(self.m3ustoragefile))
				else:
					if m3u:
						with open(CATEGORIES_TIMER_ERROR, "w") as fw:
							fw.write(language.get(lang, "156"))
			except Exception as err:
				with open(CATEGORIES_TIMER_ERROR, "w") as fw:
					fw.write(str(err))

	def runEPGIMPORT(self, result=None, retVal=None, extra_args=None):
		global clearCacheEPG
		if config.plugins.epgimport.clear_oldepg.value:
			clearCacheEPG = True
			config.plugins.epgimport.clear_oldepg.value = False
			config.plugins.epgimport.clear_oldepg.save()
		if exists(EPG_IMPORT_CONFIG) and not exists(EPG_IMPORT_CONFIG_BACK):
			move(EPG_IMPORT_CONFIG, EPG_IMPORT_CONFIG_BACK)
		if not islink(EPG_IMPORT_CONFIG) and exists(EPG_CONFIG) and exists(EPG_IMPORT_CONFIG_BACK):
			symlink(EPG_CONFIG, EPG_IMPORT_CONFIG)
		if islink(EPG_IMPORT_CONFIG):
			from Plugins.Extensions.EPGImport.plugin import autoStartTimer  # noqa: E402
			autoStartTimer.runImport()
			self.Console = Console()
			self.Console.ePopen(['sleep 2'], self.finishedEPGIMPORT)

	def finishedEPGIMPORT(self, result=None, retVal=None, extra_args=None):
		global clearCacheEPG
		if clearCacheEPG is True:
			config.plugins.epgimport.clear_oldepg.value = True
			config.plugins.epgimport.clear_oldepg.save()
		if exists(EPG_IMPORT_CONFIG_BACK):
			unlink(EPG_IMPORT_CONFIG)
			move(EPG_IMPORT_CONFIG_BACK, EPG_IMPORT_CONFIG)

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
	def __init__(self):
		self.cardofftimer = eTimer()
		self.cardofftimer.callback.append(self.iptosatCardOffTimer)
		self.cardpolltimer = eTimer()
		self.cardpolltimer.timeout.get().append(self.cardPollTimer)
		self.refreshTimerCard()

	def cardPollTimer(self):
		self.cardpolltimer.stop()
		self.scheduledtime = self.prepareTimer()

	def getTimeOffCard(self):
		now = localtime(time())
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

	def sequencetimers(self, currentservice):
		eConsoleAppContainer().execute("sleep 625 ; mv " + PLAYLIST_PATH + " " + ENIGMA2_PATH_LISTS + "iptosatjsonall ; mv " + ENIGMA2_PATH_LISTS + "iptosatjsoncard " + PLAYLIST_PATH + " ; mv " + OSCAM_SERVICES + " " + OSCAM_NO_CARD + " ; mv " + OSCAM_CARD + " " + OSCAM_SERVICES + f' && /etc/init.d/softcam.oscam restart && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={config.servicelist.startupservice.value}')
		eConsoleAppContainer().execute(f'sleep 628 && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={currentservice}')
		eConsoleAppContainer().execute("sleep 900 ; mv " + PLAYLIST_PATH + " " + ENIGMA2_PATH_LISTS + "iptosatjsoncard ; mv " + ENIGMA2_PATH_LISTS + "iptosatjsonall " + PLAYLIST_PATH + " ; mv " + OSCAM_SERVICES + " " + OSCAM_CARD + " ; mv " + OSCAM_NO_CARD + " " + OSCAM_SERVICES + f' && /etc/init.d/softcam.oscam restart && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={config.servicelist.startupservice.value}')
		eConsoleAppContainer().execute(f'sleep 903 && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={currentservice}')
		eConsoleAppContainer().execute("sleep 1530 ; mv " + PLAYLIST_PATH + " " + ENIGMA2_PATH_LISTS + "iptosatjsonall ; mv " + ENIGMA2_PATH_LISTS + "iptosatjsoncard " + PLAYLIST_PATH + " ; mv " + OSCAM_SERVICES + " " + OSCAM_NO_CARD + " ; mv " + OSCAM_CARD + " " + OSCAM_SERVICES + f' && /etc/init.d/softcam.oscam restart && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={config.servicelist.startupservice.value}')
		eConsoleAppContainer().execute(f'sleep 1533 && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={currentservice}')
		eConsoleAppContainer().execute("sleep 1800 ; mv " + PLAYLIST_PATH + " " + ENIGMA2_PATH_LISTS + "iptosatjsoncard ; mv " + ENIGMA2_PATH_LISTS + "iptosatjsonall " + PLAYLIST_PATH + " ; mv " + OSCAM_SERVICES + " " + OSCAM_CARD + " ; mv " + OSCAM_NO_CARD + " " + OSCAM_SERVICES + f' && /etc/init.d/softcam.oscam restart && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={config.servicelist.startupservice.value}')
		eConsoleAppContainer().execute(f'sleep 1803 && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={currentservice}')
		eConsoleAppContainer().execute("sleep 2430 ; mv " + PLAYLIST_PATH + " " + ENIGMA2_PATH_LISTS + "iptosatjsonall ; mv " + ENIGMA2_PATH_LISTS + "iptosatjsoncard " + PLAYLIST_PATH + " ; mv " + OSCAM_SERVICES + " " + OSCAM_NO_CARD + " ; mv " + OSCAM_CARD + " " + OSCAM_SERVICES + f' && /etc/init.d/softcam.oscam restart && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={config.servicelist.startupservice.value}')
		eConsoleAppContainer().execute(f'sleep 2433 && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={currentservice}')
		eConsoleAppContainer().execute("sleep 2700 ; mv " + PLAYLIST_PATH + " " + ENIGMA2_PATH_LISTS + "iptosatjsoncard ; mv " + ENIGMA2_PATH_LISTS + "iptosatjsonall " + PLAYLIST_PATH + " ; mv " + OSCAM_SERVICES + " " + OSCAM_CARD + " ; mv " + OSCAM_NO_CARD + " " + OSCAM_SERVICES + f' && /etc/init.d/softcam.oscam restart && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={config.servicelist.startupservice.value}')
		eConsoleAppContainer().execute(f'sleep 2703 && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={currentservice}')
		eConsoleAppContainer().execute("sleep 3330 ; mv " + PLAYLIST_PATH + " " + ENIGMA2_PATH_LISTS + "iptosatjsonall ; mv " + ENIGMA2_PATH_LISTS + "iptosatjsoncard " + PLAYLIST_PATH + " ; mv " + OSCAM_SERVICES + " " + OSCAM_NO_CARD + " ; mv " + OSCAM_CARD + " " + OSCAM_SERVICES + f' && /etc/init.d/softcam.oscam restart && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={config.servicelist.startupservice.value}')
		eConsoleAppContainer().execute(f'sleep 3333 && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={currentservice}')
		eConsoleAppContainer().execute("sleep 3600 ; mv " + PLAYLIST_PATH + " " + ENIGMA2_PATH_LISTS + "iptosatjsoncard ; mv " + ENIGMA2_PATH_LISTS + "iptosatjsonall " + PLAYLIST_PATH + " ; mv " + OSCAM_SERVICES + " " + OSCAM_CARD + " ; mv " + OSCAM_NO_CARD + " " + OSCAM_SERVICES + f' && /etc/init.d/softcam.oscam restart && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={config.servicelist.startupservice.value}')
		eConsoleAppContainer().execute(f'sleep 3603 && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={currentservice}')
		eConsoleAppContainer().execute("sleep 4230 ; mv " + PLAYLIST_PATH + " " + ENIGMA2_PATH_LISTS + "iptosatjsonall ; mv " + ENIGMA2_PATH_LISTS + "iptosatjsoncard " + PLAYLIST_PATH + " ; mv " + OSCAM_SERVICES + " " + OSCAM_NO_CARD + " ; mv " + OSCAM_CARD + " " + OSCAM_SERVICES + f' && /etc/init.d/softcam.oscam restart && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={config.servicelist.startupservice.value}')
		eConsoleAppContainer().execute(f'sleep 4233 && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={currentservice}')
		eConsoleAppContainer().execute("sleep 4500 ; mv " + PLAYLIST_PATH + " " + ENIGMA2_PATH_LISTS + "iptosatjsoncard ; mv " + ENIGMA2_PATH_LISTS + "iptosatjsonall " + PLAYLIST_PATH + " ; mv " + OSCAM_SERVICES + " " + OSCAM_CARD + " ; mv " + OSCAM_NO_CARD + " " + OSCAM_SERVICES + f' && /etc/init.d/softcam.oscam restart && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={config.servicelist.startupservice.value}')
		eConsoleAppContainer().execute(f'sleep 4503 && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={currentservice}')
		eConsoleAppContainer().execute("sleep 5130 ; mv " + PLAYLIST_PATH + " " + ENIGMA2_PATH_LISTS + "iptosatjsonall ; mv " + ENIGMA2_PATH_LISTS + "iptosatjsoncard " + PLAYLIST_PATH + " ; mv " + OSCAM_SERVICES + " " + OSCAM_NO_CARD + " ; mv " + OSCAM_CARD + " " + OSCAM_SERVICES + f' && /etc/init.d/softcam.oscam restart && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={config.servicelist.startupservice.value}')
		eConsoleAppContainer().execute(f'sleep 5133 && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={currentservice}')
		eConsoleAppContainer().execute("sleep 5400 ; mv " + PLAYLIST_PATH + " " + ENIGMA2_PATH_LISTS + "iptosatjsoncard ; mv " + ENIGMA2_PATH_LISTS + "iptosatjsonall " + PLAYLIST_PATH + " ; mv " + OSCAM_SERVICES + " " + OSCAM_CARD + " ; mv " + OSCAM_NO_CARD + " " + OSCAM_SERVICES + f' && /etc/init.d/softcam.oscam restart && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={config.servicelist.startupservice.value}')
		eConsoleAppContainer().execute(f'sleep 5403 && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={currentservice}')
		eConsoleAppContainer().execute("sleep 6030 ; mv " + PLAYLIST_PATH + " " + ENIGMA2_PATH_LISTS + "iptosatjsonall ; mv " + ENIGMA2_PATH_LISTS + "iptosatjsoncard " + PLAYLIST_PATH + " ; mv " + OSCAM_SERVICES + " " + OSCAM_NO_CARD + " ; mv " + OSCAM_CARD + " " + OSCAM_SERVICES + f' && /etc/init.d/softcam.oscam restart && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={config.servicelist.startupservice.value}')
		eConsoleAppContainer().execute(f'sleep 6033 && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={currentservice}')
		eConsoleAppContainer().execute("sleep 6300 ; mv " + PLAYLIST_PATH + " " + ENIGMA2_PATH_LISTS + "iptosatjsoncard ; mv " + ENIGMA2_PATH_LISTS + "iptosatjsonall " + PLAYLIST_PATH + " ; mv " + OSCAM_SERVICES + " " + OSCAM_CARD + " ; mv " + OSCAM_NO_CARD + " " + OSCAM_SERVICES + f' && /etc/init.d/softcam.oscam restart && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={config.servicelist.startupservice.value}')
		eConsoleAppContainer().execute(f'sleep 6303 && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={currentservice}')
		eConsoleAppContainer().execute("sleep 6930 ; mv " + PLAYLIST_PATH + " " + ENIGMA2_PATH_LISTS + "iptosatjsonall ; mv " + ENIGMA2_PATH_LISTS + "iptosatjsoncard " + PLAYLIST_PATH + " ; mv " + OSCAM_SERVICES + " " + OSCAM_NO_CARD + " ; mv " + OSCAM_CARD + " " + OSCAM_SERVICES + f' && /etc/init.d/softcam.oscam restart && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={config.servicelist.startupservice.value}')
		eConsoleAppContainer().execute(f'sleep 6933 && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={currentservice}')
		eConsoleAppContainer().execute("sleep 7200 ; mv " + PLAYLIST_PATH + " " + ENIGMA2_PATH_LISTS + "iptosatjsoncard ; mv " + ENIGMA2_PATH_LISTS + "iptosatjsonall " + PLAYLIST_PATH + " ; mv " + OSCAM_SERVICES + " " + OSCAM_CARD + " ; mv " + OSCAM_NO_CARD + " " + OSCAM_SERVICES + f' && /etc/init.d/softcam.oscam restart && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={config.servicelist.startupservice.value}')
		eConsoleAppContainer().execute(f'sleep 7203 && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={currentservice}')
		eConsoleAppContainer().execute("sleep 7830 ; mv " + PLAYLIST_PATH + " " + ENIGMA2_PATH_LISTS + "iptosatjsonall ; mv " + ENIGMA2_PATH_LISTS + "iptosatjsoncard " + PLAYLIST_PATH + " ; mv " + OSCAM_SERVICES + " " + OSCAM_NO_CARD + " ; mv " + OSCAM_CARD + " " + OSCAM_SERVICES + f' && /etc/init.d/softcam.oscam restart && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={config.servicelist.startupservice.value}')
		eConsoleAppContainer().execute(f'sleep 7833 && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={currentservice}')
		eConsoleAppContainer().execute("sleep 8100 ; mv " + PLAYLIST_PATH + " " + ENIGMA2_PATH_LISTS + "iptosatjsoncard ; mv " + ENIGMA2_PATH_LISTS + "iptosatjsonall " + PLAYLIST_PATH + " ; mv " + OSCAM_SERVICES + " " + OSCAM_CARD + " ; mv " + OSCAM_NO_CARD + " " + OSCAM_SERVICES + f' && /etc/init.d/softcam.oscam restart && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={config.servicelist.startupservice.value}')
		eConsoleAppContainer().execute(f'sleep 8103 && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={currentservice}')
		eConsoleAppContainer().execute("sleep 8730 ; mv " + PLAYLIST_PATH + " " + ENIGMA2_PATH_LISTS + "iptosatjsonall ; mv " + ENIGMA2_PATH_LISTS + "iptosatjsoncard " + PLAYLIST_PATH + " ; mv " + OSCAM_SERVICES + " " + OSCAM_NO_CARD + " ; mv " + OSCAM_CARD + " " + OSCAM_SERVICES + f' && /etc/init.d/softcam.oscam restart && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={config.servicelist.startupservice.value}')
		eConsoleAppContainer().execute(f'sleep 8733 && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={currentservice}')
		eConsoleAppContainer().execute("sleep 9000 ; mv " + PLAYLIST_PATH + " " + ENIGMA2_PATH_LISTS + "iptosatjsoncard ; mv " + ENIGMA2_PATH_LISTS + "iptosatjsonall " + PLAYLIST_PATH + " ; mv " + OSCAM_SERVICES + " " + OSCAM_CARD + " ; mv " + OSCAM_NO_CARD + " " + OSCAM_SERVICES + f' && /etc/init.d/softcam.oscam restart && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={config.servicelist.startupservice.value}')
		eConsoleAppContainer().execute(f'sleep 9003 && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={currentservice}')
		eConsoleAppContainer().execute("sleep 9630 ; mv " + PLAYLIST_PATH + " " + ENIGMA2_PATH_LISTS + "iptosatjsonall ; mv " + ENIGMA2_PATH_LISTS + "iptosatjsoncard " + PLAYLIST_PATH + " ; mv " + OSCAM_SERVICES + " " + OSCAM_NO_CARD + " ; mv " + OSCAM_CARD + " " + OSCAM_SERVICES + f' && /etc/init.d/softcam.oscam restart && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={config.servicelist.startupservice.value}')
		eConsoleAppContainer().execute(f'sleep 9633 && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={currentservice}')
		eConsoleAppContainer().execute("sleep 9900 ; mv " + PLAYLIST_PATH + " " + ENIGMA2_PATH_LISTS + "iptosatjsoncard ; mv " + ENIGMA2_PATH_LISTS + "iptosatjsonall " + PLAYLIST_PATH + " ; mv " + OSCAM_SERVICES + " " + OSCAM_CARD + " ; mv " + OSCAM_NO_CARD + " " + OSCAM_SERVICES + f' && /etc/init.d/softcam.oscam restart && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={config.servicelist.startupservice.value}')
		eConsoleAppContainer().execute(f'sleep 9903 && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={currentservice}')
		config.plugins.IPToSAT.sequencetimers.value = False
		config.plugins.IPToSAT.sequencetimers.save()
		now = localtime(time())
		current_day = int(now.tm_wday)
		config.plugins.IPToSAT.timecardoff[current_day] = ConfigClock(default=((19 * 60 + 30) * 60))
		config.plugins.IPToSAT.timecardoff[current_day].value = config.plugins.IPToSAT.timecardoff[current_day].default
		config.plugins.IPToSAT.timecardoff[current_day].save()
		config.plugins.IPToSAT.timecardon[current_day] = ConfigClock(default=((23 * 60) * 60))
		config.plugins.IPToSAT.timecardon[current_day].value = config.plugins.IPToSAT.timecardon[current_day].default
		config.plugins.IPToSAT.timecardon[current_day].save()

	def iptosatCardOffTimer(self):
		import Screens.Standby  # noqa: E402
		self.cardofftimer.stop()
		now = int(time())
		cardoff = self.getTimeOffCard()
		if not Screens.Standby.inStandby:
			try:
				currentservice = NavigationInstance.instance.getCurrentlyPlayingServiceReference().toString()
			except Exception:
				return
		if cardoff - now < 60 and not NavigationInstance.instance.getRecordings() and config.plugins.IPToSAT.timerscard.value:
			if exists(str(PLAYLIST_PATH)) and exists(str(OSCAM_SERVICES)):
				if exists(str(ENIGMA2_PATH_LISTS + "iptosatjsonall")):
					if exists(str(OSCAM_NO_CARD)):
						move(PLAYLIST_PATH, ENIGMA2_PATH_LISTS + "iptosatjsoncard")
						move(ENIGMA2_PATH_LISTS + "iptosatjsonall", PLAYLIST_PATH)
						move(OSCAM_SERVICES, OSCAM_CARD)
						move(OSCAM_NO_CARD, OSCAM_SERVICES)
						if not Screens.Standby.inStandby:
							if currentservice:
								if "http" not in currentservice:
									NavigationInstance.instance.stopService()
									eConsoleAppContainer().execute('sleep 3 && ' + RESTART_OSCAM + f' && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={currentservice}')
								if BoxInfo.getItem("distro") == "norhap":
									if config.plugins.IPToSAT.sequencetimers.value and SystemInfo["FbcTunerPowerAlwaysOn"]:
										self.sequencetimers(currentservice)
						else:
							eConsoleAppContainer().execute(RESTART_OSCAM)
					elif exists(str(OSCAM_CARD)):
						move(OSCAM_SERVICES, OSCAM_NO_CARD)
						move(OSCAM_CARD, OSCAM_SERVICES)
						if exists(str(OSCAM_NO_CARD)):
							move(PLAYLIST_PATH, ENIGMA2_PATH_LISTS + "iptosatjsoncard")
							move(ENIGMA2_PATH_LISTS + "iptosatjsonall", PLAYLIST_PATH)
							move(OSCAM_SERVICES, OSCAM_CARD)
							move(OSCAM_NO_CARD, OSCAM_SERVICES)
							eConsoleAppContainer().execute("sleep 1 && " + RESTART_OSCAM)
				else:
					if exists(str(OSCAM_NO_CARD)):
						move(OSCAM_SERVICES, OSCAM_CARD)
						move(OSCAM_NO_CARD, OSCAM_SERVICES)
						eConsoleAppContainer().execute("sleep 3 && " + RESTART_OSCAM)

	def refreshTimerCard(self):
		current_day = int(localtime().tm_wday)
		now = int(time())
		if config.plugins.IPToSAT.timecardoff[current_day].value:
			if now > 1262304000:
				self.scheduledtime = self.prepareTimer()
			else:
				self.scheduledtime = 0
				self.cardpolltimer.start(36000)
		else:
			self.scheduledtime = 0
			self.cardpolltimer.stop()


class TimerOnCard:
	def __init__(self):
		self.cardontimer = eTimer()
		self.cardontimer.callback.append(self.iptosatCardOnTimer)
		self.cardpolltimer = eTimer()
		self.cardpolltimer.timeout.get().append(self.cardPollTimer)
		self.refreshTimerCard()

	def cardPollTimer(self):
		self.cardpolltimer.stop()
		self.scheduledtime = self.prepareTimer()

	def getTimeOnCard(self):
		now = localtime(time())
		current_day = int(now.tm_wday)
		return int(mktime((now.tm_year, now.tm_mon, now.tm_mday, config.plugins.IPToSAT.timecardon[current_day].value[0], config.plugins.IPToSAT.timecardon[current_day].value[1], 0, now.tm_wday, now.tm_yday, now.tm_isdst)))

	def prepareTimer(self):
		self.cardontimer.stop()
		cardontime = self.getTimeOnCard()
		now = int(time())
		if cardontime > 0:
			if cardontime < now:
				cardontime += 24 * 3600
				while (int(cardontime) - 30) < now:
					cardontime += 24 * 3600
			next = cardontime - now
			self.cardontimer.startLongTimer(next)
		else:
			cardontime = -1
		return cardontime

	def iptosatCardOnTimer(self):
		import Screens.Standby  # noqa: E402
		self.cardontimer.stop()
		now = int(time())
		cardon = self.getTimeOnCard()
		if cardon - now < 60 and not NavigationInstance.instance.getRecordings() and config.plugins.IPToSAT.timerscard.value:
			if exists(str(ENIGMA2_PATH_LISTS + "iptosatjsoncard")) and exists(str(OSCAM_CARD)):
				move(PLAYLIST_PATH, ENIGMA2_PATH_LISTS + "iptosatjsonall")
				move(ENIGMA2_PATH_LISTS + "iptosatjsoncard", PLAYLIST_PATH)
				move(OSCAM_SERVICES, OSCAM_NO_CARD)
				move(OSCAM_CARD, OSCAM_SERVICES)
				if not Screens.Standby.inStandby:
					try:
						currentservice = NavigationInstance.instance.getCurrentlyPlayingServiceReference().toString()
					except Exception:
						return
					if currentservice:
						if "http" not in currentservice:
							NavigationInstance.instance.stopService()
							eConsoleAppContainer().execute('sleep 1 && ' + RESTART_OSCAM + f' && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={currentservice}')
			elif not exists(str(ENIGMA2_PATH_LISTS + "iptosatjsoncard")) and exists(str(OSCAM_CARD)):
				move(OSCAM_SERVICES, OSCAM_NO_CARD)
				move(OSCAM_CARD, OSCAM_SERVICES)
				eConsoleAppContainer().execute("sleep 1 && " + RESTART_OSCAM)
			elif exists(str(ENIGMA2_PATH_LISTS + "iptosatjsoncard")) and exists(str(OSCAM_NO_CARD)):
				move(PLAYLIST_PATH, ENIGMA2_PATH_LISTS + "iptosatjsonall")
				move(ENIGMA2_PATH_LISTS + "iptosatjsoncard", PLAYLIST_PATH)
				eConsoleAppContainer().execute("sleep 1 && " + RESTART_OSCAM)

	def refreshTimerCard(self):
		current_day = int(localtime().tm_wday)
		now = int(time())
		if config.plugins.IPToSAT.timecardon[current_day].value:
			if now > 1262304000:
				self.scheduledtime = self.prepareTimer()
			else:
				self.scheduledtime = 0
				self.cardpolltimer.start(36000)
		else:
			self.scheduledtime = 0
			self.cardpolltimer.stop()


class IPToSAT(Screen):
	def __init__(self, session):
		global notresetchannels
		Screen.__init__(self, session)
		self.session = session
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
			iPlayableService.evStart: self.__evStart,
			iPlayableService.evTunedIn: self.__evStart,
			iPlayableService.evEnd: self.__evEnd,
			iPlayableService.evStopped: self.__evEnd,
		})
		self.Timer = eTimer()
		self.setFCCEnable = False
		if notresetchannels is False:
			getchannel = self.__isFallbackTunerEnabled if config.usage.remote_fallback_enabled.value and isPluginInstalled("FastChannelChange") else self.get_channel
			try:
				self.Timer.callback.append(getchannel)
			except:
				self.Timer_conn = self.Timer.timeout.connect(getchannel)
		else:
			notresetchannels = False
		if BoxInfo.getItem("distro") in ("norhap", "openspa"):
			if config.plugins.IPToSAT.cardday[day].value and config.plugins.IPToSAT.timerscard.value:
				self.timercardOff = TimerOffCard()  # card timer initializer off from reboot
				self.timercardOn = TimerOnCard()  # card timer initializer on from reboot
		if config.plugins.IPToSAT.autotimerbouquets.value:
			self.timercategories = TimerUpdateCategories(self.session)  # category update timer initializer
			self.timercategories.refreshScheduler()
		self.container = eConsoleAppContainer()
		self.ip_sat = False

	def current_channel(self, channel, lastservice):
		playlist = getPlaylist()
		player = config.plugins.IPToSAT.player.value
		if channel and playlist and not self.ip_sat:
			for ch in playlist['playlist']:
				if ch['sref'] == str(ServiceReference(lastservice)):
					self.session.nav.stopService()
					self.container.execute(f"{player} {ch['url']}")
					self.session.nav.playService(lastservice)
					self.ip_sat = True
					break
		if not self.session.nav.getRecordings():
			self.recording = False
			self.recordingASingleConnection = False
		else:
			if allowsMultipleRecordings() is False:
				self.recordingASingleConnection = True
		if isIPToSAT() and self.session.nav.getRecordings():
			if not self.recordingASingleConnection and isPluginInstalled("FastChannelChange") and config.plugins.IPToSAT.typecategories.value in ("all", "live"):
				self.__resetDataBase()
				self.__InfoallowsMultipleRecordingsFBC()

	def get_channel(self):
		try:
			if isPluginInstalled("FastChannelChange"):
				from enigma import eFCCServiceManager  # noqa: E402
				if config.plugins.fccsetup.activate.value and config.plugins.IPToSAT.enable.value:
					config.plugins.fccsetup.activate.value = False
					config.plugins.fccsetup.activate.save()
					self.deactivateFCC()
				if not config.plugins.fccsetup.activate.value and config.plugins.IPToSAT.enable.value and not self.setFCCEnable:
					eFCCServiceManager.getInstance().setFCCEnable(1)
					self.setFCCEnable = True
			if self.session.nav.getCurrentlyPlayingServiceReference():
				if "http" in self.session.nav.getCurrentlyPlayingServiceReference().toString() and self.session.nav.getRecordings():
					recording_same_subscription = config.plugins.IPToSAT.username.value in self.session.nav.getCurrentlyPlayingServiceReference().toString() or config.plugins.IPToSAT.domain.value.replace("http://", "").replace("https://", "") in self.session.nav.getCurrentlyPlayingServiceReference().toString()
					if self.recordingASingleConnection and allowsMultipleRecordings() is False:
						self.recording = True
					if allowsMultipleRecordings() is True and isPluginInstalled("FastChannelChange") and not self.recording:
						self.recording = True
						self.__InfoallowsMultipleRecordingsFBC()
					if self.ip_sat:
						self.container.write("q\n", 2)
						self.ip_sat = False
					if allowsMultipleRecordings() is False and not self.recordingASingleConnection:
						if recording_same_subscription and config.plugins.IPToSAT.typecategories.value in ("all", "live"):
							self.__recordingInfo()
							self.recordingASingleConnection = True
							self.__resetDataBase()
					else:
						if allowsMultipleRecordings() is False and config.plugins.IPToSAT.typecategories.value in ("all", "live"):
							self.__resetDataBase()
					if isPluginInstalled("FastChannelChange"):
						from enigma import eFCCServiceManager  # noqa: E402
						eFCCServiceManager.getInstance().setFCCEnable(0)
			service = self.session.nav.getCurrentService()
			if service:
				info = service and service.info()
				if info:
					FeInfo = service and service.frontendInfo()
					if FeInfo:
						SNR = FeInfo.getFrontendInfo(iFrontendInformation.signalQuality) / 655
						isCrypted = info and info.getInfo(iServiceInformation.sIsCrypted)
						if isCrypted or isIPToSAT():
							if SNR > 10 and self.session.nav.getCurrentlyPlayingServiceReference():
								lastservice = self.session.nav.getCurrentlyPlayingServiceReference()
								channel_name = ServiceReference(lastservice).getServiceName()
								self.current_channel(channel_name, lastservice)
						else:
							if self.ip_sat:
								self.container.write("q\n", 2)
								self.ip_sat = False
		except:
			pass

	def __evStart(self):
		self.Timer.start(1000)

	def __recordingInfo(self):
		self.container.write("q\n", 2)
		self.Timer.stop()
		if not isPluginInstalled("FastChannelChange"):
			AddPopup(language.get(lang, "214"), MessageBox.TYPE_INFO, timeout=0)
		else:
			AddPopup(language.get(lang, "218"), MessageBox.TYPE_INFO, timeout=0)

	def __InfoallowsMultipleRecordingsFBC(self):
		self.container.write("q\n", 2)
		self.Timer.stop()
		AddPopup(language.get(lang, "215"), MessageBox.TYPE_INFO, timeout=0)

	def __isFallbackTunerEnabled(self):
		self.container.write("q\n", 2)
		self.Timer.stop()
		if isIPToSAT():
			AddPopup(language.get(lang, "229"), MessageBox.TYPE_INFO, timeout=0)

	def __resetDataBase(self):
		if exists(resolveFilename(SCOPE_CONFIG, "lamedb")) and not exists(resolveFilename(SCOPE_PLUGINS, "Extensions/IPToSAT/lamedb")):
			copy(resolveFilename(SCOPE_CONFIG, "lamedb"), resolveFilename(SCOPE_PLUGINS, "Extensions/IPToSAT/lamedb"))
		if exists(resolveFilename(SCOPE_CONFIG, "lamedb5")) and not exists(resolveFilename(SCOPE_PLUGINS, "Extensions/IPToSAT/lamedb5")):
			copy(resolveFilename(SCOPE_CONFIG, "lamedb5"), resolveFilename(SCOPE_PLUGINS, "Extensions/IPToSAT/lamedb5"))

	def deactivateFCC(self):
		self.container.write("q\n", 2)
		self.Timer.stop()

		def restartDisableFCC(answer=False):
			if answer:
				self.session.open(TryQuitMainloop, 3)

		if not self.session.nav.getRecordings():
			if BoxInfo.getItem("distro") == "norhap":
				from Screens.Standby import checkTimeshiftRunning  # noqa: E402
				if not checkTimeshiftRunning():
					self.session.openWithCallback(restartDisableFCC, MessageBox, language.get(lang, "219"), type=MessageBox.TYPE_YESNO, simple=True)
			else:
				from Screens.InfoBar import InfoBar  # noqa: E402
				inTimeshift = InfoBar and InfoBar.instance and InfoBar.ptsGetTimeshiftStatus(InfoBar.instance)
				if not inTimeshift:
					self.session.openWithCallback(restartDisableFCC, MessageBox, language.get(lang, "219"), type=MessageBox.TYPE_YESNO, simple=True)
		else:
			AddPopup(language.get(lang, "120"), type=MessageBox.TYPE_INFO, timeout=0)

	def __evEnd(self):
		self.Timer.stop()
		if hasattr(self, "ip_sat"):
			self.container.write("q\n", 2)
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
			<widget source="global.CurrentTime" render="Label" position="1175,07" size="95,30" font="Regular;24" foregroundColor="#e5e619" backgroundColor="#0023262f" transparent="1" zPosition="10">
				<convert type="ClockToText">Default</convert>
			</widget>
			<widget name="list" position="23,42" size="613,310" backgroundColor="#0023262f" scrollbarMode="showOnDemand" scrollbarForegroundColor="#0044a2ff" scrollbarBorderColor="#0044a2ff" />
			<widget name="list2" position="658,42" size="612,304" backgroundColor="#0023262f" scrollbarMode="showOnDemand" scrollbarForegroundColor="#0044a2ff" scrollbarBorderColor="#0044a2ff" />
			<widget name="please" position="680,42" size="590,35" font="Regular;24" backgroundColor="#0023262f" zPosition="12" />
			<widget name="status" position="33,394" size="870,355" font="Regular;24" backgroundColor="#0023262f" zPosition="10" />
			<widget name="description" position="925,394" size="990,565" font="Regular;24" backgroundColor="#0023262f" zPosition="6" />
			<widget name="assign" position="33,394" size="870,140" font="Regular;24" backgroundColor="#0023262f" zPosition="6" />
			<widget name="codestatus" position="33,500" size="870,249" font="Regular;24" backgroundColor="#0023262f" zPosition="10" />
			<widget name="helpbouquetepg" position="33,355" size="870,550" font="Regular;24" backgroundColor="#0023262f" zPosition="6" />
			<widget name="managerlistchannels" position="33,735" size="870,182" font="Regular;24" backgroundColor="#0023262f" zPosition="10" />
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
			<widget source="global.CurrentTime" render="Label" position="1125,07" size="75,25" font="Regular;21" foregroundColor="#e5e619" backgroundColor="#0023262f" transparent="1" zPosition="10">
				<convert type="ClockToText">Default</convert>
			</widget>
			<widget name="list" position="33,42" size="550,198" scrollbarMode="showOnDemand" />
			<widget name="list2" position="600,42" size="550,200" scrollbarMode="showOnDemand" />
			<widget name="please" position="600,42" size="540,35" font="Regular;18" zPosition="12" />
			<widget name="status" position="33,245" size="540,225" font="Regular;18" zPosition="11" />
			<widget name="description" position="600,245" size="595,350" font="Regular;18" zPosition="6" />
			<widget name="assign" position="33,245" size="540,100" font="Regular;18" zPosition="6" />
			<widget name="codestatus" position="33,330" size="540,150" font="Regular;18" zPosition="10" />
			<widget name="helpbouquetepg" position="33,245" size="540,318" font="Regular;17" zPosition="6" />
			<widget name="managerlistchannels" position="33,425" size="540,125" font="Regular;18" zPosition="10" />
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
			<widget source="key_epg" render="Label" conditional="key_epg" position="472,598" zPosition="4" size="110,25" backgroundColor="key_back" font="Regular;18" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_help" render="Label" conditional="key_help" position="587,598" zPosition="4" size="110,25" backgroundColor="key_back" font="Regular;18" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_play" render="Label" conditional="key_play" position="702,598" zPosition="4" size="110,25" backgroundColor="key_back" font="Regular;18" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_volumeup" render="Label" conditional="key_volumeup" position="817,598" zPosition="4" size="110,25" backgroundColor="key_back" font="Regular;18" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_volumedown" render="Label" conditional="key_volumedown" position="932,598" zPosition="4" size="110,25" backgroundColor="key_back" font="Regular;18" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_stop" render="Label" conditional="key_stop" position="1047,598" zPosition="4" size="110,25" backgroundColor="key_back" font="Regular;18" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_1" render="Label" conditional="key_1" position="1162,598" zPosition="12" size="35,25" backgroundColor="key_back" font="Regular;18" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
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
		self["key_1"] = StaticText("")
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
			"1": self.searchBouquetIPTV,
			"0": self.getRefSat,
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
						backupfolder = ("BackupChannelsListNorhap" if BoxInfo.getItem("distro") == "norhap" else "BackupChannelsListSPA" if BoxInfo.getItem("distro") == "openspa" else "BackupChannelsList")
						self.backupdirectory = join(self.path, f"IPToSAT/{MODEL}/{backupfolder}")
						self.alternatefolder = join(self.path, f"IPToSAT/{MODEL}/AlternateList")
						self.changefolder = join(self.path, f"IPToSAT/{MODEL}/ChangeSuscriptionList")
						self.m3ufolder = join(self.path, f"IPToSAT/{MODEL}/M3U")
						self.m3ustoragefile = join(self.m3ufolder, "iptosat_norhap.m3u")
						self.iptosatconfalternate = join(self.alternatefolder, "iptosat.conf")
						self.iptosatconfchange = join(self.changefolder, "iptosat.conf")
						self.iptosatjsonalternate = join(self.alternatefolder, "iptosat.json")
						self.iptosatjsonchange = join(self.changefolder, "iptosat.json")
						self.fileconf = join(ENIGMA2_PATH, "iptosat.conf")
						self.filejson = join(ENIGMA2_PATH, "iptosat.json")
						self.iptosatlist1conf = join(self.alternatefolder, "iptosat_LIST1.conf")
						self.iptosatlist2conf = join(self.alternatefolder, "iptosat_LIST2.conf")
						self.iptosatlist1json = join(self.alternatefolder, "iptosat_LIST1.json")
						self.iptosatlist2json = join(self.alternatefolder, "iptosat_LIST2.json")
						self.categoriesall = join(self.alternatefolder, "iptosatcategories.json")
						self.categoriesallwildcard = join(self.alternatefolder, "categoriesalljson")
						self.categoriesallwildcardchanged = join(self.alternatefolder, "categoriesalljsonchanged")
						backupfiles = ""
						bouquetiptosatepg = ""
						if exists(str(BUILDBOUQUETS_SOURCE)):
							move(BUILDBOUQUETS_SOURCE, BUILDBOUQUETS_FILE)
						# ###################REMOVE IN A FEW MONTHS ###################
						if BoxInfo.getItem("distro") == "openspa" and not exists(str(self.backupdirectory)):
							if exists(str(self.backupdirectory).replace("SPA", "")):
								eConsoleAppContainer().execute('mv -f ' + str(self.backupdirectory).replace("SPA", "") + " " + str(self.backupdirectory))
						elif BoxInfo.getItem("distro") == "norhap" and not exists(str(self.backupdirectory)):
							if exists(str(self.backupdirectory).replace("Norhap", "")):
								eConsoleAppContainer().execute('mv -f ' + str(self.backupdirectory).replace("Norhap", "") + " " + str(self.backupdirectory))
						# ################### END ###################
						if exists(str(self.backupdirectory)):
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
		self["key_1"].setText("")
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
		#  self["key_1"].setText("0")
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
		self["key_1"].setText("")
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
			if (self.getCurrentSelection().flags & 7) == 7:
				text = ""
				self.assignWidgetScript("#e5e619", text)

	def moveUp(self):
		if self.selectedList.getCurrent():
			instance = self.selectedList.instance
			instance.moveSelection(instance.moveUp)
			if (self.getCurrentSelection().flags & 7) == 7:
				text = ""
				self.assignWidgetScript("#e5e619", text)

	def getUserData(self):
		listsuscription = join(str(self.alternatefolder), "iptosat_LIST1.conf")
		if exists(str(listsuscription)):
			self.secondSuscription = True
		self["titleSuscriptionList"].setText(language.get(lang, "12")) if not self.secondSuscription else self["titleSuscriptionList"].setText(language.get(lang, "44"))
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
				if config.plugins.IPToSAT.domain.value != config.plugins.IPToSAT.domain.default:
					with open(CONFIG_PATH, "r") as fr:
						xtream = fr.read()
						self.host = xtream.split()[1].split('Host=')[1]
						self.user = xtream.split()[2].split('User=')[1]
						self.password = xtream.split()[3].split('Pass=')[1]
						self.url = '{}/player_api.php?username={}&password={}'.format(self.host, self.user, self.password)
						self.getCategories(self.url)
						self.getUserSuscription(self.url)
				else:
					self.error(error=True)
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
		text = language.get(lang, "223")
		self.assignWidgetScript("#e5e619", text)
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
		if exists(ENIGMA2_PATH_LISTS + "iptosatjsonall"):
			self['managerlistchannels'].show()
			self.assignWidgetScript("#e5e619", language.get(lang, "196"))
		playlist = getPlaylist()
		if playlist:
			if sref.startswith('1') and 'http' not in sref:
				urldomain = config.plugins.IPToSAT.domain.value if "https" not in config.plugins.IPToSAT.domain.value else config.plugins.IPToSAT.domain.value + ":" + config.plugins.IPToSAT.serverport.value
				url = urldomain + '/' + config.plugins.IPToSAT.username.value + '/' + config.plugins.IPToSAT.password.value + '/' + stream_id
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
					eDVBDB.getInstance().reloadBouquets()
					eDVBDB.getInstance().reloadServicelist()
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
			cmdinstall = ""
			camfolder = ""
			foldercam = ""
			camdscriptspa = ""
			script = ""
			cams = False
			if answer:
				self.session.open(MessageBox, language.get(lang, "69"), MessageBox.TYPE_INFO, simple=True)
				for filesenigma2 in [x for x in listdir(self.backupdirectory) if "alternatives." in x or "whitelist" in x or "lamedb" in x or "iptosat.conf" in x or "iptosat.json" in x or "iptosatjsonall" in x or "iptosatjsoncard" in x or "iptosatcategories.json" in x or "iptosatreferences" in x or "iptosatyourcatall" in x or x.endswith(".radio") or x.endswith(".tv") or "blacklist" in x or x.startswith("wpa_supplicant")]:
					backupfilesenigma = join(self.backupdirectory, filesenigma2)
					if backupfilesenigma:
						for fileschannelslist in [x for x in listdir(ENIGMA2_PATH) if "alternatives." in x or "whitelist" in x or "lamedb" in x or x.startswith("iptosat.conf") or x.startswith("iptosat.json") or "iptosatjsonall" in x or "iptosatjsoncard" in x or x.startswith("iptosatcategories.json") or x.startswith("iptosatreferences") or "iptosatyourcatall" in x or ".radio" in x or ".tv" in x or "blacklist" in x or "automounts.xml" in x or "epgimport.conf" in x]:
							enigma2files = join(ENIGMA2_PATH, fileschannelslist)
							if enigma2files:
								remove(enigma2files)
				for cam in [x for x in listdir(self.backupdirectory) if "oscam" in x or "ncam" in x or "wicardd" in x or "CCcam" in x or "zerotier-one" in x]:
					camfolder = join(self.backupdirectory, cam)
					rmcamfolder = 'sleep 5 ; rm -rf ' + FILES_TUXBOX + '/config/*cam*'
					if "cam" in cam or "cardd" in cam:
						cams = True
						if not exists(str(self.backupdirectory) + '/zerotier-one'):
							cmdinstall = f'opkg update ; opkg install enigma2-plugin-softcams-{cam} ; ' + rmcamfolder if not exists("/usr/bin/oscam") and BoxInfo.getItem("distro") != "openspa" else 'sleep 5 ; opkg update ; opkg install enigma2-plugin-extensions-epgimport'
						else:
							cmdinstall = f'opkg update ; opkg install zerotier ; opkg install enigma2-plugin-softcams-{cam} ; ' + rmcamfolder if not exists("/usr/bin/oscam") and BoxInfo.getItem("distro") != "openspa" else 'sleep 5 ; opkg update ; opkg install enigma2-plugin-extensions-epgimport'
					if cam == "zerotier-one" and cams is False:
						cmdinstall = 'opkg update ; opkg install zerotier ; sleep 5' if exists(str(self.backupdirectory) + '/zerotier-one') and BoxInfo.getItem("distro") != "openspa" else 'sleep 5 ; opkg update'
				for filestuxbox in [x for x in listdir(self.backupdirectory) if ".xml" in x]:
					backupfilestuxbox = join(self.backupdirectory, filestuxbox)
					if backupfilestuxbox:
						for fileschannelslist in [x for x in listdir(FILES_TUXBOX) if ".xml" in x and "timezone.xml" not in x]:
							tuxboxfiles = join(FILES_TUXBOX, fileschannelslist)
							if tuxboxfiles:
								remove(tuxboxfiles)
				for foldercams in [x for x in listdir(self.backupdirectory) if "cam" in x]:
					foldercam = foldercams
				for camd in [x for x in listdir(self.backupdirectory) if "Camd" in x]:
					camdscriptspa = camd
				if exists(str(self.backupdirectory) + "/script"):
					for scriptsh in [x for x in listdir(self.backupdirectory + "/script") if "cam.sh" in x and foldercam[1:8] in x]:
						script = scriptsh
				initscriptsh = "sh " + USR_SCRIPT + '/' + script + ' start'
				createfoldercam = ' ; mkdir -p ' + FILES_TUXBOX + '/config/' + foldercam + ' ; ' if foldercam else ' ; '
				command = 'init 3 ; mount -a' if BoxInfo.getItem("socfamily") != "hisi3798mv200" and not exists(str(self.backupdirectory) + '/zerotier-one') and BoxInfo.getItem("distro") != "openspa" else initscriptsh + ' ; init 3'
				dumpcommand = f'{command}' if BoxInfo.getItem("distro") != "openspa" else 'cp -a ' + self.backupdirectory + '/' + camdscriptspa + ' /etc/ ; cp -f ' + self.backupdirectory + '/.ActiveCamd /etc/ ; ' + f'{command}'
				cambackupfolder = '*cam*'
				dumped = (' ; mv -f ' + ENIGMA2_PATH_LISTS + cambackupfolder + ' ' + FILES_TUXBOX + '/config/ ; mv -f ' + ENIGMA2_PATH_LISTS + 'binary-spa/*cam* /usr/bin/ ; rm -rf ' + ENIGMA2_PATH_LISTS + cambackupfolder + ' ' + ENIGMA2_PATH_LISTS + 'binary-spa ; chmod 755 /usr/bin/*cam* ; chmod -R 644 ' + FILES_TUXBOX + '/config/ ;' f'{dumpcommand}' if not exists(str(self.backupdirectory) + '/zerotier-one') else ' ; rm -rf ' + FOLDER_TOKEN_ZEROTIER + '/*.d ; cp -rf ' + ENIGMA2_PATH_LISTS + 'zerotier-one/* ' + FOLDER_TOKEN_ZEROTIER + '/ ; /etc/init.d/zerotier start ; rm -rf ' + ENIGMA2_PATH_LISTS + 'zerotier-one ; mv -f ' + ENIGMA2_PATH_LISTS + cambackupfolder + ' ' + FILES_TUXBOX + '/config/ ; mv -f ' + ENIGMA2_PATH_LISTS + 'binary-spa/*cam* /usr/bin/ ; rm -rf ' + ENIGMA2_PATH_LISTS + 'binary-spa ; chmod 755 /usr/bin/*cam* ; chmod -R 644 ' + FOLDER_TOKEN_ZEROTIER + ' ; chmod -R 644 ' + FILES_TUXBOX + '/config/ ;' f'{dumpcommand}')
				scriptfolder = ' ; rm -rf ' + USR_SCRIPT + ' ; mv -f ' + ENIGMA2_PATH_LISTS + 'script /usr/' if exists('/usr/script') else ' ; mv -f ' + ENIGMA2_PATH_LISTS + 'script ' + USR_SCRIPT
				eConsoleAppContainer().execute('init 4 ; sleep 2 ; ' + cmdinstall + createfoldercam + 'cp -a ' + self.backupdirectory + '/* ' + ENIGMA2_PATH_LISTS + '; rm -f ' + ENIGMA2_PATH_LISTS + '*Camd* ; chmod 644 ' + ENIGMA2_PATH_LISTS + '*' + scriptfolder + ' ; chmod -R 755 ' + USR_SCRIPT + ' ; mv -f ' + ENIGMA2_PATH_LISTS + 'interfaces /etc/network/ ; mv -f ' + ENIGMA2_PATH_LISTS + 'shadow /etc/ ; chmod 400 /etc/shadow ; mv -f ' + ENIGMA2_PATH_LISTS + 'inadyn.conf /etc/ ; chmod 644 /etc/inadyn.conf ; mv -f ' + ENIGMA2_PATH_LISTS + '*wpa_supplicant.wlan* /etc/ ; chmod 600 /etc/*wpa_supplicant* ; mv -f ' + ENIGMA2_PATH_LISTS + 'auto.network /etc/ ; chmod 644 /etc/auto.network ; mv -f ' + ENIGMA2_PATH_LISTS + 'fstab /etc/ ; chmod 644 /etc/fstab ; mv -f ' + ENIGMA2_PATH_LISTS + 'CCcam.cfg /etc/ ; chmod 644 /etc/CCcam.cfg ; mv ' + ENIGMA2_PATH_LISTS + 'cables.xml ' + FILES_TUXBOX + '/ ; mv ' + ENIGMA2_PATH_LISTS + 'atsc.xml ' + FILES_TUXBOX + '/ ; mv ' + ENIGMA2_PATH_LISTS + 'terrestrial.xml ' + FILES_TUXBOX + '/ ; mv ' + ENIGMA2_PATH_LISTS + 'satellites.xml ' + FILES_TUXBOX + '/' + f'{dumped}')
		except Exception as err:
			self.session.open(MessageBox, "ERROR: %s" % str(err), MessageBox.TYPE_ERROR, default=False, timeout=10)

	def installChannelsList(self):
		if self.storage:
			try:
				backupfiles = ""
				for files in [x for x in listdir(self.backupdirectory) if "alternatives." in x or "whitelist" in x or "lamedb" in x or "iptosat.conf" in x or "iptosat.json" in x or "iptosatjsonall" in x or "iptosatjsoncard" in x or "iptosatcategories.json" in x or "iptosatreferences" in x or "iptosatyourcatall" in x or x.endswith(".radio") or x.endswith(".tv") or "blacklist" in x or "settings" in x or ".xml" in x]:
					backupfiles = join(self.backupdirectory, files)
					if backupfiles and not self.session.nav.getRecordings():
						self.session.openWithCallback(self.doinstallChannelsList, MessageBox, language.get(lang, "71"), MessageBox.TYPE_YESNO)
						break
					elif self.session.nav.getRecordings():
						self.session.open(MessageBox, language.get(lang, "208"), MessageBox.TYPE_INFO, simple=True)
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
				for files in [x for x in listdir(self.backupdirectory) if "alternatives." in x or "whitelist" in x or "lamedb" in x or ".xml" in x or "iptosat.conf" in x or "iptosat.json" in x or "iptosatjsonall" in x or "iptosatjsoncard" in x or "iptosatcategories.json" in x or "iptosatreferences" in x or "iptosatyourcatall" in x or x.endswith(".radio") or x.endswith(".tv") or "blacklist" in x or "settings" in x or "fstab" in x or "auto.network" in x or "epgimport.conf" in x or "interfaces" in x or "CCcam.cfg" in x or x.startswith("wpa_supplicant.wlan") or "shadow" in x or "inadyn.conf" in x and "inadyn.conf-opkg" not in x or "Camd" in x]:
					backupfiles = join(self.backupdirectory, files)
					remove(backupfiles)
					eConsoleAppContainer().execute('rm -rf ' + self.backupdirectory + '/*oscam*' + " " + self.backupdirectory + '/*ncam*' + " " + self.backupdirectory + '/*wicardd*' + " " + self.backupdirectory + '/*script*' + " " + self.backupdirectory + '/*zerotier-one*' + " " + self.backupdirectory + '/*binary-spa*')
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
			camfolderspath = FILES_TUXBOX + '/config'
			if answer:
				self['managerlistchannels'].hide()
				if BoxInfo.getItem("distro") == "openspa":
					eConsoleAppContainer().execute('mkdir -p ' + self.backupdirectory + '/binary-spa ; cp -f /usr/bin/*oscam*' + ' ' + self.backupdirectory + '/binary-spa/')
				for files in [x for x in listdir(self.backupdirectory) if "alternatives." in x or "whitelist" in x or "lamedb" in x or "iptosat.conf" in x or "iptosat.json" in x or "iptosatjsonall" in x or "iptosatjsoncard" in x or "iptosatcategories.json" in x or "iptosatreferences" in x or "iptosatyourcatall" in x or x.endswith(".radio") or x.endswith(".tv") or "blacklist" in x or "settings" in x or ".xml" in x or "fstab" in x or "auto.network" in x or "epgimport.conf" in x or "CCcam.cfg" in x]:
					backupfiles = join(self.backupdirectory, files)
					remove(backupfiles)
					eConsoleAppContainer().execute('rm -rf ' + self.backupdirectory + '/*oscam*' + " " + self.backupdirectory + '/*ncam*' + " " + self.backupdirectory + '/*wicardd*')
				for fileschannelslist in [x for x in listdir(ENIGMA2_PATH) if "alternatives." in x or "whitelist" in x or "lamedb" in x or x.endswith("iptosat.conf") or x.endswith("iptosat.json") or "iptosatjsonall" in x or "iptosatjsoncard" in x or x.endswith("iptosatcategories.json") or x.endswith("iptosatreferences") or "iptosatyourcatall" in x or x.endswith(".radio") or x.endswith(".tv") or "blacklist" in x or "settings" in x or "automounts.xml" in x or "epgimport.conf" in x]:
					enigma2files = join(ENIGMA2_PATH, fileschannelslist)
					if enigma2files:
						copy(enigma2files, self.backupdirectory)
						self['managerlistchannels'].show()
						self.assignWidgetScript("#86dc3d", language.get(lang, "66"))
				for files in [x for x in listdir("/etc") if "fstab" in x or "auto.network" in x or x.startswith("wpa_supplicant.wlan") or "CCcam.cfg" in x or "shadow" in x or "inadyn.conf" in x and "inadyn.conf-opkg" not in x or "Camd" in x]:
					etc_files = join("/etc", files)
					if etc_files:
						copy(etc_files, self.backupdirectory)
				for camfolders in [x for x in listdir(camfolderspath) if "oscam" in x or "ncam" in x or "wicardd" in x]:
					camfolder = join(camfolderspath, camfolders)
					if camfolder:
						eConsoleAppContainer().execute('cp -rf ' + camfolderspath + "/" + camfolders + ' ' + self.backupdirectory + '/')
				for scripts in [x for x in listdir("/usr") if "script" in x]:
					scriptsfolder = join("/usr", scripts)
					eConsoleAppContainer().execute('cp -rf ' + scriptsfolder + ' ' + self.backupdirectory + '/')
				for files in [x for x in listdir("/etc/network") if "interfaces" in x]:
					interfaces = join("/etc/network", files)
					for file in [x for x in listdir("/sys/class/net") if x.startswith("wlan")]:
						wlan = join(file)
						if exists(f"/etc/wpa_supplicant.{wlan}.conf"):
							copy(interfaces, self.backupdirectory)
				for fileschannelslist in [x for x in listdir(FILES_TUXBOX) if ".xml" in x and "timezone.xml" not in x]:
					tuxboxfiles = join(FILES_TUXBOX, fileschannelslist)
					if tuxboxfiles:
						copy(tuxboxfiles, self.backupdirectory)
					if fileContains(CONFIG_PATH, "pass"):
						self["status"].show()
				for zerotierone in [x for x in listdir(FOLDER_TOKEN_ZEROTIER) if ".public" in x or ".secret" in x or ".prom" in x or "planet" in x or ".pid" in x or ".te" in x or ".port" in x or ".d" in x]:
					zerotierfiles = join(str(FOLDER_TOKEN_ZEROTIER), zerotierone)
					if zerotierfiles:
						eConsoleAppContainer().execute('cp -rf ' + zerotierfiles + ' ' + self.backupdirectory + '/zerotier-one/') if exists(str(self.backupdirectory) + '/zerotier-one') else eConsoleAppContainer().execute('mkdir -p ' + self.backupdirectory + '/zerotier-one ; cp -rf ' + zerotierfiles + ' ' + self.backupdirectory + '/zerotier-one/')
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
		self.Console = Console()
		if hasattr(self, "getSref"):
			sref = str(self.getSref())
			channel_name = str(ServiceReference(sref).getServiceName())
		if exists(str(BUILDBOUQUETS_FILE)):
			move(BUILDBOUQUETS_FILE, BUILDBOUQUETS_SOURCE)
		if exists(CONFIG_PATH) and not fileContains(CONFIG_PATH, "pass"):
			try:
				m3u = ""
				error = ""
				if not fileContains(CONFIG_PATH_CATEGORIES, "null") and fileContains(CONFIG_PATH_CATEGORIES, ":"):
					if exists(str(CATEGORIES_TIMER_ERROR)):
						remove(CATEGORIES_TIMER_ERROR)
					if exists(str(CATEGORIES_TIMER_OK)):
						remove(CATEGORIES_TIMER_OK)
					with open(REFERENCES_FILE, "a") as updatefile:
						if search(r'[áÁéÉíÍóÓúÚñÑM+m+.]', channel_name):
							channel_name = channel_name.replace(" ", "").replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U").replace("M+", "M").replace("MOVISTAR+", "M").replace("MOVISTAR", "M").replace("+", "").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("Ñ", "N").replace("movistar+", "m").replace("m+", "m").replace("movistar", "m").replace(".", "").encode('ascii', 'ignore').decode()
						if "iptosat" not in channel_name and not fileContains(REFERENCES_FILE, str(channel_name).lower()) and "ORDER BY bouquet" not in str(sref):
							if fileContains(REFERENCES_FILE, ":"):
								updatefile.write("\n" + str(channel_name).lower() + "-->" + str(sref) + "-->1")
							else:
								updatefile.write(str(channel_name).lower() + "-->" + str(sref) + "-->1")
					hostport = config.plugins.IPToSAT.domain.value + ":" + config.plugins.IPToSAT.serverport.value
					url = str(hostport) + '/get.php?username=' + str(config.plugins.IPToSAT.username.value) + '&password=' + str(config.plugins.IPToSAT.password.value) + '&type=m3u_plus&output=ts'
					user_agent = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'
					headers = {'User-Agent': user_agent}
					request = Request(url, None, headers)
					try:
						with urlopen(request) as response:
							m3u = response.read()
					except TimeoutError:
						self.session.open(MessageBox, language.get(lang, "221"), MessageBox.TYPE_ERROR, default=False)
						return
					except Exception as err:
						error = str(err)
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
						with open(str(self.m3ufile), "wb") as m3ufile:
							m3ufile.write(m3u)  # m3ufile.write(m3u.content) with get
						with open(str(self.m3ufile), "r") as m3uread:
							charactertoreplace = m3uread.readlines()
							with open(str(self.m3ufile), "w") as m3uw:
								for line in charactertoreplace:
									if '[' in line and ']' in line and '|' in line:
										line = line.replace('[', '').replace(']', '|')
									if '|  ' in line:
										line = line.replace('|  ', '| ')
									m3uw.write(line)
						if exists(str(BUILDBOUQUETS_FILE)):
							move(BUILDBOUQUETS_FILE, BUILDBOUQUETS_SOURCE)
						eConsoleAppContainer().execute('sleep 3 ; python' + str(version_info.major) + ' ' + str(BUILDBOUQUETS_SOURCE) + " ; mv " + str(BOUQUET_IPTV_NORHAP) + ".del" + " " + str(BOUQUET_IPTV_NORHAP) + " ; wget -qO - http://127.0.0.1/web/servicelistreload?mode=2 ; rm -f " + str(self.m3ufile) + " ; mv " + str(BUILDBOUQUETS_SOURCE) + " " + str(BUILDBOUQUETS_FILE) + " ; echo 1 > /proc/sys/vm/drop_caches ; echo 2 > /proc/sys/vm/drop_caches ; echo 3 > /proc/sys/vm/drop_caches")
						if self.storage:
							eConsoleAppContainer().execute('rm -f ' + str(self.m3ustoragefile) + " ; cp " + str(self.m3ufile) + " " + str(self.m3ustoragefile))
						self["helpbouquetepg"].hide()
						self['managerlistchannels'].show()
						self.assignWidgetScript("#e5e619", (language.get(lang, "5") if config.plugins.IPToSAT.typecategories.value in ("all", "live") else language.get(lang, "220")))
						with open(CATEGORIES_TIMER_OK, "w") as fw:
							now = datetime.now().strftime("%A %-d %B") + " " + language.get(lang, "170") + " " + datetime.now().strftime("%H:%M")
							fw.write(now)
						if isPluginInstalled("EPGImport") and exists(FOLDER_EPGIMPORT + "iptosat.channels.xml") and exists(EPG_CHANNELS_XML):
							self.Console.ePopen(['sleep 0'], self.runEPGIMPORT)
					else:
						self.assignWidgetScript("#00ff2525", f"ERROR: {error}\n" + language.get(lang, "6"))
				else:
					self.assignWidgetScript("#00ff2525", language.get(lang, "156"))
			except Exception as err:
				self.session.open(MessageBox, "ERROR: %s" % str(err), MessageBox.TYPE_ERROR, default=False)
		else:
			self.session.open(MessageBox, language.get(lang, "33"), MessageBox.TYPE_ERROR, default=False)

	def runEPGIMPORT(self, result=None, retVal=None, extra_args=None):
		global clearCacheEPG
		if config.plugins.epgimport.clear_oldepg.value:
			clearCacheEPG = True
			config.plugins.epgimport.clear_oldepg.value = False
			config.plugins.epgimport.clear_oldepg.save()
		if exists(EPG_IMPORT_CONFIG) and not exists(EPG_IMPORT_CONFIG_BACK):
			move(EPG_IMPORT_CONFIG, EPG_IMPORT_CONFIG_BACK)
		if not islink(EPG_IMPORT_CONFIG) and exists(EPG_CONFIG) and exists(EPG_IMPORT_CONFIG_BACK):
			symlink(EPG_CONFIG, EPG_IMPORT_CONFIG)
		if islink(EPG_IMPORT_CONFIG):
			from Plugins.Extensions.EPGImport.plugin import autoStartTimer  # noqa: E402
			autoStartTimer.runImport()
			self.Console = Console()
			self.Console.ePopen(['sleep 2'], self.finishedEPGIMPORT)

	def finishedEPGIMPORT(self, result=None, retVal=None, extra_args=None):
		global clearCacheEPG
		if clearCacheEPG is True:
			config.plugins.epgimport.clear_oldepg.value = True
			config.plugins.epgimport.clear_oldepg.save()
		if exists(EPG_IMPORT_CONFIG_BACK):
			unlink(EPG_IMPORT_CONFIG)
			move(EPG_IMPORT_CONFIG_BACK, EPG_IMPORT_CONFIG)

	def setEPGChannel(self):
		bouquetname = BOUQUET_IPTV_NORHAP
		if not exists(str(bouquetname)):
			self.createBouquetIPTV()
			return
		self['managerlistchannels'].show()
		sref = str(self.getSref())
		channel_name = str(ServiceReference(sref).getServiceName())
		iptvchannel = channel_name.replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U").replace("Ñ", "N").encode('ascii', 'ignore').decode()
		if sref.startswith("1:"):
			refiptv = sref.split("1:")[1]
		elif sref.startswith("4097:"):
			refiptv = sref.replace("4097:", "")
		if fileContains(IPToSAT_EPG_PATH, 'SERVICE 4097:' + refiptv) and fileContains(IPToSAT_EPG_PATH, '#DESCRIPTION ' + iptvchannel) and fileContains(IPToSAT_EPG_PATH, 'NAME IPToSAT_EPG'):
			return self.session.open(MessageBox, language.get(lang, "24") + channel_name + "\n\n" + language.get(lang, "75") + FILE_IPToSAT_EPG.replace("userbouquet.", "").replace(".tv", "").upper(), MessageBox.TYPE_INFO, simple=True)
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

	def getRefSat(self):
		global refSat
		refSat = self.getCurrentSelection().toString()
		text = language.get(lang, "224")
		self.assignWidgetScript("#86dc3d", text)

	def getRefSatCheck(self):
		refSat = self.getCurrentSelection().toString()
		if refSat and "4097" not in refSat and "FROM BOUQUET" not in refSat:
			return refSat
		return None

	def addEPGChannel(self, channel_name, sref, bouquetname):
		global refSat
		ref = self.getCurrentSelection()
		if (ref.flags & 7) == 7:  # this is bouquet selection no channel!!
			self.session.open(MessageBox, language.get(lang, "84"), MessageBox.TYPE_ERROR, simple=True, timeout=5)
		else:
			try:
				epg_channel_name = channel_name
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
					if exists(IPToSAT_EPG_PATH) and fileContains(IPToSAT_EPG_PATH, epg_channel_name) and not fileContains(IPToSAT_EPG_PATH, sref) or search(r'[ÁÉÍÓÚÑ]', character) and not fileContains(IPToSAT_EPG_PATH, sref):  # remove old channel with sref old
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
						if fileContains(IPToSAT_EPG_PATH, sref):
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
									if "#NAME" in line:
										bouquetnamemsgbox = line.replace("#NAME ", "")
										namebouquet = line
									if ":" + epg_channel_name in line and "http" in line:
										sat_reference_name = line.replace("::", ":").replace("0:" + epg_channel_name, "0").replace("C00000:0:0:0:00000:0:0:0", "C00000:0:0:0").replace("#DESCRIPT" + sref, "").replace("C00000:0:0:0:0000:0:0:0:0000:0:0:0:0000:0:0:0", "C00000:0:0:0").replace(":0000:0:0:0", "")
										if refSat is not None:
											reference = sat_reference_name.split("http")[0].split("SERVICE ")[1]
											satreferencename = sat_reference_name.replace(reference, refSat).replace("#SERVICE 1:", "#SERVICE 4097:")
											sref = satreferencename
										else:
											satreferencename = sat_reference_name
						if "http" in str(satreferencename):
							with open(ENIGMA2_PATH_LISTS + bouquetiptv, "w") as fw:
								with open(WILD_CARD_EPG_FILE, "r") as fr:
									lineNAME = fr.readlines()
									for line in lineNAME:
										fw.write(line)
							if not fileContains(IPToSAT_EPG_PATH, sref):
								with open(ENIGMA2_PATH_LISTS + bouquetiptv, "w") as fw:
									fw.write(namebouquet + "\n" + satreferencename + "\n" + "#DESCRIPTION " + epg_channel_name + "\n")
								with open(IPToSAT_EPG_PATH, "a") as fw:
									if not fileContains(IPToSAT_EPG_PATH, '#NAME IPToSAT_EPG'):
										if not fileContains(IPToSAT_EPG_PATH, satreferencename):
											fw.write('#NAME IPToSAT_EPG' + "\n" + satreferencename + "\n" + "#DESCRIPTION " + epg_channel_name + "\n")
									else:
										if not fileContains(IPToSAT_EPG_PATH, satreferencename):
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
							eDVBDB.getInstance().reloadBouquets()
							eDVBDB.getInstance().reloadServicelist()
						if fileContains(IPToSAT_EPG_PATH, epg_channel_name) and fileContains(ENIGMA2_PATH_LISTS + bouquetiptv, epg_channel_name) and not fileContains(ENIGMA2_PATH_LISTS + bouquetiptv, epg_channel_name + "#SERVICE") and fileContains(IPToSAT_EPG_PATH, sref):
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
				if stream_iptv and not fileContains(IPToSAT_EPG_PATH, epg_channel_name) and not fileContains(IPToSAT_EPG_PATH, sref):  # add stream IPTV with EPG to IPToSAT_EPG
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
					eDVBDB.getInstance().reloadBouquets()
					eDVBDB.getInstance().reloadServicelist()
			except Exception as err:
				print("ERROR: %s" % str(err))
			self.resultEditionBouquets(epg_channel_name, sref, bouquetname)

	def resultEditionBouquets(self, channel_name, sref, bouquetname):
		global refSat
		try:
			sref_update = sref.replace("#SERVICE 4097:", "4097:")
			characterascii = [channel_name]
			epg_channel_name = channel_name
			try:  # write file iptosatreferences updated.
				for character in characterascii:
					if search(r'[áÁéÉíÍóÓúÚñÑM+m+.]', channel_name):
						channel_name = character.replace(" ", "").replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U").replace("M+", "M").replace("MOVISTAR+", "M").replace("MOVISTAR", "M").replace("+", "").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("Ñ", "N").replace("movistar+", "m").replace("m+", "m").replace("movistar", "m").replace(".", "").encode('ascii', 'ignore').decode()
				if fileContains(REFERENCES_FILE, ":"):
					if refSat is None and "4097" not in str(sref_update):
						with open(REFERENCES_FILE, "r") as file:  # clear old services references from direct EPG key
							filereference = file.readlines()
							with open(REFERENCES_FILE, "w") as finalfile:
								for line in filereference:
									if str(channel_name).lower() in line and str(sref_update) not in line:
										olderef = line.split(str(channel_name).lower() + "-->")[1].split("-->1")[0]
										line = line.replace(olderef, str(sref_update))
									if str(channel_name).lower() not in line and str(sref_update) in line:
										oldchannel_name = line.split("-->1:")[0]
										line = line.replace(oldchannel_name, str(channel_name).lower())
									finalfile.write(line)
						if not fileContains(REFERENCES_FILE, str(channel_name).lower()) and not fileContains(REFERENCES_FILE, str(sref_update)):
							with open(REFERENCES_FILE, "a") as updatefile:
								if "http" not in str(sref_update):
									updatefile.write("\n" + str(channel_name).lower() + "-->" + str(sref_update) + "-->1")
								else:
									updatefile.write("\n" + str(channel_name).lower() + "-->" + str(sref_update).split("http")[0].replace("4097:", "1:") + "-->1")
				else:
					with open(REFERENCES_FILE, "w") as updatefile:
						updatefile.write(str(channel_name).lower() + "-->" + str(sref_update) + "-->1")
				if refSat and "4097" not in refSat:  # from Key "0".
					if fileContains(REFERENCES_FILE, ":"):
						reference_from_refSat = ""
						with open(REFERENCES_FILE, "r") as file:  # clear old services references
							filereference = file.readlines()
							with open(REFERENCES_FILE, "w") as finalfile:
								for line in filereference:
									if ":" in line and "FROM BOUQUET" not in line or "." in line and "FROM BOUQUET" not in line:
										if str(channel_name).lower() in line and str(sref_update) not in line:
											olderef = line.split(str(channel_name).lower() + "-->")[1].split("-->1")[0]
											line = line.replace(olderef, str(sref_update)).replace("\n", "")
										if str(channel_name).lower() not in line and str(sref_update) in line or str(channel_name).lower() not in line and refSat in line:
											oldchannel_name = line.split("-->1:")[0]
											line = line.replace(oldchannel_name, str(channel_name).lower()).replace(refSat, str(sref_update))
										if "#SERVICE" in line and "http" in line:
											refiptv = line.split("#SERVICE ")[1].split("http")[0] + "-->1"
											line = str(channel_name).lower() + "-->" + refiptv.replace("\n", "")
											reference_from_refSat = line
										if "http" in line:
											line = line.split("http")[0] + "-->1".replace("\n", "")
											reference_from_refSat = line
										if "4097" not in line:
											finalfile.write(line)
						with open(REFERENCES_FILE, "r") as file:  # Add IPTV reference.
							filereference = file.readlines()
							if reference_from_refSat and reference_from_refSat not in file.readlines():
								with open(REFERENCES_FILE, "a") as finalfile:
									finalfile.write("\n" + reference_from_refSat.replace("4097:", "1:"))
						if not fileContains(REFERENCES_FILE, str(channel_name).lower()) and not fileContains(REFERENCES_FILE, str(sref_update)):
							with open(REFERENCES_FILE, "a") as updatefile:
								if "http" not in str(sref_update):
									updatefile.write("\n" + str(channel_name).lower() + "-->" + str(sref_update) + "-->1")
								else:
									updatefile.write("\n" + str(channel_name).lower() + "-->" + str(sref_update).split("http")[0].replace("4097:", "1:") + "-->1")
					else:
						with open(REFERENCES_FILE, "w") as updatefile:
							updatefile.write(str(channel_name).lower() + "-->" + str(sref_update) + "-->1")
					# END write file iptosatreferences updated.
			except Exception:
				pass
			if not fileContains(IPToSAT_EPG_PATH, "#SERVICE") and not fileContains(IPToSAT_EPG_PATH, "#NAME IPToSAT_EPG"):
				if fileContains(bouquetname, ".ts") or fileContains(bouquetname, ".m3u"):
					self.addEPGChannel(channel_name, sref)
			if fileContains(IPToSAT_EPG_PATH, epg_channel_name) and fileContains(IPToSAT_EPG_PATH, sref) or fileContains(IPToSAT_EPG_PATH, sref):
				self.session.open(MessageBox, language.get(lang, "24") + epg_channel_name + "\n\n" + language.get(lang, "94") + "\n\n" + FILE_IPToSAT_EPG.replace("userbouquet.", "").replace(".tv", "").upper(), MessageBox.TYPE_INFO, simple=True)
			if exists(BOUQUET_IPTV_NORHAP) and not fileContains(CONFIG_PATH, "pass") and fileContains(IPToSAT_EPG_PATH, "#SERVICE"):
				if not fileContains(IPToSAT_EPG_PATH, epg_channel_name) and not fileContains(IPToSAT_EPG_PATH, sref) and bouquetname:
					self['managerlistchannels'].show()
					text = language.get(lang, "153" if "%3a//" in self.getCurrentSelection().toString() else "83")
					self.assignWidgetScript("#00ff2525", text)
				elif not fileContains(IPToSAT_EPG_PATH, epg_channel_name) and not fileContains(IPToSAT_EPG_PATH, sref):
					self['managerlistchannels'].show()
					text = language.get(lang, "153" if "%3a//" in self.getCurrentSelection().toString() else "83")
					self.assignWidgetScript("#00ff2525", text)
			else:
				if not fileContains(IPToSAT_EPG_PATH, ":" + epg_channel_name) and fileContains(IPToSAT_EPG_PATH, "#SERVICE"):
					if fileContains(bouquetname, ".ts") or fileContains(bouquetname, ".m3u"):
						self.session.open(MessageBox, language.get(lang, "85") + language.get(lang, "129") + "\n\n" + ":" + epg_channel_name, MessageBox.TYPE_ERROR)
				else:
					if not fileContains(bouquetname, ".ts") and not fileContains(bouquetname, ".m3u"):
						if not fileContains(IPToSAT_EPG_PATH, '#NAME IPToSAT_EPG'):
							with open(IPToSAT_EPG_PATH, "w") as fw:
								fw.write('#NAME IPToSAT_EPG' + "\n")
						self['managerlistchannels'].show()
						text = language.get(lang, "132")
						self.assignWidgetScript("#00ff2525", text)
					else:
						self.session.open(MessageBox, language.get(lang, "131"), MessageBox.TYPE_ERROR, simple=True)
			if epg_channel_name == ".":  # it is not a valid channel
				self.session.open(MessageBox, language.get(lang, "125"), MessageBox.TYPE_ERROR)
		except Exception as err:
			print("ERROR: %s" % str(err))
			refSat = None
		refSat = None

	def purge(self):
		if self.storage:
			if exists(str(self.iptosatconfalternate)) or exists(str(self.iptosatconfchange)) or exists(str(self.iptosatjsonalternate)) or exists(str(self.iptosatjsonchange)):
				self.session.openWithCallback(self.purgeDeviceFiles, MessageBox, language.get(lang, "57"), MessageBox.TYPE_YESNO, default=False)
			else:
				self.session.open(MessageBox, language.get(lang, "43"), MessageBox.TYPE_INFO)

	def purgeDeviceFiles(self, answer):
		if answer:
			try:
				if exists(str(self.iptosatconfalternate)):
					remove(self.iptosatconfalternate)
				if exists(str(self.iptosatconfchange)):
					remove(self.iptosatconfchange)
				if exists(str(self.iptosatjsonalternate)):
					remove(self.iptosatjsonalternate)
				if exists(str(self.iptosatjsonchange)):
					remove(self.iptosatjsonchange)
				if not exists(str(self.iptosatconfalternate)) or not exists(str(self.iptosatconfchange)) or not exists(str(self.iptosatjsonalternate)) or not exists(str(self.iptosatjsonchange)):
					self.session.open(MessageBox, language.get(lang, "52"), MessageBox.TYPE_INFO)
			except Exception as err:
				print("ERROR: %s" % str(err))

	def toggleSecondList(self):
		if self.storage:
			self["helpbouquetepg"].hide()
			try:
				currentservice = self.session.nav.getCurrentlyPlayingServiceReference().toString()
				if not exists(str(self.alternatefolder)):
					makedirs(self.alternatefolder)
				if BoxInfo.getItem("distro") in ("norhap", "openspa"):
					if not exists(str(ENIGMA2_PATH_LISTS + "iptosatjsoncard")) and exists(str(OSCAM_SERVER)) and exists(str(ENIGMA2_PATH_LISTS + "iptosatjsonall")):
						self.session.open(MessageBox, language.get(lang, "55"), MessageBox.TYPE_INFO, simple=True)
						return
					else:
						if not exists(str(self.iptosatconfalternate)) and not exists(str(self.iptosatlist1conf)) and not exists(str(self.iptosatlist2conf)):
							self.session.open(MessageBox, language.get(lang, "40") + "\n\n" + self.alternatefolder + "/" + "\n\n" + language.get(lang, "206"), MessageBox.TYPE_INFO)
							return
						elif self.session.nav.getRecordings():
							self.session.open(MessageBox, language.get(lang, "208"), MessageBox.TYPE_INFO, simple=True)
							return
						if "http" not in currentservice and config.servicelist.startupservice.value:
							self.session.nav.stopService()
				else:
					if not exists(str(self.iptosatconfalternate)) and not exists(str(self.iptosatlist1conf)) and not exists(str(self.iptosatlist2conf)):
						self.session.open(MessageBox, language.get(lang, "40") + "\n\n" + self.alternatefolder + "/" + "\n\n" + language.get(lang, "206"), MessageBox.TYPE_INFO)
						return
					elif self.session.nav.getRecordings():
						self.session.open(MessageBox, language.get(lang, "208"), MessageBox.TYPE_INFO, simple=True)
						return
					if "http" not in currentservice and config.servicelist.startupservice.value:
						self.session.nav.stopService()
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
					if exists(str(CONFIG_PATH_CATEGORIES)) and not exists(str(self.categoriesallwildcard)) and not exists(str(self.categoriesallwildcardchanged)):
						move(CONFIG_PATH_CATEGORIES, self.categoriesallwildcard)
						with open(CONFIG_PATH_CATEGORIES, 'w') as f:
							f.write("null")
					elif exists(str(CONFIG_PATH_CATEGORIES)) and not exists(str(self.categoriesallwildcardchanged)):
						move(CONFIG_PATH_CATEGORIES, self.categoriesall)
						move(self.categoriesallwildcard, CONFIG_PATH_CATEGORIES)
					if exists(str(CONFIG_PATH_CATEGORIES)) and exists(str(self.categoriesall)) and not exists(str(self.categoriesallwildcardchanged)):
						move(self.categoriesall, self.categoriesallwildcard)
					if exists(str(self.categoriesallwildcardchanged)):
						move(self.categoriesallwildcardchanged, CONFIG_PATH_CATEGORIES)
				if exists(str(self.iptosatconfalternate)):
					if exists(str(self.iptosatlist2conf)) or exists(str(self.iptosatlist1conf)):
						remove(self.iptosatconfalternate)
				if exists(str(self.iptosatjsonalternate)):
					if exists(str(self.iptosatlist2json)) or exists(str(self.iptosatlist1json)):
						remove(self.iptosatjsonalternate)
				if not exists(str(self.iptosatconfalternate)) and not exists(str(self.iptosatlist1conf)) and not exists(str(self.iptosatlist2conf)):
					self.session.open(MessageBox, language.get(lang, "40") + "\n\n" + self.alternatefolder + "/" + "\n\n" + language.get(lang, "206"), MessageBox.TYPE_INFO)
					return
				if not exists(str(self.iptosatjsonalternate)) and not exists(str(self.iptosatlist1conf)) and not exists(str(self.iptosatlist2conf)):
					with open(str(self.iptosatjsonalternate), 'w') as fw:
						fw.write("{" + "\n" + '	"playlist": []' + "\n" + "}")
				if exists(CONFIG_PATH) and exists(str(self.iptosatconfalternate)):
					move(CONFIG_PATH, self.iptosatlist1conf)
					move(self.iptosatconfalternate, self.fileconf)
					self.secondSuscription = True
				elif exists(CONFIG_PATH) and exists(str(self.iptosatlist2conf)):
					move(CONFIG_PATH, self.iptosatlist1conf)
					move(self.iptosatlist2conf, self.fileconf)
					self.secondSuscription = True
				elif exists(CONFIG_PATH) and exists(str(self.iptosatlist1conf)):
					move(CONFIG_PATH, self.iptosatlist2conf)
					move(self.iptosatlist1conf, self.fileconf)
					self.secondSuscription = False
				if exists(PLAYLIST_PATH) and exists(str(self.iptosatjsonalternate)):
					move(PLAYLIST_PATH, self.iptosatlist1json)
					move(self.iptosatjsonalternate, self.filejson)
					self.secondSuscription = True
				elif exists(PLAYLIST_PATH) and exists(str(self.iptosatlist2json)):
					move(PLAYLIST_PATH, self.iptosatlist1json)
					move(self.iptosatlist2json, self.filejson)
					self.secondSuscription = True
				elif exists(PLAYLIST_PATH) and exists(str(self.iptosatlist1json)):
					move(PLAYLIST_PATH, self.iptosatlist2json)
					move(self.iptosatlist1json, self.filejson)
					self.secondSuscription = False
				else:
					if exists(str(self.iptosatjsonalternate)):  # user enters the iptosat.json file
						if exists(str(self.iptosatlist1conf)):
							move(self.iptosatjsonalternate, self.iptosatlist1json)
						if exists(str(self.iptosatlist2conf)):
							move(self.iptosatjsonalternate, self.iptosatlist2json)
						self.secondSuscription = False
				self.getUserData()
				if BoxInfo.getItem("distro") in ("norhap", "openspa"):
					if "http" not in currentservice and not self.session.nav.getRecordings():
						if not exists(str(OSCAM_SERVER)) or exists(str(ENIGMA2_PATH_LISTS + "iptosatjsoncard")):
							eConsoleAppContainer().execute(f'sleep 6 && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={currentservice}')
				else:
					if "http" not in currentservice and not self.session.nav.getRecordings():
						eConsoleAppContainer().execute(f'sleep 6 && wget -O /dev/null -q http://127.0.0.1/web/zap?sRef={currentservice}')
				if fileExists(CONFIG_PATH):
					getUserDataSuscription()
				self["codestatus"].hide()
			except Exception as err:
				print("ERROR: %s" % str(err))

	def doChangeList(self, answer):
		try:
			if answer:
				if exists(str(self.iptosatconfchange)):
					move(self.iptosatconfchange, self.iptosatlist1conf)
				if exists(str(self.iptosatjsonchange)):
					move(self.iptosatjsonchange, self.iptosatlist1json)
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
			if answer:
				move(self.iptosatconfchange, self.iptosatlist2conf)
				move(self.iptosatjsonchange, self.iptosatlist2json)
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
				if not exists(str(self.changefolder)):
					makedirs(self.changefolder)
				if not exists(str(self.alternatefolder)):
					makedirs(self.alternatefolder)
				if not exists(str(self.iptosatjsonchange)) and not exists(str(self.iptosatlist1json)) and not exists(str(self.iptosatlist2json)):
					with open(str(self.iptosatjsonchange), 'w') as fw:
						fw.write("{" + "\n" + '	"playlist": []' + "\n" + "}")
				if exists(str(self.iptosatconfchange)) and exists(str(self.iptosatjsonchange)) and not exists(str(self.iptosatlist1conf)) and not exists(str(self.iptosatlist2conf)) and not exists(str(self.iptosatconfalternate)) and not exists(str(self.iptosatjsonalternate)):
					move(self.fileconf, self.iptosatlist1conf)
					move(self.iptosatconfchange, self.fileconf)
					move(self.filejson, self.iptosatlist1json)
					move(self.iptosatjsonchange, self.filejson)
					if config.plugins.IPToSAT.typecategories.value == "all":
						move(CONFIG_PATH_CATEGORIES, self.categoriesallwildcardchanged)
						if exists(str(ALL_CATEGORIES)):
							remove(ALL_CATEGORIES)
						if exists(str(WILD_CARD_ALL_CATEGORIES)):
							remove(WILD_CARD_ALL_CATEGORIES)
					else:
						if config.plugins.IPToSAT.usercategories.value:
							config.plugins.IPToSAT.usercategories.value = False
							config.plugins.IPToSAT.usercategories.save()
					self.getUserData()
					if fileExists(CONFIG_PATH):
						getUserDataSuscription()
					self.session.openWithCallback(self.doChangeList, MessageBox, language.get(lang, "73") + config.plugins.IPToSAT.domain.value + "\n\n" + language.get(lang, "59") + self.alternatefolder + "/", MessageBox.TYPE_INFO)
				if not exists(str(self.iptosatjsonchange)) and not exists(str(self.iptosatconfchange)) and not exists(str(self.iptosatlist1conf)) and not exists(str(self.iptosatlist2conf)) and not exists(str(self.iptosatconfalternate)):
					self.session.open(MessageBox, language.get(lang, "49") + self.changefolder + "/\n\n" + language.get(lang, "50"), MessageBox.TYPE_INFO)
				if exists(str(self.iptosatconfalternate)) and exists(str(self.iptosatconfchange)):
					if exists(str(self.iptosatlist1conf)):
						remove(self.iptosatconfalternate)
					if exists(str(self.iptosatlist2conf)):
						remove(self.iptosatconfalternate)
				if exists(str(self.iptosatjsonalternate)) and exists(str(self.iptosatjsonchange)):
					if exists(str(self.iptosatlist1json)):
						remove(self.iptosatjsonalternate)
					if exists(str(self.iptosatlist2json)):
						remove(self.iptosatjsonalternate)
					if exists(str(self.iptosatconfalternate)):
						self.session.open(MessageBox, language.get(lang, "53") + "\n\n" + self.iptosatconfalternate + "\n\n" + language.get(lang, "54") + "\n\n" + self.iptosatconfchange + "\n\n" + language.get(lang, "41"), MessageBox.TYPE_INFO)
				if exists(str(self.iptosatconfalternate)) and not exists(str(self.iptosatconfchange)):
					self.session.open(MessageBox, language.get(lang, "49") + self.changefolder + "/", MessageBox.TYPE_INFO)
				if exists(str(self.iptosatlist1conf)) and exists(str(self.iptosatconfchange)):
					self.session.openWithCallback(self.doChangeList, MessageBox, language.get(lang, "48") + config.plugins.IPToSAT.domain.value + "\n\n" + language.get(lang, "45"), MessageBox.TYPE_YESNO, default=False)
				if not exists(str(self.iptosatconfchange)):
					self.session.open(MessageBox, language.get(lang, "40") + "\n\n" + self.changefolder + "/\n\n" + language.get(lang, "56"), MessageBox.TYPE_INFO)
				if exists(str(self.iptosatlist2conf)) and exists(str(self.iptosatconfchange)):
					self.session.openWithCallback(self.doChangeList2, MessageBox, language.get(lang, "48") + config.plugins.IPToSAT.domain.value + "\n\n" + language.get(lang, "45"), MessageBox.TYPE_YESNO, default=False)
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
		parsed = urlparse(url)
		if self.storage:
			self["please"].setText(language.get(lang, "31"))
		if parsed.scheme == "https" and sslverify:
			sslfactory = SSLFactory(parsed.hostname)
			getPage(str.encode(url), sslfactory).addCallback(callback)
		else:
			getPage(str.encode(url)).addCallback(callback).addErrback(self.error)

	def suscription(self, url, callback):
		parsed = urlparse(url)
		if parsed.scheme == "https" and sslverify:
			sslfactory = SSLFactory(parsed.hostname)
			getPage(str.encode(url), sslfactory).addCallback(callback)
		else:
			getPage(str.encode(url)).addCallback(callback)

	def error(self, error=False):
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
					recording = language.get(lang, "119")
					if int(max_connections) == 1:
						self.assignWidgetScript("#86dc3d", language.get(lang, "105") + " " + expires + "\n" + language.get(lang, "106") + " " + status + "\n" + language.get(lang, "118") + " " + active_cons + "\n" + language.get(lang, "107") + " " + max_connections + "\n" + recording + " " + max_connections)
					else:
						if int(max_connections) == 2:
							self.assignWidgetScript("#86dc3d", language.get(lang, "105") + " " + expires + "\n" + language.get(lang, "106") + " " + status + "\n" + language.get(lang, "118") + " " + active_cons + "\n" + language.get(lang, "107") + " " + max_connections + "\n" + recording + " " + max_connections)
						else:
							self.assignWidgetScript("#86dc3d", language.get(lang, "105") + " " + expires + "\n" + language.get(lang, "106") + " " + status + "\n" + language.get(lang, "118") + " " + active_cons + "\n" + language.get(lang, "107") + " " + max_connections + "\n" + recording + " " + max_connections)
				elif int(time()) < int(exp_date):
					self.assignWidgetScript("#00ff2525", language.get(lang, "105") + " " + expires + "\n" + language.get(lang, "106") + " " + language.get(lang, "117") + "\n" + language.get(lang, "107") + " " + max_connections)
				else:
					self.assignWidgetScript("#00ff2525", language.get(lang, "108") + " " + expires + "\n" + language.get(lang, "106") + " " + status + "\n" + language.get(lang, "107") + " " + max_connections)
			else:
				if "Banned" not in status:
					if int(max_connections) == 1:
						self.assignWidgetScript("#86dc3d", language.get(lang, "109") + " " + expires + "\n" + language.get(lang, "106") + " " + status + "\n" + language.get(lang, "118") + " " + active_cons + "\n" + language.get(lang, "107") + " " + max_connections + "\n" + language.get(lang, "119") + " " + max_connections)
					else:
						if int(max_connections) == 2:
							self.assignWidgetScript("#86dc3d", language.get(lang, "109") + " " + expires + "\n" + language.get(lang, "106") + " " + status + "\n" + language.get(lang, "118") + " " + active_cons + "\n" + language.get(lang, "107") + " " + max_connections + "\n" + language.get(lang, "120") + " " + max_connections)
						else:
							self.assignWidgetScript("#86dc3d", language.get(lang, "109") + " " + expires + "\n" + language.get(lang, "106") + " " + status + "\n" + language.get(lang, "118") + " " + active_cons + "\n" + language.get(lang, "107") + " " + max_connections + "\n" + language.get(lang, "121") + " " + max_connections)
				else:
					self.assignWidgetScript("#00ff2525", language.get(lang, "105") + " " + expires + "\n" + language.get(lang, "106") + " " + language.get(lang, "117") + "\n" + language.get(lang, "107") + " " + max_connections)
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
				if str(channel_satellite[0:6]) in str(match['name'][0:12]):
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
				backupfolder = ("BackupChannelsListNorhap" if BoxInfo.getItem("distro") == "norhap" else "BackupChannelsListSPA" if BoxInfo.getItem("distro") == "openspa" else "BackupChannelsList")
				self.folderBackupCategories = join(self.path, f"IPToSAT/{MODEL}/{backupfolder}")
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
				if len(list) < 4:
					self["footnote"] = Label(language.get(lang, "185")) if config.plugins.IPToSAT.typecategories.value != "all" else Label(language.get(lang, "207"))
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
		if not fileContains(ALL_CATEGORIES, ":"):
			if fileContains(CONFIG_PATH_CATEGORIES, ":"):
				with open(CONFIG_PATH_CATEGORIES, "r") as fr:
					with open(ALL_CATEGORIES, "w") as fw:
						fw.write("{" + '\n')
					with open(ALL_CATEGORIES, "a") as fw:
						for lines in fr.readlines():
							lines = lines.replace("]", "],").replace("],,", "],")
							fw.write(lines)
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
									fw.write(lines + "\n" + "}" if not fileContains(WILD_CARD_CATYOURLIST, ",") else lines)
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
		<widget source="xmlfiles" render="Label" conditional="xmlfiles" position="7,555" zPosition="12" size="165,55" backgroundColor="key_back" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text"/>
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
		<widget name="status" position="712,545" size="684,170" font="Regular;20" horizontalAlignment="left" verticalAlignment="center" zPosition="3"/>
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
		self.backupdirectory = None
		self.backupChannelList = None
		self.tuxboxxml = 'https://github.com/OpenPLi/tuxbox-xml/archive/refs/heads/master.zip'  # TUXBOX FILES UPDATE REPOSITORY OPenPLi
		self.skinName = ["InstallChannelsListsIPToSAT"]
		self.setTitle(language.get(lang, "88"))
		self['list'] = MenuList([])
		self["key_red"] = StaticText("")
		self["key_green"] = StaticText("")
		self["key_yellow"] = StaticText("")
		self["xmlfiles"] = StaticText(language.get(lang, "216"))
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
			"menu": self.getinstallXMLUpdated,
			"left": self.goLeft,
			"right": self.goRight,
			"down": self.moveDown,
			"up": self.moveUp,
			"pageUp": self.pageUp,
			"pageDown": self.pageDown,
			"0": self.restoreBackupChannelsList,
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
				backupfolder = ("BackupChannelsListNorhap" if BoxInfo.getItem("distro") == "norhap" else "BackupChannelsListSPA" if BoxInfo.getItem("distro") == "openspa" else "BackupChannelsList")
				self.backupdirectory = join(self.path, f"IPToSAT/{MODEL}/{backupfolder}")
				if not exists(str(self.folderlistchannels)):
					makedirs(self.folderlistchannels)
				workdirectory = self.folderlistchannels + '/*'
				for dirfiles in glob(workdirectory, recursive=True):
					if exists(str(dirfiles)):
						eConsoleAppContainer().execute('rm -rf ' + dirfiles)
				if exists(str(self.backupdirectory)):
					for fileschannelslist in [x for x in listdir(self.backupdirectory) if "alternatives." in x or "whitelist" in x or "lamedb" in x or x.endswith(".radio") or x.endswith(".tv") or "blacklist" in x]:
						self.backupChannelList = join(self.backupdirectory, fileschannelslist)

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
				self["status"].setText(language.get(lang, "2" if not self.backupChannelList else "226"))
			else:
				self["key_red"].setText(language.get(lang, "89"))
				self["key_yellow"].setText(language.get(lang, "92"))
				self["status"].setText(language.get(lang, "184" if not self.backupChannelList else "226"))

	def keyGreen(self):
		channelslists = self["list"].getCurrent()
		if channelslists and self.storage:
			if self.session.nav.getRecordings():
				self.session.open(MessageBox, language.get(lang, "208"), MessageBox.TYPE_INFO, simple=True)
				return
			else:
				self.session.openWithCallback(self.doInstallChannelsList, MessageBox, language.get(lang, "91") + " " + channelslists, MessageBox.TYPE_YESNO)

	def keyRed(self):
		self.close(True)

	def exit(self, ret=None):
		self.close(True)

	def doindexListsRepositories(self, answer):
		self.satList = []
		self.satellites = {}
		self.transponders = {}
		from zipfile import ZipFile
		if answer:
			try:
				urljungle = 'https://github.com/jungla-team/Canales-enigma2/archive/refs/heads/main.zip'
				urlnorhap = 'https://github.com/norhap/channelslists/archive/refs/heads/main.zip'
				junglerepository = get(urljungle, timeout=10)
				norhaprepository = get(urlnorhap, timeout=10)
				with open(CHANNELS_LISTS_PATH, 'w') as fw:
					fw.write("{" + "\n" + '	"channelslists": []' + "\n" + "}")
				with open(str(self.zip_jungle), "wb") as jungle:
					jungle.write(junglerepository.content)
				with open(str(self.zip_sorys_vuplusmania), "wb") as norhap:
					norhap.write(norhaprepository.content)
				# JUNGLE TEAM
				if exists(str(self.zip_jungle)):
					with ZipFile(self.zip_jungle, 'r') as zipfile:
						zipfile.extractall(self.folderlistchannels)
				junglerepo = self.folderlistchannels + '/*/*Jungle-*'
				jungleupdatefile = self.folderlistchannels + '/**/*actualizacion*'
				junglelists = ""
				indexdate = ""
				indexlistssources = getChannelsLists()
				for file in glob(jungleupdatefile, recursive=True):
					with open(file, 'r') as fr:
						update = fr.readlines()
						for indexdate in update:
							indexdate = indexdate.replace("[", "")
				for folders in glob(junglerepo, recursive=True):
					junglelists = str([folders.split('main/')[1], indexdate])[1:-1].replace('\'', '').replace(',', '   ')
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
				indexdatecomunitarias = ""
				for file in glob(sorysupdatefile, recursive=True):
					if "comunitarias" not in file:
						with open(file, 'r') as fr:
							update = fr.readlines()
							for indexdate in update:
								indexdate = indexdate.replace("[", "")
					else:
						with open(file, 'r') as fr:
							update = fr.readlines()
							for indexdatecomunitarias in update:
								indexdatecomunitarias = indexdatecomunitarias.replace("[", "")
				for folders in glob(sorysrepository, recursive=True):
					if "Comunitarias" not in folders:
						soryslists = str([folders.split('main/')[1], indexdate])[1:-1].replace('\'', '').replace(',', '   ')
						indexlistssources['channelslists'].append({'listtype': soryslists})
					else:
						soryslists = str([folders.split('main/')[1], indexdatecomunitarias])[1:-1].replace('\'', '').replace(',', '   ')
						indexlistssources['channelslists'].append({'listtype': soryslists})
					with open(CHANNELS_LISTS_PATH, 'w') as f:
						dump(indexlistssources, f, indent=4)
				vuplusmaniarepository = self.folderlistchannels + '/*/*Vuplusmania-*'
				vuplusmaniaupdatefile = self.folderlistchannels + '/*/*Vuplusmania-*/*actualizacion*'
				vuplusmanialists = ""
				for file in glob(vuplusmaniaupdatefile, recursive=True):
					with open(file, 'r') as fr:
						update = fr.readlines()
						for indexdate in update:
							indexdate = indexdate.replace("[", "")
				for folders in glob(vuplusmaniarepository, recursive=True):
					vuplusmanialists = str([folders.split('main/')[1], indexdate])[1:-1].replace('\'', '').replace(',', '   ')
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

	def getinstallXMLUpdated(self):
		def restarGUI(answer):
			if answer:
				self.session.open(TryQuitMainloop, 3)

		def doinstallXMLRepositorie(answer):
			if answer:
				self.satList = []
				self.satellites = {}
				self.transponders = {}
				from zipfile import ZipFile
				try:
					tuxboxrepository = get(self.tuxboxxml, timeout=10)
					with open(str(self.zip_tuxbox_xml), "wb") as xml:
						xml.write(tuxboxrepository.content)
					if exists(str(self.zip_tuxbox_xml)):
						with ZipFile(self.zip_tuxbox_xml, 'r') as zipfile:
							zipfile.extractall(self.folderlistchannels)
					eConsoleAppContainer().execute('cp -a ' + self.folderlistchannels + '/tuxbox-xml-master/xml/*.xml ' + FILES_TUXBOX + '/')
					sleep(1)
					readsatellitesxml = eDVBDB.getInstance().readSatellites(self.satList, self.satellites, self.transponders)
					if readsatellitesxml:
						self.session.openWithCallback(restarGUI, MessageBox, language.get(lang, "222"), MessageBox.TYPE_YESNO)
				except Exception as err:
					print("ERROR: %s" % str(err))

		if self.storage:
			self.session.openWithCallback(doinstallXMLRepositorie, MessageBox, language.get(lang, "217"), MessageBox.TYPE_YESNO)

	def restoreBackupChannelsList(self):
		def dorestoreBackupChannelsList(answer):
			try:
				fileschannelslist = ""
				tuxboxfiles = ""
				backupfilestuxbox = ""
				if answer:
					self.session.open(MessageBox, language.get(lang, "227"), MessageBox.TYPE_INFO, simple=True)
					if self.backupChannelList:
						for enigma2files in [x for x in listdir(ENIGMA2_PATH) if "alternatives." in x or "whitelist" in x or "lamedb" in x or ".radio" in x or ".tv" in x or "blacklist" in x]:
							fileschannelslist = join(ENIGMA2_PATH, enigma2files)
							if fileschannelslist:
								remove(fileschannelslist)
					for filestuxbox in [x for x in listdir(self.backupdirectory) if ".xml" in x]:
						backupfilestuxbox = filestuxbox
						if backupfilestuxbox:
							for filestuxboxlist in [x for x in listdir(FILES_TUXBOX) if ".xml" in x and "timezone.xml" not in x]:
								tuxboxfiles = join(FILES_TUXBOX, filestuxboxlist)
								if tuxboxfiles:
									remove(tuxboxfiles)
					eConsoleAppContainer().execute('sleep 5 && init 4 && sleep 2 ; cp -a ' + str(self.backupdirectory) + '/*.xml ' + FILES_TUXBOX + '/ ; cp -a ' + str(self.backupdirectory) + '/*.tv ' + ENIGMA2_PATH_LISTS + ' ; cp -a ' + str(self.backupdirectory) + '/*.radio ' + ENIGMA2_PATH_LISTS + ' ; cp -a ' + str(self.backupdirectory) + '/whitelist ' + ENIGMA2_PATH_LISTS + ' ; cp -a ' + str(self.backupdirectory) + '/*alternatives. ' + ENIGMA2_PATH_LISTS + ' ; cp -a ' + str(self.backupdirectory) + '/blacklist ' + ENIGMA2_PATH_LISTS + ' ; cp -a ' + str(self.backupdirectory) + '/lamedb ' + ENIGMA2_PATH_LISTS + ' ; init 3')
			except Exception as err:
				self.session.open(MessageBox, "ERROR: %s" % str(err), MessageBox.TYPE_ERROR, default=False, timeout=10)
		if self.storage and self.backupChannelList:
			self.session.openWithCallback(dorestoreBackupChannelsList, MessageBox, language.get(lang, "225"), MessageBox.TYPE_YESNO)

	def getListsRepositories(self):
		if self.storage:
			self.session.openWithCallback(self.doindexListsRepositories, MessageBox, language.get(lang, "87"), MessageBox.TYPE_YESNO)

	def getSourceUpdated(self):
		if self.storage:
			if self.session.nav.getRecordings():
				self.session.open(MessageBox, language.get(lang, "208"), MessageBox.TYPE_INFO, simple=True)
				return
			else:
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
				checkfilesinstall = ' && cp -f ' + self.folderlistchannels + '/IPtoSAT-main/src/etc/enigma2/iptosatreferences ' + ENIGMA2_PATH + '/ && cp -f ' + self.folderlistchannels + '/IPtoSAT-main/src/IPtoSAT/* ' + SOURCE_PATH if not exists(FOLDER_EPGIMPORT + "iptosat.channels.xml") else ' && cp -f ' + self.folderlistchannels + '/IPtoSAT-main/src/etc/enigma2/iptosatreferences ' + ENIGMA2_PATH + '/ && cp -f ' + self.folderlistchannels + '/IPtoSAT-main/src/IPtoSAT/* ' + SOURCE_PATH + ' && cp -f ' + self.folderlistchannels + '/IPtoSAT-main/src/IPtoSAT/iptosat.channels.xml ' + FOLDER_EPGIMPORT + 'iptosat.channels.xml && cp -f ' + self.folderlistchannels + '/IPtoSAT-main/src/IPtoSAT/iptosat.sources.xml ' + FOLDER_EPGIMPORT + 'iptosat.sources.xml'
				eConsoleAppContainer().execute('cd ' + self.folderlistchannels + ' && unzip IPtoSAT-main.zip && rm -f ' + EPG_CONFIG + " " + EPG_SOURCES_XML + " " + EPG_CHANNELS_XML + " " + SOURCE_PATH + "keymap.xml" + " " + SOURCE_PATH + "icon.png" + " " + SOURCE_PATH + "buildbouquets" + " " + LANGUAGE_PATH + " " + VERSION_PATH + f'{checkfilesinstall}' + ' && /sbin/init 4 && sleep 5 && /sbin/init 3 && sleep 35 && rm -rf ' + self.folderlistchannels + "/* " + SOURCE_PATH + '*.py')
		except Exception as err:
			self.session.open(MessageBox, "ERROR: %s" % str(err), MessageBox.TYPE_ERROR, default=False, timeout=10)

	def doInstallChannelsList(self, answer):
		from zipfile import ZipFile
		channelslists = self["list"].getCurrent()
		if answer:
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
					for files in [x for x in listdir(dirnewlist) if x.endswith(".tv")]:
						newfiles = join(dirnewlist, files)
						if exists(str(newfiles)):
							self.session.open(MessageBox, language.get(lang, "77") + "   " + str(channelslists), MessageBox.TYPE_INFO, simple=True)
							for installedlist in [x for x in listdir(ENIGMA2_PATH) if "alternatives." in x or "whitelist" in x or "lamedb" in x or "satellites.xml" in x or "atsc.xml" in x or "terrestrial.xml" in x or ".radio" in x or ".tv" in x or "blacklist" in x]:
								installedfiles = join(ENIGMA2_PATH, installedlist)
								if installedfiles:
									remove(installedfiles)
							if exists(self.folderlistchannels + '/tuxbox-xml-master'):
								eConsoleAppContainer().execute('sleep 2 ; init 4 ; sleep 2 ; mv -f ' + dirnewlist + '/*.xml' + " " + FILES_TUXBOX + '/ ; cp -f ' + dirnewlist + '/*' + " " + ENIGMA2_PATH_LISTS + ' ; cp -f ' + self.folderlistchannels + '/tuxbox-xml-master/xml/*.xml ' + FILES_TUXBOX + '/ ; rm -f ' + ENIGMA2_PATH_LISTS + 'actualizacion ; init 3')
							else:
								eConsoleAppContainer().execute('sleep 2 ; init 4 ; sleep 2 ; mv -f ' + dirnewlist + '/*.xml' + " " + FILES_TUXBOX + '/ ; cp -f ' + dirnewlist + '/*' + " " + ENIGMA2_PATH_LISTS + ' ; rm -f ' + ENIGMA2_PATH_LISTS + 'actualizacion ; init 3')
						else:
							return self.session.open(MessageBox, language.get(lang, "228") + "   " + str(channelslists) + "\n" + language.get(lang, "221"), MessageBox.TYPE_ERROR, simple=True)
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
			killActivePlayer()
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
