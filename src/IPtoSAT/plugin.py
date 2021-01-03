from Screens.Screen import Screen
from Plugins.Plugin import PluginDescriptor
from Components.ActionMap import ActionMap
from Components.ServiceEventTracker import ServiceEventTracker
from Components.config import config, ConfigInteger, getConfigListEntry, ConfigSelection, ConfigYesNo, ConfigSubsection
from Components.ConfigList import ConfigList, ConfigListScreen
from Components.MenuList import MenuList
from enigma import iPlayableService, iServiceInformation, eServiceCenter, eServiceReference, iFrontendInformation, eTimer
from Components.Label import Label
from ServiceReference import ServiceReference
from Screens.MessageBox import MessageBox
from Components.Sources.StaticText import StaticText
from enigma import eConsoleAppContainer
from Tools.Directories import fileExists

config.plugins.IPToSAT = ConfigSubsection()
config.plugins.IPToSAT.enable = ConfigYesNo(default=False)


def trace_error():
    import sys
    import traceback
    try:
        traceback.print_exc(file=sys.stdout)
        traceback.print_exc(file=open('/tmp/IPtoSAT.log', 'a'))
    except:
        pass


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


REDC = '\033[31m'
ENDC = '\033[m'


def cprint(text):
    print(REDC+text+ENDC)


class IPToSATSetup(Screen, ConfigListScreen):
    skin = """
		<screen name="IPToSATSetup" position="center,center" size="650,460" title="IPToSATSetup settings">
		<widget position="15,10" size="620,300" name="config" scrollbarMode="showOnDemand" />
			<ePixmap position="100,418" zPosition="1" size="165,2" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/IPtoSAT/icons/red.png" alphatest="blend" />
		<widget source="red_key" render="Label" position="100,388" zPosition="2" size="165,30" font="Regular; 20" halign="center" valign="center" transparent="1" />
		<ePixmap position="385,418" zPosition="1" size="165,2" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/IPtoSAT/icons/green.png" alphatest="blend" />
		<widget source="green_key" render="Label" position="385,388" zPosition="2" size="165,30" font="Regular; 20" halign="center" valign="center" transparent="1" />
		</screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self.skinName = ["IPToSATSetup"]
        self.setup_title = _("IPToSAT BY ZIKO V %s" % Ver)

        self.onChangedEntry = []
        self.list = []
        ConfigListScreen.__init__(
            self, self.list, session=session, on_change=self.changedEntry)

        self["actions"] = ActionMap(["SetupActions"],
                                    {
            "cancel": self.keyCancel,
            "save":   self.apply,
            "ok":     self.apply
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

        self["config"].list = self.list
        self["config"].setList(self.list)

    def apply(self):
        for x in self["config"].list:
            x[1].save()
        self.close()

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
            iPlayableService.evStopped: self.__evEnd
        })
        self.Timer = eTimer()
        self.Timer.callback.append(self.get_channel)
        self.container = eConsoleAppContainer()
        self.ip_sat = False

    def __evStart(self):
        self.Timer.start(2000)
        

    def readJs(self):
        import json
        if fileExists('/etc/enigma2/iptosat.json'):
            with open('/etc/enigma2/iptosat.json', 'r')as f:
                try:
                    return json.loads(f.read())
                except ValueError:
                    trace_error()
        else:
            return None

    def current_channel(self, channel):
        playlist = self.readJs()
        if channel and playlist:
            for ch in playlist['playlist']:
                if channel == ch['channel']:
                    self.ip_sat = True
                    cmd = 'exteplayer3 {}'.format(ch['url'])
                    self.container.execute(cmd)
                    

    def get_channel(self):
        service = self.session.nav.getCurrentService()
        if service:
            info = service and service.info()
            if info:
                FeInfo = service and service.frontendInfo()
                if FeInfo:
                    isCrypted = info and info.getInfo(iServiceInformation.sIsCrypted)
                    if isCrypted:
                        SNR = FeInfo.getFrontendInfo(iFrontendInformation.signalQuality) / 655
                        if SNR > 10 and not self.container.running():
                            channel_name = ServiceReference(self.session.nav.getCurrentlyPlayingServiceReference()).getServiceName()
                            self.current_channel(channel_name)
                        elif self.container.running() and SNR <= 10:
                            self.container.kill()
                            self.ip_sat = False
                            
    def __evEnd(self):
        self.Timer.stop()
        if self.ip_sat:
            self.container.kill()
        self.ip_sat = False


def autostart(reason, **kwargs):
    if config.plugins.IPToSAT.enable.value:
        session = kwargs["session"]
        IPtoSAT(session)


def iptosatSetup(session, **kwargs):
    autostart(reason=0, session=session)
    session.open(IPToSATSetup)


def Plugins(**kwargs):
    Descriptors = []
    Descriptors.append(PluginDescriptor(where=[PluginDescriptor.WHERE_SESSIONSTART], fnc=autostart))
    Descriptors.append(PluginDescriptor(name="IPtoSAT", description="IPtoSAT", icon="icon.png",where=PluginDescriptor.WHERE_PLUGINMENU, fnc=iptosatSetup))
    return Descriptors