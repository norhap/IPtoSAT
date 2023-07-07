from Screens.ChannelSelection import ChannelSelectionBase
from Components.ServiceList import ServiceList
from Screens.Screen import Screen
from Plugins.Plugin import PluginDescriptor
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.ServiceEventTracker import ServiceEventTracker
from Components.config import config, ConfigInteger, getConfigListEntry, ConfigSelection, ConfigYesNo, ConfigSubsection
from Components.ConfigList import ConfigList, ConfigListScreen
from Components.MenuList import MenuList
from enigma import iPlayableService, iServiceInformation, eServiceCenter, eServiceReference, iFrontendInformation, eTimer , gRGB , eConsoleAppContainer , gFont
from Components.Label import Label
from ServiceReference import ServiceReference
from Screens.MessageBox import MessageBox
from Screens.Standby import TryQuitMainloop
from Components.Sources.StaticText import StaticText
from Components.Console import Console
from Tools.Directories import fileContains, fileExists, isPluginInstalled
from Tools.BoundFunction import boundFunction
from twisted.web.client import getPage, downloadPage
from datetime import datetime
import json
from os.path import join
from os import listdir
from shutil import move
from configparser import ConfigParser
try:
	from Components.Language import language
	lang = language.getLanguage()
	lang = lang[:2]
except:
	try:
		lang = config.osd.language.value[:-3]
	except:
		lang = "en"

language_path = r"/usr/lib/enigma2/python/Plugins/Extensions/IPtoSAT/languages"

try:
	language = ConfigParser()
	language.read(language_path, encoding="utf8")
except:
	try:
		lang="en"
		language = ConfigParser()
		language.read(language_path, encoding="utf8")
	except:
		pass



def choices_list():
	if fileExists('/var/lib/dpkg/status'):
		# Fixed DreamOS by. audi06_19 , gst-play-1.0
		return [("gst-play-1.0", _("OE-2.5 Player")),("exteplayer3", _("Exteplayer3")),]
	elif isPluginInstalled("FastChannelChange"):
		return [("gstplayer", _("GstPlayer"))]
	else:
		return [("gstplayer", _("GstPlayer")),("exteplayer3", _("Exteplayer3")),]

default_player = "gstplayer" if not fileExists('/var/lib/dpkg/status') or isPluginInstalled("FastChannelChange") else "gst-play-1.0"
config.plugins.IPToSAT = ConfigSubsection()
config.plugins.IPToSAT.enable = ConfigYesNo(default=False)
config.plugins.IPToSAT.player = ConfigSelection(default=default_player, choices=choices_list())
config.plugins.IPToSAT.assign = ConfigSelection(choices = [("1", _("Press OK"))], default = "1")
config.plugins.IPToSAT.playlist = ConfigSelection(choices = [("1", _("Press OK"))], default = "1")

PLAYLIST_PATH = '/etc/enigma2/iptosat.json'

def trace_error():
	import sys
	import traceback
	try:
		traceback.print_exc(file=sys.stdout)
		traceback.print_exc(file=open('/tmp/IPtoSAT.log', 'a'))
	except:
		pass

def log(data):
	now = datetime.now().strftime('%Y-%m-%d %H:%M')
	open('/tmp/IPtoSAT.log', 'a').write(now + ' : ' + str(data) + '\r\n')

def getversioninfo():
	import os
	currversion = '1.0'
	version_file = '/usr/lib/enigma2/python/Plugins/Extensions/IPtoSAT/version'
	if os.path.exists(version_file):
		try:
			fp = open(version_file, 'r').readlines()
			for line in fp:
				if 'version' in line:
					currversion = line.split('=')[1].strip()
		except:
			pass
	return (currversion)


Ver = getversioninfo()


def parseColor(s):
	return gRGB(int(s[1:], 0x10))


def getPlaylist():
	if fileExists(PLAYLIST_PATH):
		with open(PLAYLIST_PATH, 'r') as f:
			try:
				return json.loads(f.read())
			except ValueError:
				trace_error()
	else:
		return None

class IPToSATSetup(Screen, ConfigListScreen):

	skin = """
		<screen name="IPToSATSetup" position="center,center" size="650,300" title="IPToSATSetup settings">
			<widget position="15,10" size="620,300" name="config" scrollbarMode="showOnDemand" />
			<ePixmap position="100,290" zPosition="1" size="100,2" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/IPtoSAT/icons/red.png" alphaTest="blend" />
			<widget name="key_red" position="65,260" zPosition="2" size="165,30" font="Regular; 20" horizontalAlignment="center" verticalAlignment="center" transparent="1" />
			<ePixmap position="480,290" zPosition="1" size="100,2" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/IPtoSAT/icons/green.png" alphaTest="blend" />
			<widget name="key_green" position="450,260" zPosition="2" size="165,30" font="Regular; 20" horizontalAlignment="center" verticalAlignment="center" transparent="1" />
			<widget name="HelpWindow" position="0,0" size="0,0" alphaTest="blend" conditional="HelpWindow" transparent="1" zPosition="+1" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = ["IPToSATSetup"]
		self.setup_title = _(language.get(lang, "IPToSAT BY ZIKO") + " " + "Version %s" % Ver)
		self.onChangedEntry = []
		self.list = []
		ConfigListScreen.__init__(self, self.list, session=session, on_change=self.changedEntry)
		self["actions"] = ActionMap(["IPtoSATActions"],
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
		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("Save"))
		self.createSetup()
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_(language.get(lang, "IPToSAT BY ZIKO") + " " + "Version %s" % Ver))

	def createSetup(self):
		self.list = [getConfigListEntry(_(language.get(lang, "Enable IPToSAT")), config.plugins.IPToSAT.enable)]
		self.list.append(getConfigListEntry(_(language.get(lang, "IPToSAT Player")), config.plugins.IPToSAT.player))
		self.list.append(getConfigListEntry(_(language.get(lang, "Assign satellite channel to IPTV list")), config.plugins.IPToSAT.assign))
		self.list.append(getConfigListEntry(_(language.get(lang, "Reset or Remove channels from playlist")), config.plugins.IPToSAT.playlist))
		self["config"].list = self.list
		self["config"].setList(self.list)
		if isPluginInstalled("FastChannelChange") and fileContains(PLAYLIST_PATH, '"sref": "') and config.plugins.IPToSAT.enable.value:
			if not config.plugins.fccsetup.activate.value:
				config.plugins.fccsetup.activate.value = True
				config.plugins.fccsetup.activate.save()
				self.session.open(TryQuitMainloop, 3)

	def ok(self):
		current = self["config"].getCurrent()
		if current[1] == config.plugins.IPToSAT.assign:
			self.session.open(AssignService)
		elif current[1] == config.plugins.IPToSAT.playlist:
			self.session.open(EditPlaylist)

	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def keySave(self):
		ConfigListScreen.keySave(self)
		if config.plugins.IPToSAT.enable.value and fileContains(PLAYLIST_PATH, '"sref": "'):
			self.session.open(TryQuitMainloop, 3)

	def moveUp(self):
		self["config"].moveUp()

	def moveDown(self):
		self["config"].moveDown()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)

	def keyRight(self):
		ConfigListScreen.keyRight(self)


class IPtoSAT(Screen):

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

	skin = """<screen name="IPToSAT Service Assign" position="center,center" size="1351,602" title="IPToSAT Service Assign">
				<widget position="18,22" size="620,310" name="list" scrollbarMode="showOnDemand" />
				<widget position="701,22" size="620,300" name="list2" scrollbarMode="showOnDemand" />
				<widget name="status" position="850,150" size="250,28" font="Regular;24" zPosition="3"/>
				<widget name="assign" position="15,359" size="1200,30" font="Regular;24" zPosition="3"/>
				<widget name="key_green" position="7,544" zPosition="2" size="165,30" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" transparent="1"/>
				<ePixmap position="18,580" zPosition="1" size="165,2" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/IPtoSAT/icons/green.png" alphaTest="blend"/>
				<widget name="key_blue" position="215,544" zPosition="2" size="165,30" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" transparent="1"/>
				<widget name="key_red" position="423,524" zPosition="2" size="165,50" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" transparent="1"/>
				<ePixmap position="230,580" zPosition="1" size="165,2" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/IPtoSAT/icons/blue.png" alphaTest="blend"/>
				<ePixmap position="438,580" zPosition="1" size="165,2" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/IPtoSAT/icons/red.png" alphaTest="blend"/>
				<widget name="description" position="633,390" size="710,210" font="Regular;24" zPosition="3"/>
				<widget name="HelpWindow" position="0,0" size="0,0" alphaTest="blend" conditional="HelpWindow" transparent="1" zPosition="+1" />
			</screen>"""

	def __init__(self, session, *args):
		self.session = session
		ChannelSelectionBase.__init__(self, session)
		self.bouquet_mark_edit = 0
		self["status"] = Label()
		self["assign"] = Label()
		description = _(language.get(lang, "0"))
		self["description"] = Label(description)
		self["key_green"] = Button(_("Satellites"))
		self["key_red"] = Button(_(language.get(lang, "Add EPG IPTV Channel")))
		self["key_yellow"] = StaticText("")
		self["key_blue"] = Button(_("Favourites"))
		self["ChannelSelectBaseActions"] = ActionMap(["IPtoSATAsignActions"],
		{
			"cancel": self.exit,
			"back": self.exit,
			"ok": self.channelSelected,
			"left": self.left,
			"right": self.right,
			"down": self.moveDown,
			"up": self.moveUp,
			"green": self.showSatellites,
			"red": self.setEPGChannel,
			"blue": self.showFavourites,
			"nextBouquet": self.chUP,
			"prevBouquet": self.chDOWN,

		}, -2)
		self.errortimer = eTimer()
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

	def onWindowShow(self):
		self.onShown.remove(self.onWindowShow)
		try:
			self.disablelist2()
		except:pass

	def setModeTv(self):
		self.setTvMode()
		self.showFavourites()
		self.buildTitleString()

	def buildTitleString(self):
		titleStr = self.getTitle().replace('IPtoSAT - ','')
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
				self.setTitle('IPtoSAT - ' + titleStr)

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
		if fileExists('/etc/enigma2/iptosat.conf'):
			xtream = open('/etc/enigma2/iptosat.conf').read()
			try:
				self.host = xtream.split()[1].split('Host=')[1]
				self.user = xtream.split()[2].split('User=')[1]
				self.password = xtream.split()[3].split('Pass=')[1]
				self.url = '{}/player_api.php?username={}&password={}'.format(self.host,self.user,self.password)
				self.getCategories(self.url)
			except:
				trace_error()
				self.errortimer.start(200, True)
		else:
			log('/etc/enigma2/iptosat.conf , No such file or directory')
			self.close(True)

	def errorMessage(self):
		self.session.openWithCallback(self.exit, MessageBox, _(language.get(lang, "Something is wrong in /etc/iptosat.conf. Log in /tmp/IPtoSAT.log")), MessageBox.TYPE_ERROR, timeout=10)

	def getCategories(self,url):
		url += '&action=get_live_categories'
		self.callAPI(url,self.getData)

	def channelSelected(self):
		if self.selectedList == self["list"]:
			ref = self.getCurrentSelection()
			if (ref.flags & 7) == 7:
				self.enterPath(ref)
				self.in_bouquets = True
		elif self.selectedList == self["list2"]:
			if self.url and self.in_channels == False and len(self.categories) > 0:
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
				self.addChannel(channel_name,stream_id,sref,xtream_channel)

	def addChannel(self,channel_name,stream_id,sref,xtream_channel):
		playlist = getPlaylist()
		if playlist:
			if sref.startswith('1') and not 'http' in sref:
				url = self.host + '/' + self.user + '/' + self.password + '/' + stream_id
				if not fileContains(PLAYLIST_PATH, sref):
					from unicodedata import normalize
					playlist['playlist'].append({'sref':sref,'channel':normalize('NFKD', channel_name).encode('ascii', 'ignore').decode() ,'url':url})
					with open(PLAYLIST_PATH, 'w') as f:
						json.dump(playlist, f, indent = 4)
					text = channel_name + " " + _(language.get(lang, "correctly assigned with")) + " " + xtream_channel
					self.assignWidget("#008000",text)
				else:
					text = channel_name + " " + _(language.get(lang, "this channel already exists in the list"))
					self.assignWidget("#00ff2525",text)
			else:
				text = _(language.get(lang, "Cannot assign to this channel"))
				self.assignWidget("#00ff2525",text)
		else:
			text = _(language.get(lang, "Failed to load Playlist"))
			self.assignWidget("#00ff2525",text)

	def restarGUI(self, answer):
		if answer:
			self.session.open(TryQuitMainloop, 3)
		else:
			self.channelSelected()

	def setEPGChannel(self):
		sref = str(self.getSref())
		channel_name = str(ServiceReference(sref).getServiceName())
		self.addEPGChannel(channel_name, sref)

	def addEPGChannel(self, channel_name, sref):
		for filelist in sorted([x for x in listdir("/etc/enigma2") if "userbouquet." in x and ".tv" in x]):
			bouquetiptv = join(filelist)
			if fileContains("/etc/enigma2/" + bouquetiptv, channel_name) and fileContains("/etc/enigma2/" + bouquetiptv, str(self.password)) and not fileContains("/etc/enigma2/" + bouquetiptv, sref):
				with open("/etc/enigma2/" + bouquetiptv, "r") as fr:
					lines = fr.readlines()
					with open("/etc/enigma2/" + "iptv_bouquet_epg.txt", "w") as fw:
						for line in lines:
							if channel_name not in line:
								fw.write(line)
				with open("/etc/enigma2/" + bouquetiptv, "r") as file:
					replacement = ""
					for line in file:
						line = line.strip()
						if "4097" in line or "5001" in line or "5002" in line:
							ref = line[9:31]
						else:
							ref = line[9:28]
						if channel_name in line and self.password in line:
							reference_epg = line.replace(ref, self.getSref()).replace("::", ":").replace("0:" + channel_name, "0")
							replacement = replacement + reference_epg
				with open("/etc/enigma2/" + "iptv_bouquet_epg.txt", "a") as fr:
					fr.write("#" + "\n" + replacement)
				move("/etc/enigma2/iptv_bouquet_epg.txt", "/etc/enigma2/" + bouquetiptv)
				if not fileContains("/etc/enigma2/" + bouquetiptv, ":" + channel_name):
					text = channel_name + " " + _(language.get(lang, "No EPG, check channel name"))
					self.assignWidget("#00ff2525",text)
				else:
					text = channel_name + " " + _(language.get(lang, "with EPG set"))
					self.assignWidget("#008000",text)
					message = _(language.get(lang, "1"))
					self.session.openWithCallback(self.restarGUI, MessageBox, str(channel_name) + " " + message, MessageBox.TYPE_YESNO, default=False)

	def exists(self,sref,playlist):
		try:
			refs = [ref['sref'] for ref in playlist['playlist']]
			return False if not sref in refs else True
		except KeyError:
			pass

	def assignWidget(self,color,text):
		self['assign'].setText(text)
		self['assign'].instance.setForegroundColor(parseColor(color))

	def resetWidget(self):
		self['assign'].setText('')

	def getSref(self):
		ref = self.getCurrentSelection()
		return ref.toString()

	def callAPI(self, url, callback):
		self['list2'].hide()
		self["status"].show()
		self["status"].setText(_(language.get(lang, "Please wait...")))
		getPage(str.encode(url)).addCallback(callback).addErrback(self.error)

	def error(self, error=None):
		if error:
			log(error)
			self['list2'].hide()
			self["status"].show()
			self["status"].setText('Error!!')
			self.session.openWithCallback(self.exit, MessageBox, _(language.get(lang, "An Unexpected HTTP Error Occurred During The API Request !!")), MessageBox.TYPE_ERROR, timeout=10)

	def getData(self, data):
		list = []
		js = json.loads(data)
		if js != []:
			for cat in js:
				list.append((str(cat['category_name']),
							 str(cat['category_id'])))
		self["status"].hide()
		self['list2'].show()
		self['list2'].l.setList(list)
		self.categories = list
		self.in_channels = False

	def getChannels(self, data):
		sref = str(self.getSref())
		channel_satellite = str(ServiceReference(sref).getServiceName())
		search_name = channel_satellite[2:6]  # criteria 5 bytes to search for matches
		list = []
		js = json.loads(data)
		if js != []:
			for ch in js:
				if str(search_name) in str(ch['name']):
					list.append((str(ch['name']), str(ch['stream_id'])))
			if list == []:
				for match in js:
					if str(search_name) in str(match['epg_channel_id']):
						list.append((str(match['name']), str(match['stream_id'])))
			if list == []:
				for match in js:
					search_name = channel_satellite[2:5].lower()
					if str(search_name) in str(match['name']):
						list.append((str(match['name']), str(match['stream_id'])))
			if list == []:
				for match in js:
					search_name = channel_satellite[1:4]
					if str(search_name) in str(match['name']):
						list.append((str(match['name']), str(match['stream_id'])))
			if list == []:
				for match in js:
					list.append((str(match['name']), str(match['stream_id'])))
				text = channel_satellite + " " + _(language.get(lang, "2"))
				self.assignWidget("#00e5b243",text)
		self["status"].hide()
		self['list2'].show()
		self['list2'].l.setList(list)
		self["list2"].moveToIndex(0)
		self.channels = list
		self.in_channels = True

	def exit(self,ret=None):
		if ret:
			self.close(True)
		if self.selectedList == self['list'] and self.in_bouquets:
			ref = self.getCurrentSelection()
			self.showFavourites()
			self.in_bouquets = False
		elif self.selectedList == self["list2"] and self.in_channels:
			self.getCategories(self.url)
		else:
			self.close(True)

class EditPlaylist(Screen):

	skin = """<screen name="EditPlaylistIPtoSAT" position="center,center" size="600,450" title="IPToSAT - Edit Playlist">
				<widget name="list" position="18,22" size="565,350" scrollbarMode="showOnDemand"/>
				<widget source="key_red" render="Label" objectTypes="key_red,StaticText" position="7,405" zPosition="2" size="165,50" backgroundColor="key_red" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text" />
				<widget source="key_green" render="Label" objectTypes="key_red,StaticText" position="222,405" zPosition="2" size="165,50" backgroundColor="key_green" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" foregroundColor="key_text" />
				<widget name="status" position="175,185" size="250,28" font="Regular;24" zPosition="3"/>
				<widget name="HelpWindow" position="0,0" size="0,0" alphaTest="blend" conditional="HelpWindow" transparent="1" zPosition="+1" />
			</screen>"""

	def __init__(self, session , *args):
		self.session = session
		Screen.__init__(self, session)
		self["status"] = Label()
		self.skinName = ["EditPlaylistIPtoSAT"]
		self.setTitle(_(language.get(lang, "Edit channel list")))
		self['list'] = MenuList([])
		self["key_red"] = StaticText("")
		self["key_green"] = StaticText("")
		self["IptosatActions"] = ActionMap(["IPtoSATActions"],
		{
			"back": self.close,
			"cancel": self.exit,
			"red": self.keyRed,
			"green":self.keyGreen,

		}, -2)
		self.channels = []
		self.playlist = getPlaylist()
		self.iniMenu()

	def iniMenu(self):
		if self.playlist:
			list = []
			for channel in self.playlist['playlist']:
				try:
					list.append(str(channel['channel']))
				except KeyError:pass
			if len(list) > 0:
				self['list'].l.setList(list)
				self.channels = sorted(list)
				self["status"].hide()
				self["key_red"].setText(_(language.get(lang, "Delete list")))
				self["key_green"].setText(_(language.get(lang, "Delete Channel")))
			else:
				self["status"].setText(_(language.get(lang, "No channel list")))
				self["status"].show()
				self['list'].hide()
		else:
			self["status"].setText(_(language.get(lang, "Failed to read list")))
			self["status"].show()
			self['list'].hide()

	def keyGreen(self):
		if self.playlist and len(self.channels) > 0:
			index = self['list'].getSelectionIndex()
			playlist = self.playlist['playlist']
			del playlist[index]
			self.playlist['playlist'] = playlist
			with open(PLAYLIST_PATH, 'w') as f:
				json.dump(self.playlist, f , indent = 4)
		self.iniMenu()

	def keyRed(self):
		if self.playlist and len(self.channels) > 0:
			self.playlist['playlist'] = []
			with open(PLAYLIST_PATH, 'w') as f:
				json.dump(self.playlist, f , indent = 4)
		self.iniMenu()

	def exit(self,ret=None):
		self.close(True)

def autostart(reason, **kwargs):
	if reason == 0:
		if config.plugins.IPToSAT.enable.value:
			if fileExists('/usr/bin/{}'.format(config.plugins.IPToSAT.player.value)):
				IPtoSAT(kwargs["session"])
			else:
				log("Cannot start IPtoSat, {} not found".format(config.plugins.IPToSAT.player.value))


def iptosatSetup(session, **kwargs):
	session.open(IPToSATSetup)


def Plugins(**kwargs):
	Descriptors = []
	Descriptors.append(PluginDescriptor(where=[PluginDescriptor.WHERE_SESSIONSTART], fnc=autostart))
	Descriptors.append(PluginDescriptor(name="IPtoSAT", description="IPtoSAT Setup {}".format(Ver), icon="icon.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=iptosatSetup))
	return Descriptors
