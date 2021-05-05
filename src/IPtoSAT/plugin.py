from Screens.ChannelSelection import ChannelSelectionBase
from Components.ServiceList import ServiceList
from Screens.Screen import Screen
from Plugins.Plugin import PluginDescriptor
from Components.ActionMap import ActionMap
from Components.ServiceEventTracker import ServiceEventTracker
from Components.config import config, ConfigInteger, getConfigListEntry, ConfigSelection, ConfigYesNo, ConfigSubsection
from Components.ConfigList import ConfigList, ConfigListScreen
from Components.MenuList import MenuList
from enigma import iPlayableService, iServiceInformation, eServiceCenter, eServiceReference, iFrontendInformation, eTimer , gRGB , eConsoleAppContainer
from Components.Label import Label
from ServiceReference import ServiceReference
from Screens.MessageBox import MessageBox
from Components.Sources.StaticText import StaticText
from Tools.Directories import fileExists
from twisted.web.client import getPage, downloadPage
from datetime import datetime
import json

config.plugins.IPToSAT = ConfigSubsection()
config.plugins.IPToSAT.enable = ConfigYesNo(default=False)
config.plugins.IPToSAT.player = ConfigSelection(default="gstplayer", choices=[
	("gstplayer", _("GstPlayer")),
	("exteplayer3", _("Exteplayer3")),
])
config.plugins.IPToSAT.assign = ConfigSelection(choices = [("1", _("Press OK"))], default = "1")

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
	open('/tmp/IPtoSAT.log', 'a').write(now+' : '+str(data)+'\r\n')

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

def parseColor(s):
	return gRGB(int(s[1:], 0x10))

Ver = getversioninfo()


REDC = '\033[31m'
ENDC = '\033[m'


def cprint(text):
	print(REDC+text+ENDC)

def getPlaylist():
	import json
	if fileExists(PLAYLIST_PATH):
		with open(PLAYLIST_PATH, 'r')as f:
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
			<ePixmap position="100,290" zPosition="1" size="100,2" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/IPtoSAT/icons/red.png" alphatest="blend" />
			<widget source="red_key" render="Label" position="65,260" zPosition="2" size="165,30" font="Regular; 20" halign="center" valign="center" transparent="1" />
			<ePixmap position="480,290" zPosition="1" size="100,2" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/IPtoSAT/icons/green.png" alphatest="blend" />
			<widget source="green_key" render="Label" position="450,260" zPosition="2" size="165,30" font="Regular; 20" halign="center" valign="center" transparent="1" />
        </screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = ["IPToSATSetup"]
		self.setup_title = _("IPToSAT BY ZIKO V %s" % Ver)

		self.onChangedEntry = []
		self.list = []
		ConfigListScreen.__init__(self, self.list, session=session, on_change=self.changedEntry)

		self["actions"] = ActionMap(["IPtoSATActions"],
		{
			"cancel": self.keyCancel,
			"save": self.apply,
			"ok": self.apply,
		}, -2)
		self["green_key"] = StaticText(_("Save"))
		self["red_key"] = StaticText(_("Cancel"))
		self.createSetup()
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_("IPToSAT BY ZIKO V %s" % Ver))

	def createSetup(self):
		self.list = [getConfigListEntry(
			_("Enable IPToSAT"), config.plugins.IPToSAT.enable)]
		self.list.append(getConfigListEntry(_("IPToSAT Player"), config.plugins.IPToSAT.player))
		self.list.append(getConfigListEntry(_("Assign service to IPTV Link"), config.plugins.IPToSAT.assign))

		self["config"].list = self.list
		self["config"].setList(self.list)

	def apply(self):
		for x in self["config"].list:
			if x[1] == config.plugins.IPToSAT.assign:
				self.session.open(AssignService)
			x[1].save()

	def changedEntry(self):
		for x in self.onChangedEntry:
			x()


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
					SNR = FeInfo.getFrontendInfo(
						iFrontendInformation.signalQuality) / 655
					isCrypted = info and info.getInfo(
						iServiceInformation.sIsCrypted)
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

	skin = """<screen name="IPToSAT Service Assign" position="center,center" size="1351,400" title="IPToSAT Service Assign">
				<widget position="18,22" size="620,310" name="list" scrollbarMode="showOnDemand" />
				<widget position="701,22" size="620,300" name="list2" scrollbarMode="showOnDemand" />
				<widget name="status" position="850,150" size="724,28" font="Regular;24" zPosition="3"/>
				<widget name="assign" position="15,359" size="724,28" font="Regular;24" zPosition="3"/>
			</screen>"""

	def __init__(self, session, *args):
		self.session = session
		ChannelSelectionBase.__init__(self, session)
		self["status"] = Label()
		self["assign"] = Label()
		self["ChannelSelectBaseActions"] = ActionMap(["IPtoSATActions"],
		{
			"cancel": self.exit,
			"ok": self.channelSelected,
			"left": self.left,
			"right": self.right,
			"down": self.moveDown,
			"up": self.moveUp,

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
				self.setTitle('IPtoSAT - '+titleStr)

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
		self.session.openWithCallback(self.exit, MessageBox, _('Something is wrong in /etc/iptosat.conf\nFull log in /tmp/IPtoSAT.log'), MessageBox.TYPE_ERROR, timeout=10)

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
			if self.url and self.in_channels == False and len(self.categories)>0:
				index = self['list2'].getSelectionIndex()
				cat_id = self.categories[index][1]
				url = self.url
				url += '&action=get_live_streams&category_id='+cat_id
				self.callAPI(url, self.getChannels)
			elif self.in_channels and len(self.channels)>0:
				index = self['list2'].getSelectionIndex()
				xtream_channel = self.channels[index][0]
				stream_id = self.channels[index][1]
				sref = self.getSref()
				channel_name = ServiceReference(sref).getServiceName()
				self.addChannel(channel_name,stream_id,sref,xtream_channel)

	def addChannel(self,channel_name,stream_id,sref,xtream_channel):
		playlist = getPlaylist()
		if playlist:
			if sref.startswith('1') and sref.endswith(':'):
				url = self.host+'/'+self.user+'/'+self.password+'/'+stream_id
				if not self.exists(sref,playlist):
					playlist['playlist'].append({'sref':sref,'channel':channel_name ,'url':url})
					with open(PLAYLIST_PATH, 'w')as f:
						json.dump(playlist, f, indent = 4 , sort_keys = False)
					text = channel_name+' mapped successfully with '+xtream_channel
					self.assignWidget("#008000",text)
				else:
					text = channel_name+' already exist in playlist'
					self.assignWidget("#00ff2525",text)
			else:
				text = "Cannot assign channel to this service"
				self.assignWidget("#00ff2525",text)
		else:
			text = "Failed to load Playlist"
			self.assignWidget("#00ff2525",text)

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
		self["status"].setText('Please wait ...')
		getPage(str.encode(url)).addCallback(callback).addErrback(self.error)

	def error(self, error=None):
		if error:
			log(error)
			self['list2'].hide()
			self["status"].show()
			self["status"].setText('Error!!')
			self.session.openWithCallback(self.exit, MessageBox, _('An Unexpected HTTP Error Occurred During The API Request !!'), MessageBox.TYPE_ERROR, timeout=10)

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
		list = []
		js = json.loads(data)
		if js != []:
			for ch in js:
				list.append((str(ch['name']),str(ch['stream_id'])))
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


def autostart(reason, **kwargs):
	if reason == 0:
		if config.plugins.IPToSAT.enable.value:
			session = kwargs["session"]
			if fileExists('/var/lib/dpkg/status'):
				if fileExists('/usr/bin/exteplayer3'):
					IPtoSAT(session)
				else:
					log("Cannot start IPtoSat, exteplayer3 not found")
			else:
				if fileExists('/usr/bin/{}'.format(config.plugins.IPToSAT.player.value)):
					IPtoSAT(session)
				else:
					log("Cannot start IPtoSat, {} not found".format(config.plugins.IPToSAT.player.value))


def iptosatSetup(session, **kwargs):
	session.open(IPToSATSetup)


def Plugins(**kwargs):
	Descriptors = []
	Descriptors.append(PluginDescriptor(where=[PluginDescriptor.WHERE_SESSIONSTART], fnc=autostart))
	Descriptors.append(PluginDescriptor(name="IPtoSAT", description="IPtoSAT Setup {}".format(Ver), icon="icon.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=iptosatSetup))
	return Descriptors
