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
    </params>
</plugin>
"""
import Domoticz
#import socket
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
    #HostIP = None
    #HostMac = None
    #HostName = None
    atagConn = None
    countDown = 6
    
    def __init__(self):
        #self.var = 123
        return

    def onStart(self):
        DumpConfigToLog()
        
        if not (self.TARGET_TEMP_UNIT in Devices):
            Domoticz.Device(Name="TargetTemp",  Unit=self.TARGET_TEMP_UNIT, Type=242,  Subtype=1).Create()
            
        if not (self.ROOM_TEMP_UNIT in Devices):
            Domoticz.Device(Name="RoomTemp", Unit=self.ROOM_TEMP_UNIT, TypeName='Temperature').Create()
            
        self.atagConn = Domoticz.Connection(Name='AtagOneLocalConn', Transport="TCP/IP", Protocol="HTTP", Address=Parameters["Address"], Port=self.HTTP_CLIENT_PORT)
        self.atagConn.Connect()
        Domoticz.Heartbeat(10)
        Domoticz.Log("onStart called")

    def onStop(self):
        Domoticz.Log("onStop called")

    def onConnect(self, Connection, Status, Description):
        if (Status == 0):
            Domoticz.Debug("Atag One connected successfully. Requesting details")
            self.RequestDetails()
        else:
            Domoticz.Log("Failed to connect ("+str(Status)+") to: "+Parameters["Address"]+":"+str(self.HTTP_CLIENT_PORT)+" with error: "+Description)
            self.countDown = 0

    def onMessage(self, Connection, Data):
        Status = int(Data["Status"])
        newCountDown = 0
        if (Status == 200):            
            strData = Data["Data"].decode("utf-8", "ignore")
            Domoticz.Log('Atag One respons: '+strData)
            atagResponse = json.loads(strData)['retrieve_reply']
            if (int(atagResponse['acc_status']) == 2) and ('report' in atagResponse) and ('control' in atagResponse):
                report = atagResponse['report']
                control = atagResponse['control']
                if ('room_temp' in report) and ('boiler_status' in report) and ('ch_mode_temp' in control):
                    roomTemp = report['room_temp']
                    targetTemp = control['ch_mode_temp']
                    boilerStatus = int(report['boiler_status'])
                    Domoticz.Log('Atag One status retrieved: roomTemp='+str(roomTemp)+' targetTemp='+str(targetTemp)+' boilerStatus='+str(boilerStatus))
                    UpdateDevice(self.TARGET_TEMP_UNIT, int(targetTemp), str(targetTemp))
                    UpdateDevice(self.ROOM_TEMP_UNIT, int(roomTemp), str(roomTemp))
                else:
                    Domoticz.Log('Atag One /retrieve failed')
                    newCountDown = 3 # retry on next Heartbeat
            else:
                Domoticz.Log('Atag One /retrieve failed')
                newCountDown = 3 # retry on next Heartbeat
        else:
            Domoticz.Error('Atag One returned status='+Data['Status'])
        self.countDown = newCountDown
        Domoticz.Log("onMessage called")

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Log("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Log("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        Domoticz.Log("onDisconnect called")

    def onHeartbeat(self):
        self.countDown = self.countDown + 1
        if self.countDown == 6:
            if (self.atagConn == None) or (not self.atagConn.Connected()):
                Domoticz.Log('Attempting to reconnect AtagOne')
                self.atagConn = Domoticz.Connection(Name='AtagOneLocalConn', Transport="TCP/IP", Protocol="HTTP", Address=Parameters["Address"], Port=self.HTTP_CLIENT_PORT)
                self.atagConn.Connect()
            else:
                Domoticz.Log('Requesting AtagOne details')
                self.RequestDetails()

    def RequestDetails(self):
        payload = { "retrieve_message": { "seqnr":0, 
                                          "account_auth" : { "user_account": "",
                                                             "mac_address": "1a:2b:3c:4d:5e:6f" },
                                          "info": self.MESSAGE_INFO_CONTROL+self.MESSAGE_INFO_REPORT } }
        sendData = { 'Verb' : 'POST',
                     'URL'  : '/retrieve',
                     'Headers' : { 'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8', \
                                   'Connection': 'keep-alive', \
                                   'Accept': 'Content-Type: */*; charset=UTF-8', \
                                   'Host': Parameters["Address"]+":"+str(self.HTTP_CLIENT_PORT), \
                                   'User-Agent':'Domoticz/1.0' },
                     'Data' : json.dumps(payload)
                   }
        self.atagConn.Send(sendData)
      
'''        
    def GetHostInfo(self):
        if (self.HostIP == None)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                # doesn't even have to be reachable
                s.connect(('10.255.255.255', 1))
                # get host IP address and hostname
                self.HostIP = s.getsockname()[0]
                self.HostName = s.gethostname()
                # get host mac address for external IP/NIC
                interfaces = socket.if_nameindex()
                for index, ifname in interfaces:
                    ifip = socket.inet_ntoa(fcntl.ioctl(s.fileno(),
                                            0x8915,  # SIOCGIFADDR
                                            struct.pack('256s', bytes(ifname[:15], 'utf-8'))
                                            )[20:24])
                    if (ifip == self.HostIP):
                        info = fcntl.ioctl(s.fileno(), 
                                            0x8927,  
                                            struct.pack('256s',  bytes(ifname[:15], 'utf-8'))
                                            )
                        self.HostMac = ''.join(l + '-' * (n % 2 == 1) for n, l in enumerate(binascii.hexlify(info[18:24]).decode('utf-8')))[:-1]
                Domoticz.Log('Host info: IP='+self.HostIP+' Mac='+self.HostMac+' hostname='+self.HostName)
            except:
                self.HostIP = '127.0.0.1'
                self.HostName = 'localhost'
                self.HostMac = '' #unimportant because we cannot reach remote devices now anyway
                Domoticz.Error('Host info: Failed')
            finally:
                s.close()
'''

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

def UpdateDevice(Unit, nValue, sValue):
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it 
    if (Unit in Devices):
        if (Devices[Unit].nValue != nValue) or (Devices[Unit].sValue != sValue):
            Devices[Unit].Update(nValue=nValue, sValue=str(sValue))
            Domoticz.Log("Update "+str(nValue)+":'"+str(sValue)+"' ("+Devices[Unit].Name+")")
    return

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
