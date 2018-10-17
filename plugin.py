# AtagOne-Local plugin
#
# Author: MCorino
#
"""
<plugin key="AtagOneLocal" name="AtagOne Local" author="mcorino" version="1.0.0" wikilink="https://github.com/mcorino/Domoticz-AtagOne-Local" externallink="http://atag.one/">
    <description>
        <h2>AtagOne Local plugin</h2><br/>
        Provides direct local network access to an installed Atag One thermostat.
        Based on the code developed by Rob Juurlink (https://github.com/kozmoz/atag-one-api).
        Creates a thermostat setpoint sensor and a temperature sensor.
    </description>
    <params>
        <param field="Address" label="IP Address of Atag One" width="200px" required="true" default="127.0.0.1"/>
        <param field="Mode1" label="Domoticz MAC" width="600px" required="true" default="1A-2B-3C-4D-5E-6F"/>
        <param field="Mode2" label="Debug" width="75px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal"  default="True" />
            </options>
        </param>
    </params>
</plugin>
"""
import Domoticz
import socket
import json

class BasePlugin:
    MESSAGE_INFO_CONTROL = 1
    MESSAGE_INFO_SCHEDULES = 2
    MESSAGE_INFO_CONFIGURATION = 4
    MESSAGE_INFO_REPORT = 8
    MESSAGE_INFO_STATUS = 16
    MESSAGE_INFO_WIFISCAN = 32
    MESSAGE_INFO_EXTRA = 64
    HTTP_CLIENT_PORT = '10000'
    TARGET_TEMP_UNIT = 1
    ROOM_TEMP_UNIT = 2
    TEMPERATURE_MIN = 4.0
    TEMPERATURE_MAX = 27.0
    FLAME_ON_IMG = 'AtagOneLocalFlame'
    FLAME_OFF_IMG = 'AtagOneLocalNoFlame'
    hostMac = '1a-2b-3c-4d-5e-6f' # 'unique' MAC
    hostName = 'Domoticz atag-one API'
    hostAuth = True
    setLevel = False
    newLevel = None
    atagConn = None
    countDown = -1
    
    def __init__(self):
        #self.var = 123
        return

    def onStart(self):
        if Parameters["Mode2"] == 'Debug':
            Domoticz.Debugging(1)
            DumpConfigToLog()
        else:
            Domoticz.Debugging(0)
        self.hostMac = str(Parameters['Mode1'])
        if (self.FLAME_ON_IMG not in Images):
            Domoticz.Log('Loading flame ON images')
            Domoticz.Image('flame-on-icons.zip').Create()
            
        if (self.FLAME_OFF_IMG not in Images):
            Domoticz.Log('Loading flame OFF images')
            Domoticz.Image('flame-off-icons.zip').Create()

        for image in Images:
            Domoticz.Debug("Icon " + str(Images[image].ID) + " " + Images[image].Name)
            
        Domoticz.Debug('flame ON image='+str(Images[self.FLAME_ON_IMG].ID))
        Domoticz.Debug('flame OFF image='+str(Images[self.FLAME_OFF_IMG].ID))
            
        if (self.TARGET_TEMP_UNIT not in Devices):
            Domoticz.Device(Name="TargetTemp",  Unit=self.TARGET_TEMP_UNIT, Type=242,  Subtype=1, Image=Images[self.FLAME_OFF_IMG].ID).Create()
            UpdateDevice(self.TARGET_TEMP_UNIT, 0, "0.0")
            
        if (self.ROOM_TEMP_UNIT not in Devices):
            Domoticz.Device(Name="RoomTemp", Unit=self.ROOM_TEMP_UNIT, TypeName='Temperature').Create()
            UpdateDevice(self.ROOM_TEMP_UNIT, 0, "0.0")
            
        self.SetupConnection()
        Domoticz.Heartbeat(10)

    def onStop(self):
        Domoticz.Log("onStop called")

    def onConnect(self, Connection, Status, Description):
        if (Status == 0):
            Domoticz.Log("Atag One connected successfully.")
            if self.hostAuth:
                if self.setLevel:
                    Domoticz.Log("Setting AtagOne target temperature.")
                    self.UpdateTargetTemp(self.newLevel)
                else:
                    Domoticz.Log("Requesting AtagOne details.")
                    self.RequestDetails()
            else:
                Domoticz.Log("Requesting AtagOne authorization.")
                self.Authenticate()
        else:
            Domoticz.Log("Failed to connect ("+str(Status)+") to: "+Parameters["Address"]+":"+str(self.HTTP_CLIENT_PORT)+" with error: "+Description)
            self.countDown = 6

    def onMessage(self, Connection, Data):
        Status = int(Data["Status"])
        if (Status == 200):            
            strData = Data["Data"].decode("utf-8", "ignore")
            Domoticz.Debug('Atag One response: '+strData)
            atagResponse = json.loads(strData)
            if ('retrieve_reply' in atagResponse):
                self.countDown = self.ProcessDetails(atagResponse['retrieve_reply'])
                return
            
            if ('pair_reply' in atagResponse):
                self.countDown = self.ProcessAuthorization(atagResponse['pair_reply'])
                return
            
            if ('update_reply' in atagResponse):
                self.ProcessUpdate(atagResponse['update_reply'])
            else:
                Domoticz.Log('Unknown response from AtagOne')
        else:
            Domoticz.Error('Atag One returned status='+Data['Status'])
        self.countDown = 6
        Domoticz.Log("onMessage called")

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Log("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))
        if (int(Unit) == self.TARGET_TEMP_UNIT) and (int(Unit) in Devices) and (str(Command) == 'Set Level'):
            if (self.atagConn != None) and self.atagConn.Connected():
                self.atagConn.Disconnect()
            self.setLevel = True
            self.newLevel = Level
            Domoticz.Debug('Attempting to reconnect AtagOne')
            self.SetupConnection()

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Log("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        Domoticz.Log("onDisconnect called")

    def onHeartbeat(self):
        if self.countDown >= 0: self.countDown -= 1
        if self.countDown == 0:
            if (self.atagConn == None) or (not self.atagConn.Connected()):
                Domoticz.Debug('Attempting to reconnect AtagOne')
                self.SetupConnection()
            else:
                if self.hostAuth:
                    Domoticz.Log('Requesting AtagOne details')
                    self.RequestDetails()
                else:
                    Domoticz.Log("Requesting AtagOne authorization.")
                    self.Authenticate()

    def SetupConnection(self):
        self.atagConn = Domoticz.Connection(Name='AtagOneLocalConn', Transport="TCP/IP", Protocol="HTTP", Address=Parameters["Address"], Port=self.HTTP_CLIENT_PORT)
        self.atagConn.Connect()

    def RequestDetails(self):
        payload = { "retrieve_message": { "seqnr": 0, 
                                          "account_auth" : { "user_account": "",
                                                             "mac_address": self.hostMac },
                                          "info": self.MESSAGE_INFO_CONTROL+self.MESSAGE_INFO_REPORT } }
        sendData = { 'Verb' : 'POST',
                     'URL'  : '/retrieve',
                     'Headers' : { 'User-Agent': "Mozilla/5.0 (compatible; AtagOneLocalAPI/1.0.0; http://atag.one/)",
                                   'X-OneApp-Version': '1.0.0', \
                                   'Content-Type': 'application/json; UTF-8', \
                                   'Connection': 'keep-alive', \
                                   'Accept': '*/*', \
                                   'Accept-Charset': 'UTF-8', \
                                   'Host': Parameters["Address"]+":"+str(self.HTTP_CLIENT_PORT) },
                     'Data' : json.dumps(payload)
                   }
        self.atagConn.Send(sendData)
        
    def ProcessDetails(self, response):
        newCountDown = 6
        if (('acc_status' in response) and int(response['acc_status']) == 2) and ('report' in response) and ('control' in response):
            report = response['report']
            control = response['control']
            if ('room_temp' in report) and ('boiler_status' in report) and ('ch_mode_temp' in control):
                roomTemp = report['room_temp']
                targetTemp = control['ch_mode_temp']
                boilerStatus = int(report['boiler_status'])
                Domoticz.Log('Atag One status retrieved: roomTemp='+str(roomTemp)+' targetTemp='+str(targetTemp)+' boilerStatus='+str(boilerStatus))
                if ((boilerStatus & 8) == 8):
                    Domoticz.Log('Updating with flame ON')
                    UpdateDevice(self.TARGET_TEMP_UNIT, int(targetTemp), str(targetTemp), Images[self.FLAME_ON_IMG].ID)
                else:
                    Domoticz.Log('Updating with flame OFF')
                    UpdateDevice(self.TARGET_TEMP_UNIT, int(targetTemp), str(targetTemp), Images[self.FLAME_OFF_IMG].ID)
                UpdateDevice(self.ROOM_TEMP_UNIT, int(roomTemp), str(roomTemp))
            else:
                Domoticz.Log('Atag One invalid retrieve response')
        else:
            if (('acc_status' in response) and (int(response['acc_status']) == 3)):
                self.hostAuth = False
                newCountDown = 1
            else:
                if (('acc_status' in response) and (int(response['acc_status']) == 0)):
                    newCountDown = 12 # wait longer before retrying
                Domoticz.Log('Atag One missing retrieve response')
        return newCountDown
        
    def Authenticate(self):
        payload = { "pair_message": { "seqnr": 0, 
                                      "account_auth": { "user_account": "",
                                                        "mac_address": self.hostMac },
                                      "accounts": {"entries": [{"user_account": "",
                                                                "mac_address": self.hostMac,
                                                                "device_name": self.hostName,
                                                                "account_type": 0}]} } }
        sendData = { 'Verb' : 'POST',
                     'URL'  : '/retrieve',
                     'Headers' : { 'User-Agent': "Mozilla/5.0 (compatible; AtagOneLocalAPI/1.0.0; http://atag.one/)",
                                   'X-OneApp-Version': '1.0.0', \
                                   'Content-Type': 'application/json; UTF-8', \
                                   'Connection': 'keep-alive', \
                                   'Accept': '*/*', \
                                   'Accept-Charset': 'UTF-8', \
                                   'Host': Parameters["Address"]+":"+str(self.HTTP_CLIENT_PORT) },
                     'Data' : json.dumps(payload)
                   }
        self.atagConn.Send(sendData)
        
    def ProcessAuthorization(self, response):
        newCountDown = 6
        if ('acc_status' in response):
            if (int(response['acc_status']) == 2):
                self.hostAuth = True
                Domoticz.Log('AtagOne connection authorized')
            else:
                if (int(response['acc_status']) == 1):
                    newCountDown = 1                    
                    Domoticz.Log('AtagOne authorization pending')
                else:
                    if (int(response['acc_status']) == 3):
                        Domoticz.Log('AtagOne authorization denied. Retry in a minute.')
                    else:
                        Domoticz.Log('Atag One invalid pairing response: acc_status='+str(response['acc_status']))
        else:
            Domoticz.Log('Atag One invalid pairing response')
        return newCountDown
      
    def UpdateTargetTemp(self, target):
        self.setLevel = False        
        if (float(target) < self.TEMPERATURE_MIN) or (float(target) > self.TEMPERATURE_MAX):
            Domoticz.Error('Invalid temperature setting : '+str(target)+'. Should be >='+str(self.TEMPERATURE_MIN)+' and <='+str(self.TEMPERATURE_MAX))
            return
        
        Domoticz.Log('Updating target temperatur to '+str(target))
        payload = { "update_message": { "seqnr": 0, 
                                        "account_auth" : { "user_account": "",
                                                            "mac_address": self.hostMac },
                                        "control": { "ch_mode_temp": target } } }
        sendData = { 'Verb' : 'POST',
                     'URL'  : '/retrieve',
                     'Headers' : { 'User-Agent': "Mozilla/5.0 (compatible; AtagOneLocalAPI/1.0.0; http://atag.one/)",
                                   'X-OneApp-Version': '1.0.0', \
                                   'Content-Type': 'application/json; UTF-8', \
                                   'Connection': 'keep-alive', \
                                   'Accept': '*/*', \
                                   'Accept-Charset': 'UTF-8', \
                                   'Host': Parameters["Address"]+":"+str(self.HTTP_CLIENT_PORT) },
                     'Data' : json.dumps(payload)
                   }
        self.atagConn.Send(sendData)
        
    def ProcessUpdate(self, response):
        if (('acc_status' in response) and int(response['acc_status']) == 2) and ('status' in response):
            Domoticz.Log('Atag One target temperature updated')
            if (self.atagConn != None) and self.atagConn.Connected():
                self.atagConn.Disconnect()
            Domoticz.Debug('Attempting to reconnect AtagOne')
            self.SetupConnection()
        else:
            Domoticz.Log('Atag One failed update')
      
global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

def UpdateDevice(Unit, nValue, sValue, Image=None):
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it 
    if (Unit in Devices):
        if (Devices[Unit].nValue != nValue) or (Devices[Unit].sValue != sValue) or ((Image != None) and (Image != Devices[Unit].Image)):
            if (Image != None) and (Image != Devices[Unit].Image):
                Devices[Unit].Update(nValue=nValue, sValue=str(sValue), Image=Image)
                Domoticz.Log("Update "+str(nValue)+":'"+str(sValue)+"' ("+Devices[Unit].Name+") Image="+str(Image))
            else:
                Devices[Unit].Update(nValue=nValue, sValue=str(sValue))
                Domoticz.Log("Update "+str(nValue)+":'"+str(sValue)+"' ("+Devices[Unit].Name+")")

    # Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return
