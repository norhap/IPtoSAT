from enigma import iPlayableService, iServiceInformation, iFrontendInformation, eTimer, gRGB, eConsoleAppContainer, getDesktop
from Screens.ChannelSelection import ChannelSelectionBase
from Components.ServiceList import ServiceList  # noqa: F401
from Screens.Screen import Screen
from Components.config import config, getConfigListEntry, ConfigSelection, ConfigYesNo, ConfigText, ConfigSubsection
from Plugins.Plugin import PluginDescriptor
from Components.ActionMap import ActionMap
from Components.ServiceEventTracker import ServiceEventTracker
from Components.ConfigList import ConfigList, ConfigListScreen  # noqa: F401
from Components.MenuList import MenuList
from Components.Label import Label
from Components.SystemInfo import BoxInfo  # ,MODEL import from getBoxType for all images OE
from boxbranding import getBoxType
from ServiceReference import ServiceReference
from Screens.MessageBox import MessageBox
from Screens.Standby import TryQuitMainloop
from Components.Sources.StaticText import StaticText
from Components.Console import Console
from Tools.Directories import SCOPE_PLUGINS, fileContains, fileExists, isPluginInstalled, resolveFilename
from twisted.web.client import getPage
from datetime import datetime
from json import dump, loads
from glob import glob
from os import listdir, makedirs, remove
from os.path import join, exists, normpath
from configparser import ConfigParser
from time import sleep, time
from Components.Harddisk import harddiskmanager
from shutil import move, copy
from re import search
from sys import stdout

MODEL = getBoxType()
PLAYLIST_PATH = "/etc/enigma2/iptosat.json"
CHANNELS_LISTS_PATH = "/etc/enigma2/iptosatchlist.json"
SUSCRIPTION_USER_DATA = "/etc/enigma2/suscriptiondata"
BUILDBOUQUETS_FILE = resolveFilename(SCOPE_PLUGINS, "Extensions/IPToSAT/buildbouquets")
BUILDBOUQUETS_SOURCE = resolveFilename(SCOPE_PLUGINS, "Extensions/IPToSAT/buildbouquets.py")
REFERENCES_FILE = "/etc/enigma2/iptosatreferences"
CONFIG_PATH_CATEGORIES = "/etc/enigma2/iptosatcategories.json"
CONFIG_PATH = "/etc/enigma2/iptosat.conf"
SOURCE_PATH = resolveFilename(SCOPE_PLUGINS, "Extensions/IPToSAT")
LANGUAGE_PATH = resolveFilename(SCOPE_PLUGINS, "Extensions/IPToSAT/languages")
VERSION_PATH = resolveFilename(SCOPE_PLUGINS, "Extensions/IPToSAT/version")
IPToSAT_EPG_PATH = "/etc/enigma2/userbouquet.iptosat_epg.tv"
FILE_IPToSAT_EPG = "userbouquet.iptosat_epg.tv"
BOUQUETS_TV = "/etc/enigma2/bouquets.tv"
SOURCE_BOUQUET_IPTV = "/etc/enigma2/iptv.sh"
WILD_CARD_EPG_FILE = "/etc/enigma2/wildcardepg"
WILD_CARD_BOUQUETSTV = "/etc/enigma2/wildcardbouquetstv"
ENIGMA2_PATH = "/etc/enigma2"
ENIGMA2_PATH_LISTS = "/etc/enigma2/"

try:
	if not fileContains(LANGUAGE_PATH, "[" + config.osd.language.value[:-3] + "]"):
		lang = "en"
	else:
		from Components.Language import language
		lang = language.getLanguage()
		lang = lang[:2]
except:
	try:
		lang = config.osd.language.value[:-3]
	except:
		lang = "en"

try:
	language = ConfigParser()
	language.read(LANGUAGE_PATH, encoding="utf8")
except:
	try:
		lang = "en"
		language = ConfigParser()
		language.read(LANGUAGE_PATH, encoding="utf8")
	except:
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
config.plugins.IPToSAT.deletecategories = ConfigYesNo(default=False)
config.plugins.IPToSAT.downloadcategories = ConfigYesNo(default=True)
config.plugins.IPToSAT.player = ConfigSelection(default=default_player, choices=choices_list())
config.plugins.IPToSAT.assign = ConfigSelection(choices=[("1", language.get(lang, "34"))], default="1")
config.plugins.IPToSAT.playlist = ConfigSelection(choices=[("1", language.get(lang, "34"))], default="1")
config.plugins.IPToSAT.installchannelslist = ConfigSelection(choices=[("1", language.get(lang, "34"))], default="1")
config.plugins.IPToSAT.domain = ConfigText(default="http://hostname", fixed_size=False)
config.plugins.IPToSAT.serverport = ConfigText(default="80", fixed_size=False)
config.plugins.IPToSAT.username = ConfigText(default=language.get(lang, "113"), fixed_size=False)
config.plugins.IPToSAT.password = ConfigText(default=language.get(lang, "114"), fixed_size=False)


def trace_error():
	import traceback
	try:
		traceback.print_exc(file=stdout)
		traceback.print_exc(file=open('/tmp/IPToSAT.log', 'a'))
	except:
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
		except:
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
	<screen name="IPToSATSetup" position="center,center" size="1150,700" title="IPToSATSetup settings">
		<widget name="config" itemHeight="50" position="15,10" size="1120,550" scrollbarMode="showOnDemand" />
		<widget name="footnote" position="35,575" size="1110,80" font="Regular;24" zPosition="3" />
		<widget name="key_red" position="25,660" size="150,30" zPosition="2" backgroundColor="key_red" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text" />
		<widget name="key_green" position="210,660" size="150,30" zPosition="2" backgroundColor="key_green" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text" />
		<widget source="VKeyIcon" text="TEXT" render="Label" position="e-200,e-50" size="90,40" backgroundColor="key_back" conditional="VKeyIcon" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget name="HelpWindow" position="0,0" size="0,0" alphaTest="blend" conditional="HelpWindow" transparent="1" zPosition="+1" />
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = ["Setup"]
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
			"ok": self.ok,
		}, -2)
		for partition in harddiskmanager.getMountedPartitions():
			self.path = normpath(partition.mountpoint)
			if self.path != "/" and "net" not in self.path and "autofs" not in self.path:
				if exists(str(self.path)) and listdir(self.path):
					self.storage = True
		self["key_red"] = Label(_("Cancel"))  # noqa: F821
		self["key_green"] = Label(_("Save"))  # noqa: F821
		self["footnote"] = Label(language.get(lang, "99"))
		self.createSetup()
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(language.get(lang, "13"))

	def createSetup(self):
		self.list = [getConfigListEntry(language.get(lang, "14"), config.plugins.IPToSAT.enable)]
		self.list.append(getConfigListEntry(language.get(lang, "15"), config.plugins.IPToSAT.assign))
		self.list.append(getConfigListEntry(language.get(lang, "16"), config.plugins.IPToSAT.playlist))
		if config.plugins.IPToSAT.showuserdata.value:
			self.list.append(getConfigListEntry(language.get(lang, "111"), config.plugins.IPToSAT.domain))
			self.list.append(getConfigListEntry(language.get(lang, "112"), config.plugins.IPToSAT.serverport))
			self.list.append(getConfigListEntry(language.get(lang, "113"), config.plugins.IPToSAT.username))
			self.list.append(getConfigListEntry(language.get(lang, "114"), config.plugins.IPToSAT.password))
		if self.storage:
			self.list.append(getConfigListEntry(language.get(lang, "88"), config.plugins.IPToSAT.installchannelslist))
			if not fileContains(CONFIG_PATH, "pass"):
				self.list.append(getConfigListEntry(language.get(lang, "126"), config.plugins.IPToSAT.downloadcategories))
		if fileContains(BOUQUETS_TV, "norhap"):
			self.list.append(getConfigListEntry(language.get(lang, "127"), config.plugins.IPToSAT.deletecategories))
		self.list.append(getConfigListEntry(language.get(lang, "17"), config.plugins.IPToSAT.player))
		self.list.append(getConfigListEntry(language.get(lang, "98"), config.plugins.IPToSAT.mainmenu))
		self.list.append(getConfigListEntry(language.get(lang, "116"), config.plugins.IPToSAT.showuserdata))
		self["config"].list = self.list
		self["config"].setList(self.list)
		self.saveConfig()
		if isPluginInstalled("FastChannelChange") and fileContains(PLAYLIST_PATH, '"sref": "') and BoxInfo.getItem("distro") == "norhap" and config.plugins.IPToSAT.enable.value:
			try:
				if config.usage.remote_fallback_enabled.value or not config.plugins.fccsetup.activate.value or config.plugins.fccsetup.activate.value and not config.plugins.fccsetup.zapupdown.value or config.plugins.fccsetup.activate.value and not config.plugins.fccsetup.history.value:
					config.plugins.fccsetup.activate.value = True
					config.plugins.fccsetup.activate.save()
					config.plugins.fccsetup.zapupdown.value = True
					config.plugins.fccsetup.zapupdown.save()
					config.plugins.fccsetup.history.value = True
					config.plugins.fccsetup.history.save()
					config.plugins.fccsetup.maxfcc.value = 2
					config.plugins.fccsetup.maxfcc.save()
					config.plugins.fccsetup.priority.value = "zapupdown"
					config.plugins.fccsetup.priority.save()
					config.usage.remote_fallback_enabled.value = False
					config.usage.remote_fallback_enabled.save()
					self.session.open(TryQuitMainloop, 3)
			except:
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
		elif current[1] == config.plugins.IPToSAT.installchannelslist:
			self.session.open(InstallChannelsLists)

	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def keySave(self):
		self.saveiptosatconf()
		ConfigListScreen.keySave(self)

	def moveUp(self):
		self["config"].moveUp()

	def moveDown(self):
		self["config"].moveDown()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)

	def keyRight(self):
		ConfigListScreen.keyRight(self)

	def saveiptosatconf(self):
		if exists(CONFIG_PATH):
			with open(CONFIG_PATH, 'w') as iptosatconf:
				iptosatconf.write("[IPToSat]" + "\n" + 'Host=' + config.plugins.IPToSAT.domain.value + ":" + config.plugins.IPToSAT.serverport.value + "\n" + "User=" + config.plugins.IPToSAT.username.value + "\n" + "Pass=" + config.plugins.IPToSAT.password.value)
		else:
			with open(CONFIG_PATH, 'w') as iptosatconf:
				iptosatconf.write("[IPToSat]" + "\n" + 'Host=http://domain:port' + "\n" + "User=user" + "\n" + "Pass=pass")
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
		except:
			self.Timer_conn = self.Timer.timeout.connect(self.get_channel)
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
	screenWidth = getDesktop(0).size().width()
	if screenWidth == 1920:
		skin = """
		<screen name="IPToSAT Service Assign" position="0,60" size="1920,1020" backgroundColor="#0023262f" title="IPToSAT Service Assign">
			<eLabel backgroundColor="#0044a2ff" position="0,0" size="1917,3"/>
			<eLabel backgroundColor="#0044a2ff" position="0,3" size="3,1020"/>
			<eLabel backgroundColor="#0044a2ff" position="0,1017" size="1917,3"/>
			<eLabel backgroundColor="#0044a2ff" position="1917,0" size="3,1020"/>
			<widget name="titleChannelsList" position="100,05" size="705,35" horizontalAlignment="center" verticalAlignment="center" foregroundColor="yellow" backgroundColor="#0023262f" zPosition="2" font="Regular;25" />
			<widget name="titleSuscriptionList" position="1000,05" size="705,35" horizontalAlignment="center" verticalAlignment="center" foregroundColor="yellow" backgroundColor="#0023262f" zPosition="2" font="Regular;25" />
			<widget name="list" position="33,42" size="875,310" backgroundColor="#0023262f" scrollbarMode="showOnDemand" scrollbarForegroundColor="#0044a2ff" scrollbarBorderColor="#0044a2ff" />
			<widget name="list2" position="925,42" size="962,305" backgroundColor="#0023262f" scrollbarMode="showOnDemand" scrollbarForegroundColor="#0044a2ff" scrollbarBorderColor="#0044a2ff" />
			<widget name="please" position="925,42" size="870,35" font="Regular;24" backgroundColor="#0023262f" zPosition="12" />
			<widget name="status" position="33,357" size="870,400" font="Regular;24" backgroundColor="#0023262f" zPosition="10" />
			<widget name="description" position="925,355" size="962,605" font="Regular;24" backgroundColor="#0023262f" zPosition="6" />
			<widget name="assign" position="33,357" size="870,140" font="Regular;24" backgroundColor="#0023262f" zPosition="6" />
			<widget name="codestatus" position="33,500" size="870,300" font="Regular;24" backgroundColor="#0023262f" zPosition="10" />
			<widget name="helpbouquetepg" position="33,355" size="870,550" font="Regular;24" backgroundColor="#0023262f" zPosition="6" />
			<widget name="managerlistchannels" position="33,750" size="870,165" font="Regular;24" backgroundColor="#0023262f" zPosition="10" />
			<widget name="help" position="925,355" size="962,605" font="Regular;24" backgroundColor="#0023262f" zPosition="3" />
			<widget name="play" position="925,355" size="962,530" font="Regular;24" backgroundColor="#0023262f" zPosition="3" />
			<widget source="key_green" render="Label" objectTypes="key_green,StaticText" position="12,965" zPosition="2" size="165,52" backgroundColor="key_green" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text" />
			<widget source="key_blue" render="Label" objectTypes="key_blue,StaticText" position="189,965" zPosition="2" size="165,52" backgroundColor="key_blue" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text" />
			<widget source="key_red" conditional="key_red" render="Label" objectTypes="key_red,StaticText" position="365,965" zPosition="2" size="165,52" backgroundColor="key_red" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_yellow" conditional="key_yellow" render="Label" objectTypes="key_yellow,StaticText" position="541,965" zPosition="2" size="165,52" backgroundColor="key_yellow" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_epg" render="Label" conditional="key_epg" position="717,965" zPosition="4" size="165,52" backgroundColor="key_back" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_help" render="Label" conditional="key_help" position="893,965" zPosition="4" size="165,52" backgroundColor="key_back" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_play" render="Label" conditional="key_play" position="1069,965" zPosition="4" size="165,52" backgroundColor="key_back" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_volumeup" render="Label" conditional="key_volumeup" position="1245,965" zPosition="4" size="165,52" backgroundColor="key_back" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_volumedown" render="Label" conditional="key_volumedown" position="1421,965" zPosition="4" size="165,52" backgroundColor="key_back" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_stop" render="Label" conditional="key_stop" position="1597,965" zPosition="4" size="165,52" backgroundColor="key_back" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_0" render="Label" conditional="key_0" position="1772,965" zPosition="12" size="60,52" backgroundColor="key_back" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_tv" conditional="key_tv" render="Label" position="12,928" size="165,35" zPosition="12" backgroundColor="key_back" font="Regular;20" horizontalAlignment="center" verticalAlignment="center">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_audio" render="Label" conditional="key_audio" position="189,928" zPosition="12" size="165,35" backgroundColor="key_back" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_rec" render="Label" conditional="key_rec" position="365,928" zPosition="12" size="165,35" backgroundColor="key_back" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
				<convert type="ConditionalShowHide"/>
			</widget>
			<widget source="key_menu" render="Label" conditional="key_menu" position="541,928" zPosition="12" size="165,35" backgroundColor="key_back" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
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
			<widget source="key_menu" render="Label" conditional="key_menu" position="357,560" zPosition="12" size="110,25" backgroundColor="key_back" font="Regular;18" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
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
		self.m3ufile = None
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
		self["key_menu"] = StaticText("")
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
			"menu": self.removeScript,
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
		except:
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
					fw.write("[IPToSat]" + "\n" + 'Host=http://hostname:port' + "\n" + "User=user" + "\n" + "Pass=pass")
			for partition in harddiskmanager.getMountedPartitions():
				self.path = normpath(partition.mountpoint)
				if self.path != "/" and "net" not in self.path and "autofs" not in self.path:
					if exists(str(self.path)) and listdir(self.path):
						self.storage = True
						self.backupdirectory = join(self.path, "IPToSAT/%s/BackupChannelsList" % MODEL)
						self.alternatefolder = join(self.path, "IPToSAT/%s/AlternateList" % MODEL)
						self.changefolder = join(self.path, "IPToSAT/%s/ChangeSuscriptionList" % MODEL)
						self.m3ufolder = join(self.path, "IPToSAT/%s/M3U" % MODEL)
						self.m3ufile = join(self.m3ufolder, "iptosat_norhap.m3u")
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
		try:  # user help move old directory REMOVE LINE 552 to 576 coming soon
			for partition in harddiskmanager.getMountedPartitions():
				self.path = normpath(partition.mountpoint)
				if self.path != "/" and "net" not in self.path and "autofs" not in self.path:
					if exists(str(self.path)) and listdir(self.path):
						oldbackupdirectory = join(self.path, "IPToSAT/BackupChannelsList")
						oldealternatefolder = join(self.path, "IPToSAT/AlternateList")
						oldchangefolder = join(self.path, "IPToSAT/ChangeSuscriptionList")
						oldm3ufolder = join(self.path, "IPToSAT/M3U")
						oldchannelslists = join(self.path, "IPToSAT/ChannelsLists")
						newdirectorywork = join(self.path, "IPToSAT/" + MODEL)
						if not exists(str(newdirectorywork)):
							makedirs(newdirectorywork)
						if exists(str(oldbackupdirectory)):
							move(oldbackupdirectory, newdirectorywork)
						if exists(str(oldealternatefolder)):
							move(oldealternatefolder, newdirectorywork)
						if exists(str(oldchangefolder)):
							move(oldchangefolder, newdirectorywork)
						if exists(str(oldm3ufolder)):
							move(oldm3ufolder, newdirectorywork)
						if exists(str(oldchannelslists)):
							eConsoleAppContainer().execute("rm -rf " + oldchannelslists)
		except Exception as err:
			print("ERROR: %s" % str(err))
		if not fileContains(CONFIG_PATH, "pass"):
			if exists(str(self.m3ufile)):
				self["key_yellow"].setText(language.get(lang, "32"))
			else:
				self["key_yellow"].setText(language.get(lang, "74"))

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
		except:
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
		if exists(SOURCE_BOUQUET_IPTV):
			self["key_menu"] = StaticText("MENU")
			self["codestatus"].show()
			self["codestatus"].setText(language.get(lang, "6"))
		else:
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
			except:
				trace_error()
				self.errortimer.start(200, True)
		else:
			log('%s, No such file or directory' % CONFIG_PATH)
			self.close(True)

	def errorMessage(self):
		self.session.openWithCallback(self.exit, MessageBox, language.get(lang, "19"), MessageBox.TYPE_ERROR, timeout=10)

	def getCategories(self, url):
		url += '&action=get_live_categories'
		self.callAPI(url, self.getData)

	def getUserSuscription(self, url):
		self.suscription(url, self.getSuscriptionData)

	def channelSelected(self):
		if exists(SOURCE_BOUQUET_IPTV):
			self["codestatus"].setText(language.get(lang, "6"))
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
		if exists(SOURCE_BOUQUET_IPTV):
			self["codestatus"].setText(language.get(lang, "6"))
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
		playlist = getPlaylist()
		if playlist:
			if sref.startswith('1') and 'http' not in sref:
				url = self.host + '/' + self.user + '/' + self.password + '/' + stream_id
				if not fileContains(PLAYLIST_PATH, sref):
					from unicodedata import normalize
					playlist['playlist'].append({'sref': sref, 'channel': normalize('NFKD', channel_name).encode('ascii', 'ignore').decode(), 'url': url})
					with open(PLAYLIST_PATH, 'w') as f:
						dump(playlist, f, indent=4)
					if fileContains(PLAYLIST_PATH, sref):
						text = (channel_name + " " + language.get(lang, "21") + " " + xtream_channel)
						self.assignWidget("#86dc3d", text)
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

	def removeScript(self):
		if exists(SOURCE_BOUQUET_IPTV):
			self.Console.ePopen("rm -f " + SOURCE_BOUQUET_IPTV)
			if not exists(SOURCE_BOUQUET_IPTV):
				text = (language.get(lang, "35"))
				self['codestatus'].hide()
				self['managerlistchannels'].show()
				self.assignWidgetScript("#86dc3d", text)
				self["key_menu"].setText("")

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
			backupfiles = ""
			enigma2files = ""
			if answer:
				self.session.open(MessageBox, language.get(lang, "77"), MessageBox.TYPE_INFO, simple=True)
				for files in [x for x in listdir(self.backupdirectory) if "alternatives." in x or "whitelist" in x or "lamedb" in x or "iptosat.conf" in x or "iptosat.json" in x or "iptosatchlist.json" in x or "iptosatreferences" in x or x.endswith(".radio") or x.endswith(".tv") or "blacklist" in x]:
					backupfiles = join(self.backupdirectory, files)
					if backupfiles:
						for fileschannelslist in [x for x in listdir(ENIGMA2_PATH) if "alternatives." in x or "whitelist" in x or "lamedb" in x or x.startswith("iptosat.conf") or x.startswith("iptosat.json") or x.startswith("iptosatchlist.json") or x.startswith("iptosatreferences") or ".radio" in x or ".tv" in x or "blacklist" in x]:
							enigma2files = join(ENIGMA2_PATH, fileschannelslist)
							if enigma2files:
								remove(enigma2files)
				eConsoleAppContainer().execute('init 4 && sleep 5 && cp -a ' + self.backupdirectory + "/" + "*" + " " + ENIGMA2_PATH + "/" + ' && init 3')
		except Exception as err:
			self.session.open(MessageBox, "ERROR: %s" % str(err), MessageBox.TYPE_ERROR, default=False, timeout=10)

	def installChannelsList(self):
		if self.storage:
			try:
				backupfiles = ""
				for files in [x for x in listdir(self.backupdirectory) if "alternatives." in x or "whitelist" in x or "lamedb" in x or "iptosat.conf" in x or "iptosat.json" in x or "iptosatchlist.json" in x or "iptosatreferences" in x or x.endswith(".radio") or x.endswith(".tv") or "blacklist" in x or "settings" in x]:
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
				for files in [x for x in listdir(self.backupdirectory) if "alternatives." in x or "whitelist" in x or "lamedb" in x or "iptosat.conf" in x or "iptosat.json" in x or "iptosatchlist.json" in x or "iptosatreferences" in x or x.endswith(".radio") or x.endswith(".tv") or "blacklist" in x]:
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
			if answer:
				for files in [x for x in listdir(self.backupdirectory) if "alternatives." in x or "whitelist" in x or "lamedb" in x or "iptosat.conf" in x or "iptosat.json" in x or "iptosatchlist.json" in x or "iptosatreferences" in x or x.endswith(".radio") or x.endswith(".tv") or "blacklist" in x or "settings" in x]:
					backupfiles = join(self.backupdirectory, files)
					remove(backupfiles)
				for fileschannelslist in [x for x in listdir(ENIGMA2_PATH) if "alternatives." in x or "whitelist" in x or "lamedb" in x or x.endswith("iptosat.conf") or x.endswith("iptosat.json") or x.endswith("iptosatchlist.json") or x.endswith("iptosatreferences") or x.endswith(".radio") or x.endswith(".tv") or "blacklist" in x or "settings" in x]:
					enigma2files = join(ENIGMA2_PATH, fileschannelslist)
					if enigma2files:
						copy(enigma2files, self.backupdirectory)
						bouquetiptosatepg = join(self.backupdirectory, FILE_IPToSAT_EPG)
					if fileContains(CONFIG_PATH, "pass"):
						self["status"].show()
				self['managerlistchannels'].show()
				self.assignWidgetScript("#86dc3d", language.get(lang, "66"))
				self["key_rec"].setText("REC")
				self["key_audio"].setText("AUDIO")
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
				enigma2files = ""
				if not exists(str(self.backupdirectory)):
					makedirs(self.backupdirectory)
				for backupfiles in [x for x in listdir(self.backupdirectory) if "alternatives." in x or "whitelist" in x or "lamedb" in x or x.endswith("iptosat.conf") or x.endswith("iptosat.json") or x.endswith("iptosatchlist.json") or x.endswith("iptosatreferences") or x.endswith(".radio") or x.endswith(".tv") or "blacklist" in x or "settings" in x]:
					backupfiles = join(self.backupdirectory, backupfiles)
				if backupfiles:
					self.session.openWithCallback(self.dobackupChannelsList, MessageBox, language.get(lang, "63") + " " + self.backupdirectory + "/" + "\n\n" + language.get(lang, "64"), MessageBox.TYPE_YESNO)
				else:
					self.session.openWithCallback(self.dobackupChannelsList, MessageBox, language.get(lang, "65"), MessageBox.TYPE_YESNO)
			except Exception as err:
				print("ERROR: %s" % str(err))

	def tryToUpdateIPTVChannels(self, answer):
		if answer:
			with open(SOURCE_BOUQUET_IPTV, "r") as fr:
				riptvsh = fr.readlines()
				for line in riptvsh:
					bouquetname = line.split("bouquet=")[1].split(";")[0]
					with open(SOURCE_BOUQUET_IPTV, "w") as fw:
						createbouquet = line.replace(bouquetname, '"iptv_iptosat"')
						fw.write(createbouquet)
			createbouquet = ""
			eConsoleAppContainer().execute(SOURCE_BOUQUET_IPTV)
			sleep(2)
			for filelist in [x for x in listdir(ENIGMA2_PATH) if "iptv_iptosat" in x and x.endswith(".tv")]:
				bouquetiptv = join(filelist)
				with open(ENIGMA2_PATH_LISTS + bouquetiptv, "r") as fr:
					lines = fr.readlines()
					for content in lines:
						createnamebouquet = content.replace("#NAME", "#NAME IPTV_IPToSAT")
						BouquetIPToSAT = createnamebouquet.replace("#NAME IPTV_IPToSAT", "IPTV_IPToSAT")
						createbouquet = createbouquet + createnamebouquet
						with open(ENIGMA2_PATH_LISTS + bouquetiptv, "w",) as fw:
							fw.write(createbouquet + "\n" + content)
							if exists(SOURCE_BOUQUET_IPTV):
								eConsoleAppContainer().execute('rm -f ' + SOURCE_BOUQUET_IPTV)
						if "IPTV_IPToSAT" in BouquetIPToSAT and not self.storage and not config.plugins.IPToSAT.downloadcategories.value:
							self.session.open(MessageBox, "Bouquet" + " " + BouquetIPToSAT + "\n\n" + language.get(lang, "38"), MessageBox.TYPE_INFO, simple=True, timeout=10)
						elif "IPTV_IPToSAT" in BouquetIPToSAT and exists(str(self.m3ufile)):
							self['managerlistchannels'].show()
							if config.plugins.IPToSAT.downloadcategories.value:
								self.assignWidgetScript("#e5e619", "Bouquet IPTV_IPToSAT " + language.get(lang, "5") + "\n" + language.get(lang, "100") + " " + self.m3ufile + "\n" + language.get(lang, "123"))
								eConsoleAppContainer().execute("ln -s " + str(self.m3ufile) + " " + ENIGMA2_PATH_LISTS + " ; python " + BUILDBOUQUETS_SOURCE + " ; mv /etc/enigma2/userbouquet.iptosat_norhap.tv.del /etc/enigma2/userbouquet.iptosat_norhap.tv ; wget -qO - http://127.0.0.1/web/servicelistreload?mode=2 ; wget -qO - http://127.0.0.1/web/servicelistreload?mode=2 ; rm -f " + ENIGMA2_PATH_LISTS + "iptosat_norhap.m3u")
		else:
			self.channelSelected()
			if exists(SOURCE_BOUQUET_IPTV):
				eConsoleAppContainer().execute('rm -f ' + SOURCE_BOUQUET_IPTV)

	def createBouquetIPTV(self):
		if exists(str(BUILDBOUQUETS_FILE)):
			move(BUILDBOUQUETS_FILE, BUILDBOUQUETS_SOURCE)
		if exists(CONFIG_PATH) and not fileContains(CONFIG_PATH, "pass"):
			try:
				with open(CONFIG_PATH, "r") as fr:
					configfile = fr.read()
					hostport = configfile.split()[1].split("Host=")[1]
					user = configfile.split()[2].split('User=')[1]
					password = configfile.split()[3].split('Pass=')[1]
					if self.storage:
						if not exists(str(self.m3ufolder)):
							makedirs(self.m3ufolder)
						if exists(str(self.m3ufile)):
							remove(self.m3ufile)
						if config.plugins.IPToSAT.deletecategories.value:
							for bouquets_iptosat_norhap in [x for x in listdir(ENIGMA2_PATH) if "norhap" in x]:
								with open(BOUQUETS_TV, "r") as fr:
									bouquetread = fr.readlines()
									with open(BOUQUETS_TV, "w") as bouquetswrite:
										for line in bouquetread:
											if "norhap" not in line:
												bouquetswrite.write(line)
								enigma2files = join(ENIGMA2_PATH, bouquets_iptosat_norhap)
								if enigma2files:
									remove(enigma2files)
						eConsoleAppContainer().execute('wget -O ' + SOURCE_BOUQUET_IPTV + " " + '"' + hostport + '/get.php?username=' + user + '&password=' + password + '&type=enigma22_script&output=mpegts"' + " " + '&& chmod 755 ' + SOURCE_BOUQUET_IPTV + ' ; wget -O ' + self.m3ufile + " " + '"' + hostport + '/get.php?username=' + user + '&password=' + password + '&type=m3u_plus&output=mpegts"')
						sleep(3)
					else:
						eConsoleAppContainer().execute('wget -O ' + SOURCE_BOUQUET_IPTV + " " + '"' + hostport + '/get.php?username=' + user + '&password=' + password + '&type=enigma22_script&output=mpegts"' + " " + '&& chmod 755 ' + SOURCE_BOUQUET_IPTV)
						sleep(3)
					if exists(SOURCE_BOUQUET_IPTV):
						with open(SOURCE_BOUQUET_IPTV, "r") as fr:
							createbouquet = ""
							riptvsh = fr.readlines()
							for line in riptvsh:
								bouquetname = line.split("bouquet=")[1].split(";")[0]
								if " " in str(bouquetname) or "  " in str(bouquetname):
									with open(SOURCE_BOUQUET_IPTV, "w") as fw:
										bouquetrename = str(bouquetname).replace(' ', '_').replace(' ', '_')
										createbouquet = line.replace(bouquetname, bouquetrename)
										fw.write(createbouquet)
										eConsoleAppContainer().execute(SOURCE_BOUQUET_IPTV)
										if exists(str(self.m3ufile)):
											self["helpbouquetepg"].hide()
											self['managerlistchannels'].show()
											self['codestatus'].show()
											self["key_menu"].setText("MENU")
											if config.plugins.IPToSAT.downloadcategories.value:
												self.assignWidgetScript("#e5e619", "Bouquet IPTV" + " " + str(bouquetname) + " " + language.get(lang, "5") + "\n" + language.get(lang, "100") + " " + self.m3ufile + "\n" + language.get(lang, "122"))
												eConsoleAppContainer().execute("ln -s " + str(self.m3ufile) + " " + ENIGMA2_PATH_LISTS + " ; python " + BUILDBOUQUETS_SOURCE + " ; mv /etc/enigma2/userbouquet.iptosat_norhap.tv.del /etc/enigma2/userbouquet.iptosat_norhap.tv ; wget -qO - http://127.0.0.1/web/servicelistreload?mode=2 ; wget -qO - http://127.0.0.1/web/servicelistreload?mode=2 ; rm -f " + ENIGMA2_PATH_LISTS + "iptosat_norhap.m3u")
											else:
												self.assignWidgetScript("#e5e619", "Bouquet IPTV" + " " + str(bouquetname) + " " + language.get(lang, "5"))
										else:
											self["helpbouquetepg"].hide()
											self['managerlistchannels'].show()
											self['codestatus'].show()
											self["key_menu"].setText("MENU")
											self.assignWidgetScript("#e5e619", "Bouquet IPTV" + " " + str(bouquetname) + " " + language.get(lang, "5"))
								elif 'bouquet=""' not in line:
									eConsoleAppContainer().execute(SOURCE_BOUQUET_IPTV)
									if exists(str(self.m3ufile)):
										self["helpbouquetepg"].hide()
										self['managerlistchannels'].show()
										self['codestatus'].show()
										self["key_menu"].setText("MENU")
										if config.plugins.IPToSAT.downloadcategories.value:
											self.assignWidgetScript("#e5e619", "Bouquet IPTV" + " " + str(bouquetname) + " " + language.get(lang, "5") + "\n" + language.get(lang, "100") + " " + self.m3ufile + "\n" + language.get(lang, "122"))
											eConsoleAppContainer().execute("ln -s " + str(self.m3ufile) + " " + ENIGMA2_PATH_LISTS + " ; python " + BUILDBOUQUETS_SOURCE + " ; mv /etc/enigma2/userbouquet.iptosat_norhap.tv.del /etc/enigma2/userbouquet.iptosat_norhap.tv ; wget -qO - http://127.0.0.1/web/servicelistreload?mode=2 ; wget -qO - http://127.0.0.1/web/servicelistreload?mode=2 ; rm -f " + ENIGMA2_PATH_LISTS + "iptosat_norhap.m3u")
										else:
											self.assignWidgetScript("#e5e619", "Bouquet IPTV" + " " + str(bouquetname) + " " + language.get(lang, "5"))
									else:
										self["helpbouquetepg"].hide()
										self['managerlistchannels'].show()
										self['codestatus'].show()
										self["key_menu"].setText("MENU")
										self.assignWidgetScript("#e5e619", "Bouquet IPTV" + " " + str(bouquetname) + " " + language.get(lang, "5"))
								else:
									self.session.openWithCallback(self.tryToUpdateIPTVChannels, MessageBox, language.get(lang, "8"), MessageBox.TYPE_YESNO, default=False)
					if exists(str(self.m3ufile)) and not isPluginInstalled("MediaPlayer"):
						eConsoleAppContainer().execute('opkg update && opkg install enigma2-plugin-extensions-mediaplayer')
			except Exception as err:
				self.session.open(MessageBox, "ERROR: %s" % str(err), MessageBox.TYPE_ERROR, default=False, timeout=10)
		else:
			self.session.open(MessageBox, language.get(lang, "33"), MessageBox.TYPE_ERROR, default=False)

	def setEPGChannel(self):
		self['managerlistchannels'].hide()
		sref = str(self.getSref())
		channel_name = str(ServiceReference(sref).getServiceName())
		if self.selectedList == self["list"]:
			self.addEPGChannel(channel_name, sref)

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

	def addEPGChannel(self, channel_name, sref):
		ref = self.getCurrentSelection()
		if (ref.flags & 7) == 7:  # this is bouquet selection no channel!!
			self.session.open(MessageBox, language.get(lang, "84"), MessageBox.TYPE_ERROR, simple=True, timeout=5)
		elif not config.plugins.IPToSAT.downloadcategories.value and self.storage and not fileContains(CONFIG_PATH, "pass"):  # for download EPG to YES.
			self.session.open(MessageBox, language.get(lang, "130"), MessageBox.TYPE_ERROR, simple=True)
		else:
			try:
				epg_channel_name = channel_name.upper()
				characterascii = [epg_channel_name]
				satreferencename = ""
				bouquetnamemsgbox = ""
				bouquetname = ""
				stream_iptv = ""
				bouquetiptosatepg = ""
				if exists(IPToSAT_EPG_PATH) and fileContains(IPToSAT_EPG_PATH, epg_channel_name) and not fileContains(IPToSAT_EPG_PATH, sref.upper()):  # remove old channel with sref old
					with open(IPToSAT_EPG_PATH, "r") as iptosat_epg_read:
						bouquetiptosatepg = iptosat_epg_read.readlines()
					with open(IPToSAT_EPG_PATH, "w") as iptosat_epg_write:
						for channel in bouquetiptosatepg:
							if epg_channel_name in channel and "http" in channel and "%3a " not in channel:  # replace reference old -> condition two points + channel_name
								changereference = channel.split("http")[1]
								channel = "#SERVICE " + sref + "http" + changereference
							if epg_channel_name not in channel and "%3a " not in channel or epg_channel_name + " " + "HD" not in channel and "%3a " not in channel or "#DESCRIPTION " + epg_channel_name not in channel and "#SERVICE" in channel:
								iptosat_epg_write.write(channel)
					self.session.open(MessageBox, language.get(lang, "76") + " " + epg_channel_name, MessageBox.TYPE_INFO, simple=True)
				for character in characterascii:
					if search(r'[ÁÉÍÓÚÑ]', character):
						epg_channel_name = character.replace("Ñ", "N").replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")
				for filelist in [x for x in listdir(ENIGMA2_PATH) if x.endswith(".tv") and not x.endswith("userbouquet.iptosat_norhap.tv") and exists(str(self.m3ufile)) or x.endswith(".tv") and not exists(str(self.m3ufile)) or x.endswith(".radio")]:
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
										bouquetname = line
									if ":" + epg_channel_name in line and "http" in line:
										sat_reference_name = line.replace(ref, self.getSref()).replace("::", ":").replace("0:" + epg_channel_name, "0").replace("C00000:0:0:0:00000:0:0:0", "C00000:0:0:0").replace("#DESCRIPT" + sref, "").replace("C00000:0:0:0:0000:0:0:0:0000:0:0:0:0000:0:0:0", "C00000:0:0:0").replace(":0000:0:0:0", "")
										satreferencename = sat_reference_name
						if "http" in str(satreferencename):
							with open(ENIGMA2_PATH_LISTS + bouquetiptv, "w") as fw:
								with open(WILD_CARD_EPG_FILE, "r") as fr:
									lineNAME = fr.readlines()
									for line in lineNAME:
										fw.write(line)
							with open(ENIGMA2_PATH_LISTS + bouquetiptv, "w") as fw:
								fw.write(bouquetname + "\n" + satreferencename + "\n" + "#DESCRIPTION " + epg_channel_name + "\n")
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
							if exists(WILD_CARD_EPG_FILE):
								self.Console.ePopen("rm -f " + WILD_CARD_EPG_FILE)
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
				for filelist in [x for x in listdir(ENIGMA2_PATH) if x.endswith(".tv") and not x.endswith("userbouquet.iptosat_norhap.tv") and exists(str(self.m3ufile)) or x.endswith(".tv") and not exists(str(self.m3ufile)) or x.endswith(".radio")]:
					bouquets_categories = join(filelist)
					with open(ENIGMA2_PATH_LISTS + bouquets_categories, "r") as file:
						lines = file.readlines()
						for line in lines:
							if sref in line and "http" in line and ":" + epg_channel_name not in line:
								replacement = line.replace(".ts", ".ts" + ":" + epg_channel_name).replace(".m3u8", ".m3u8" + ":" + epg_channel_name).replace(".m3u", ".m3u" + ":" + epg_channel_name) # add condition -> two points + channel_name for change old reference
								if ":" + epg_channel_name + ":" in replacement:  # remove one :channel_name (two channels name in bouquets_categories)
									if ".ts" in replacement:
										line = replacement.split(".ts:" + epg_channel_name)[0] + ".ts:" + epg_channel_name + "\n"
									elif ".m3u8" in replacement:
										line = replacement.split(".m3u8:" + epg_channel_name)[0] + ".m3u8:" + epg_channel_name + "\n"
									else:
										line = replacement.split(".m3u:" + epg_channel_name)[0] + ".m3u:" + epg_channel_name + "\n"
								else:
									line = replacement
							if sref in line and "http" in line:
								stream_iptv = line
				if stream_iptv and not fileContains(IPToSAT_EPG_PATH, epg_channel_name):  # add stream IPTV with EPG to IPToSAT_EPG
					if not fileContains(IPToSAT_EPG_PATH, '#NAME IPToSAT_EPG'):
						with open(IPToSAT_EPG_PATH, "w") as fw:
							fw.write('#NAME IPToSAT_EPG' + "\n")
					else:
						with open(IPToSAT_EPG_PATH, "a") as fw:
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
			self.resultEditionBouquets(epg_channel_name, sref)

	def resultEditionBouquets(self, channel_name, sref):
		try:
			sref_update = sref.upper()
			characterascii = [channel_name]
			epg_channel_name = channel_name.upper()
			bouquetname = ""
			if exists(REFERENCES_FILE):
				try:
					for character in characterascii:
						if search(r'[áÁéÉíÍóÓúÚñÑM+m+.]', channel_name):
							channel_name = character.replace(" ", "").replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "o").replace("Ú", "U").replace("M+", "M").replace("MOVISTAR+", "").replace("MOVISTAR", "").replace("+", "").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("Ñ", "N").replace("movistar+", "").replace("m+", "m").replace("movistar", "").replace(".", "").encode('ascii', 'ignore').decode()
						if not fileContains(REFERENCES_FILE, channel_name.lower()):
							with open(REFERENCES_FILE, "a") as updatefile:
								updatefile.write("\n" + str(channel_name).lower() + "-->" + str(sref_update) + "-->1")
					with open(REFERENCES_FILE, "r") as file:  # clear old services references
						filereference = file.readlines()
						with open(REFERENCES_FILE, "w") as finalfile:
							for line in filereference:
								if str(channel_name).lower() + "." in line and str(sref_update) in line or str(channel_name).lower() in line and str(sref_update) in line or str(channel_name).lower() not in line and str(sref_update) not in line:
									finalfile.write(line)
				except Exception:
					pass
			if exists(IPToSAT_EPG_PATH) and not fileContains(IPToSAT_EPG_PATH, "#SERVICE"):
				self.addEPGChannel(channel_name, sref)
			if fileContains(IPToSAT_EPG_PATH, epg_channel_name) and fileContains(IPToSAT_EPG_PATH, sref):
				self.session.open(MessageBox, language.get(lang, "24") + epg_channel_name + "\n\n" + language.get(lang, "94") + "\n\n" + FILE_IPToSAT_EPG.replace("userbouquet.", "").replace(".tv", "").upper(), MessageBox.TYPE_INFO, simple=True)
			try:
				with open(SOURCE_BOUQUET_IPTV, "r") as fr:
					riptvsh = fr.readlines()
					for line in riptvsh:
						bouquetname = line.split("bouquet=")[1].split(";")[0]
			except Exception as err:
				print("ERROR: %s" % str(err))
			if exists(str(self.m3ufile)) and not fileContains(CONFIG_PATH, "pass"):
				if not fileContains(IPToSAT_EPG_PATH, epg_channel_name) and not fileContains(IPToSAT_EPG_PATH, sref) and bouquetname:  # Warning for channel without bouquet suscription IPTV -> then make manual EPG -> :CHANNEL NAME
					self.session.open(MessageBox, language.get(lang, "128") + ENIGMA2_PATH + "/userbouquet." + bouquetname.replace('"', '') + "__"  + "tv_.tv" + "\n\n" + language.get(lang, "129") + "\n\n" + ":" + epg_channel_name + "\n\n" + language.get(lang, "124"), MessageBox.TYPE_ERROR)
				elif not fileContains(IPToSAT_EPG_PATH, epg_channel_name) and not fileContains(IPToSAT_EPG_PATH, sref):  # Warning for channel without bouquet suscription IPTV -> then make manual EPG -> :CHANNEL NAME
					self.session.open(MessageBox, language.get(lang, "83") + "\n\n" + ":" + epg_channel_name + "\n\n" + language.get(lang, "124"), MessageBox.TYPE_ERROR)
			else:
				if not fileContains(IPToSAT_EPG_PATH, ":" + epg_channel_name):  # make manual EPG -> :CHANNEL NAME
					self.session.open(MessageBox, language.get(lang, "131") + language.get(lang, "129") + "\n\n" + ":" + epg_channel_name, MessageBox.TYPE_ERROR)
			if epg_channel_name == ".":  # it is not a valid channel
				self.session.open(MessageBox, language.get(lang, "125"), MessageBox.TYPE_ERROR)
		except Exception as err:
			print("ERROR: %s" % str(err))

	def purge(self):
		if self.storage:
			iptosatconf = join(self.alternatefolder, "iptosat.conf")
			iptosat2conf = join(self.changefolder, "iptosat.conf")
			if exists(str(iptosatconf)) or exists(str(iptosat2conf)):
				self.session.openWithCallback(self.purgeDeviceFiles, MessageBox, language.get(lang, "57"), MessageBox.TYPE_YESNO, default=False)
			else:
				self.session.open(MessageBox, language.get(lang, "43"), MessageBox.TYPE_INFO)

	def purgeDeviceFiles(self, answer):
		if answer:
			try:
				iptosatconf = join(self.alternatefolder, "iptosat.conf")
				iptosat2conf = join(self.changefolder, "iptosat.conf")
				if exists(str(iptosatconf)):
					remove(iptosatconf)
				if exists(str(iptosat2conf)):
					remove(iptosat2conf)
				if not exists(str(iptosatconf)) or not exists(str(iptosat2conf)):
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
				if exists(str(iptosat2conf)):
					if exists(str(iptosatlist2conf)) or exists(str(iptosatlist1conf)):
						remove(iptosat2conf)
				if not exists(str(self.alternatefolder)):
					makedirs(self.alternatefolder)
				if not exists(str(iptosat2conf)) and not exists(str(iptosatlist1conf)) and not exists(str(iptosatlist2conf)):
					self.session.open(MessageBox, language.get(lang, "40") + "\n\n" + self.alternatefolder + "/", MessageBox.TYPE_INFO)
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
				self.getUserData()
				IPToSATSetup.saveConfig(self)
				self["codestatus"].hide()
			except Exception as err:
				print("ERROR: %s" % str(err))

	def doChangeList(self, answer):
		try:
			iptosatlist1conf = join(self.alternatefolder, "iptosat_LIST1.conf")
			iptosat2change = join(self.changefolder, "iptosat.conf")
			iptosatconf = join(self.alternatefolder, "iptosat.conf")
			fileconf = join(ENIGMA2_PATH, "iptosat.conf")
			if answer:
				if exists(str(iptosat2change)):
					move(iptosat2change, iptosatlist1conf)
					IPToSATSetup.saveConfig(self)
			else:
				self.session.open(MessageBox, language.get(lang, "46") + "\n\n" + language.get(lang, "42"), MessageBox.TYPE_INFO)
		except Exception as err:
			print("ERROR: %s" % str(err))

	def doChangeList2(self, answer):
		try:
			fileconf = join(ENIGMA2_PATH, "iptosat.conf")
			iptosatlist2conf = join(self.alternatefolder, "iptosat_LIST2.conf")
			iptosat2change = join(self.changefolder, "iptosat.conf")
			iptosatconf = join(self.alternatefolder, "iptosat.conf")
			if answer:
				move(iptosat2change, iptosatlist2conf)
				IPToSATSetup.saveConfig(self)
			else:
				self.session.open(MessageBox, language.get(lang, "46") + "\n\n" + language.get(lang, "42"), MessageBox.TYPE_INFO)
		except Exception as err:
			print("ERROR: %s" % str(err))

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
					with open(iptosatlist1conf, "r") as f:
						host = f.read()
						self.host = host.split()[1].split('Host=')[1].split(':')[1].replace("//", "http://") if not fileContains(iptosatlist1conf, "https") else host.split()[1].split('Host=')[1].split(':')[1].replace("//", "https://")
					self.session.openWithCallback(self.doChangeList, MessageBox, language.get(lang, "48") + self.host + "\n\n" + language.get(lang, "45"), MessageBox.TYPE_YESNO, default=False)
				if exists(str(iptosatlist1conf)) and not exists(str(iptosat2change)):
					self.session.open(MessageBox, language.get(lang, "55") + "\n\n" + self.changefolder + "/" + language.get(lang, "56"), MessageBox.TYPE_INFO)
				if exists(str(iptosatlist2conf)) and exists(str(iptosat2change)):
					with open(iptosatlist2conf, "r") as f:
						host = f.read()
						self.host = host.split()[1].split('Host=')[1].split(':')[1].replace("//", "http://") if not fileContains(iptosatlist2conf, "https") else host.split()[1].split('Host=')[1].split(':')[1].replace("//", "https://")
					self.session.openWithCallback(self.doChangeList2, MessageBox, language.get(lang, "48") + self.host + "\n\n" + language.get(lang, "45"), MessageBox.TYPE_YESNO, default=False)
				if exists(str(iptosatlist2conf)) and not exists(str(iptosat2change)):
					self.session.open(MessageBox, language.get(lang, "55") + "\n\n" + self.changefolder + "/" + language.get(lang, "56"), MessageBox.TYPE_INFO)
				self.getUserData()
				IPToSATSetup.saveConfig(self)
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
		self['assign'].instance.setForegroundColor(parseColor(color))
		self['status'].hide()

	def assignWidgetScript(self, color, text):
		self['managerlistchannels'].setText(text)
		self['managerlistchannels'].instance.setForegroundColor(parseColor(color))

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
				if fileContains(CONFIG_PATH, "pass") and self.storage:
					self["status"].setText(language.get(lang, "3"))
					self["please"].hide()
					self["codestatus"].hide()
					self["key_menu"].setText("")
				if fileContains(CONFIG_PATH, "pass") and not self.storage:
					self["description"].hide()
					self["status"].setText(language.get(lang, "72"))
					self["codestatus"].hide()
					self["key_menu"].setText("")
				if not fileContains(CONFIG_PATH, "pass"):
					self.session.openWithCallback(self.exit, MessageBox, language.get(lang, "4"), MessageBox.TYPE_ERROR)
		except Exception as err:
			print("ERROR: %s" % str(err))

	def getData(self, data):
		list = []
		bouquets_categories = []
		js = loads(data)
		if js != []:
			for cat in js:
				list.append((str(cat['category_name']),
					str(cat['category_id'])))
				if not search(r'[/]', str(cat['category_name'])):
					bouquets_categories.append((str(cat['category_name']), str(cat['category_name'])))
		self['list2'].show()
		self["please"].hide()
		self['list2'].l.setList(list)
		self.categories = list
		self.bouquets = bouquets_categories
		self.in_channels = False
		iptosatcategoriesjson = ""
		with open(CONFIG_PATH_CATEGORIES, "w") as categories:
			dump(self.bouquets, categories)
		with open(CONFIG_PATH_CATEGORIES, "r") as m3ujsonread:
			iptosatcategoriesjson = m3ujsonread.read()
		with open(CONFIG_PATH_CATEGORIES, "w") as m3ujsonwrite:
			m3ujsonwrite.write("{" + "\n" + '	"CATEGORIES": {' + "\n" + '		' + iptosatcategoriesjson.replace('[[', '').replace('["', '"').replace('", "', '":').replace('":', '": ["').replace('"]]', '"]').replace('], "', '],' + "\n" + '        "') + "\n" + "	}" + "\n" + "}")

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
						self.assignWidgetScript("#86dc3d", language.get(lang, "109") + " " + expires + "\n" + language.get(lang, "106") + " " + status + " " + language.get(lang, "118") + " " + active_cons + "\n" + anguage.get(lang, "107") + " " + max_connections + " " + language.get(lang, "119"))
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

	def getChannels(self, data):
		sref = str(self.getSref())
		channel_satellite = str(ServiceReference(sref).getServiceName())
		search_name = channel_satellite[2:6]  # criteria 5 bytes to search for matches
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
			ref = self.getCurrentSelection()
			self.showFavourites()
			self.in_bouquets = False
		elif self.selectedList == self["list2"] and self.in_channels and not fileContains(CONFIG_PATH, "pass"):
			self.getCategories(self.url)
		else:
			self.close(True)


class EditPlaylist(Screen):
	skin = """
	<screen name="PlaylistEditPlaylistIPToSAT" position="center,center" size="1400,650" title="IPToSAT - Edit">
		<widget name="list" itemHeight="40" position="18,22" size="1364,520" scrollbarMode="showOnDemand"/>
		<widget source="key_red" render="Label" objectTypes="key_red,StaticText" position="7,583" zPosition="2" size="165,52" backgroundColor="key_red" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
			<convert type="ConditionalShowHide"/>
		</widget>
		<widget source="key_green" render="Label" objectTypes="key_red,StaticText" position="183,583" zPosition="2" size="165,52" backgroundColor="key_green" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
			<convert type="ConditionalShowHide"/>
		</widget>
		<widget name="status" position="360,562" size="860,89" font="Regular;20" horizontalAlignment="left" verticalAlignment="center" zPosition="3"/>
		<widget name="HelpWindow" position="0,0" size="0,0" alphaTest="blend" conditional="HelpWindow" transparent="1" zPosition="+1" />
	</screen>"""

	def __init__(self, session, *args):
		self.session = session
		Screen.__init__(self, session)
		self.skinName = ["EditPlaylistIPToSAT"]
		self.setTitle(language.get(lang, "26"))
		self['list'] = MenuList([])
		self["key_red"] = StaticText("")
		self["key_green"] = StaticText("")
		self["status"] = Label()
		self["iptosatactions"] = ActionMap(["IPToSATActions"],
		{
			"back": self.close,
			"cancel": self.exit,
			"red": self.keyRed,
			"green": self.keyGreen,
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
						with open(PLAYLIST_PATH, 'w')as f:
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
			for channel in self.playlist['playlist']:
				try:
					reference = channel['sref'][7:11] if ":" not in channel['sref'][7:11] else channel['sref'][6:10]
					list.append(str(channel['channel'] + "   " + reference))
				except KeyError:
					pass
			if len(list) > 0:
				self['list'].l.setList(list)
				self.channels = sorted(list)
				self["status"].hide()
				self["key_red"].setText(language.get(lang, "27"))
				self["key_green"].setText(language.get(lang, "28"))
				self["status"].show()
				self["status"].setText(language.get(lang, "95"))
			else:
				self["status"].setText(language.get(lang, "29"))
				self["status"].show()
				self['list'].hide()
		else:
			self["status"].setText(language.get(lang, "30"))
			self["status"].show()
			self['list'].hide()

	def keyGreen(self):
		index = self['list'].getCurrent()
		message = language.get(lang, "104")
		self.session.openWithCallback(self.deleteChannel, MessageBox, message + str(index), MessageBox.TYPE_YESNO, default=False)

	def deleteChannel(self, answer):
		if answer:
			index = self['list'].getSelectionIndex()
			playlist = self.playlist['playlist']
			try:
				if self.playlist and range(len(self.channels)):
					del playlist[index]
					with open(PLAYLIST_PATH, 'w')as f:
						dump(self.playlist, f, indent=4)
				self.iniMenu()
			except Exception as err:
				print("ERROR: %s" % str(err))

	def deletelistJSON(self, answer):
		if answer:
			self.playlist['playlist'] = []
			with open(PLAYLIST_PATH, 'w') as f:
				dump(self.playlist, f, indent=4)
			self.iniMenu()
		else:
			self.iniMenu()

	def keyRed(self):
		message = language.get(lang, "7")
		if self.playlist and len(self.channels) > 0:
			self.session.openWithCallback(self.deletelistJSON, MessageBox, message, MessageBox.TYPE_YESNO, default=False)

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
	<screen name="InstallChannelsListsIPToSAT" position="center,center" size="1400,655" title="IPToSAT - Install Channels Lists">
		<widget name="list" itemHeight="40" position="18,22" size="1364,520" scrollbarMode="showOnDemand"/>
		<widget source="key_red" render="Label" objectTypes="key_red,StaticText" position="7,583" zPosition="2" size="165,52" backgroundColor="key_red" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
			<convert type="ConditionalShowHide"/>
		</widget>
		<widget source="key_green" render="Label" objectTypes="key_red,StaticText" position="183,583" zPosition="2" size="165,52" backgroundColor="key_green" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
			<convert type="ConditionalShowHide"/>
		</widget>
		<widget source="key_yellow" render="Label" objectTypes="key_yellow,StaticText" position="359,583" zPosition="2" size="165,52" backgroundColor="key_yellow" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
			<convert type="ConditionalShowHide"/>
		</widget>
		<widget source="key_blue" render="Label" objectTypes="key_blue,StaticText" position="535,583" zPosition="2" size="165,52" backgroundColor="key_blue" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text">
			<convert type="ConditionalShowHide"/>
		</widget>
		<widget name="status" position="712,560" size="684,93" font="Regular;20" horizontalAlignment="left" verticalAlignment="center" zPosition="3"/>
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
				self.folderlistchannels = join(self.path, "IPToSAT/%s/ChannelsLists" % MODEL)
				self.zip_jungle = join(self.folderlistchannels, "jungle.zip")
				self.zip_sorys_vuplusmania = join(self.folderlistchannels, "sorys_vuplusmania.zip")
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
		self["key_yellow"].setText(language.get(lang, "92"))
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
				self["status"].setText(language.get(lang, "2"))

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
				with open(CHANNELS_LISTS_PATH, 'w') as fw:
					fw.write("{" + "\n" + '	"channelslists": []' + "\n" + "}")
				# JUNGLE TEAM
				eConsoleAppContainer().execute('wget -O ' + self.zip_jungle + ' https://github.com/jungla-team/Canales-enigma2/archive/refs/heads/main.zip && wget -O ' + self.zip_sorys_vuplusmania + ' https://github.com/norhap/channelslists/archive/refs/heads/main.zip')
				sleep(10)
				if exists(str(self.zip_jungle)):
					with ZipFile(self.zip_jungle, 'r') as zipfile:
						zipfile.extractall(self.folderlistchannels)
				junglerepository = self.folderlistchannels + '/*/*Jungle-*'
				jungleupdatefile = self.folderlistchannels + '/**/*actualizacion*'
				junglelists = ""
				index = ""
				for file in glob(jungleupdatefile, recursive=True):
					with open(file, 'r') as fr:
						update = fr.readlines()
						for index in update:
							index = index.replace("[", "")
				for folders in glob(junglerepository, recursive=True):
					junglelists = str([folders.split('main/')[1], index])[1:-1].replace('\'', '').replace(',', '   ')
					indexlistssources = getChannelsLists()
					indexlistssources['channelslists'].append({'listtype': junglelists})
					with open(CHANNELS_LISTS_PATH, 'w') as f:
						dump(indexlistssources, f, indent=4)
				# SORYS VUPLUSMANIA
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
			if answer:
				if exists(BUILDBOUQUETS_SOURCE):
					remove(BUILDBOUQUETS_SOURCE)
				self.session.open(MessageBox, language.get(lang, "103"), MessageBox.TYPE_INFO, simple=True)
				eConsoleAppContainer().execute('wget -O ' + self.folderlistchannels + "/" + "IPtoSAT-main.zip"' https://github.com/norhap/IPtoSAT/archive/refs/heads/main.zip && cd ' + self.folderlistchannels + ' && unzip IPtoSAT-main.zip && rm -f ' + SOURCE_PATH + "keymap.xml" + " " + SOURCE_PATH + "icon.png" + " " + LANGUAGE_PATH + " " + VERSION_PATH + ' && cp -f ' + self.folderlistchannels + '/IPtoSAT-main/src/etc/enigma2/iptosatreferences ' + ENIGMA2_PATH + '/ && cp -f ' + self.folderlistchannels + '/IPtoSAT-main/src/IPtoSAT/* ' + SOURCE_PATH + ' && /sbin/init 4 && sleep 5 && /sbin/init 3 && sleep 35 && rm -rf ' + self.folderlistchannels + "/* " + SOURCE_PATH + '*.py')
		except Exception as err:
			self.session.open(MessageBox, "ERROR: %s" % str(err), MessageBox.TYPE_ERROR, default=False, timeout=10)

	def doInstallChannelsList(self, answer):
		channelslists = self["list"].getCurrent()
		if answer:
			self.session.open(MessageBox, language.get(lang, "77"), MessageBox.TYPE_INFO, simple=True)
			dirpath = ""
			try:
				if "Jungle-" in channelslists:
					dirpath = self.folderlistchannels + '/**/' + channelslists.split()[0] + '/etc/enigma2'
					eConsoleAppContainer().execute('wget -O ' + self.zip_jungle + ' https://github.com/jungla-team/Canales-enigma2/archive/refs/heads/main.zip && cd ' + self.folderlistchannels + ' && unzip ' + self.zip_jungle)
				if "Sorys-" in channelslists or "Vuplusmania-" in channelslists:
					dirpath = self.folderlistchannels + '/**/' + channelslists.split()[0]
					eConsoleAppContainer().execute('wget -O ' + self.zip_sorys_vuplusmania + ' https://github.com/norhap/channelslists/archive/refs/heads/main.zip && cd ' + self.folderlistchannels + ' && unzip ' + self.zip_sorys_vuplusmania)
				sleep(8)
				for dirnewlist in glob(dirpath, recursive=True):
					for files in [x for x in listdir(dirnewlist) if x.endswith("actualizacion")]:
						updatefiles = join(dirnewlist, files)
						if exists(str(updatefiles)):
							remove(updatefiles)
						for installedlist in [x for x in listdir(ENIGMA2_PATH) if "alternatives." in x or "whitelist" in x or "lamedb" in x or "satellites.xml" in x or "atsc.xml" in x or "terrestrial.xml" in x or ".radio" in x or ".tv" in x or "blacklist" in x]:
							installedfiles = join(ENIGMA2_PATH, installedlist)
							if installedfiles:
								remove(installedfiles)
					eConsoleAppContainer().execute('init 4 && sleep 10 && mv -f ' + dirnewlist + '/*.xml /etc/tuxbox/ && cp -a ' + dirnewlist + '/* /etc/enigma2/ && init 3')
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
