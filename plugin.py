# AtagOne-Local plugin
#
# Author: MCorino
#
"""
<plugin key="AtagOneLocal" name="AtagOne Local plugin" author="mcorino" version="1.0.0" wikilink="http://www.domoticz.com/wiki/plugins/AtagOneLocal.html" externallink="https://github.com/mcorino/Domoticz-AtagOne-Local">
    <description>
        <h2>AtagOne Local plugin</h2><br/>
        Provides direct local network access to an installed Atag One thermostat.
        Based on the code developed by Rob Juurlink (https://github.com/kozmoz/atag-one-api).
        Creates a thermostat setpoint sensor and a thermostat temperature sensor.
    </description>
    <params>
        <param field="Address" label="IP Address of Atag One" width="200px" required="true" default="127.0.0.1"/>
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
    HTTP_CLIENT_PORT = 10000
    #HostIP = None
    #HostMac = None
    #HostName = None
    atagConn = None
    countDown = 3
    
    def __init__(self):
        #self.var = 123
        return

    def onStart(self):
        DumpConfigToLog()
        Domoticz.Heartbeat(10)
        
        if (len(Devices) == 0):
            Domoticz.Device(Name="TargetTemp",  Unit=1, Type=242,  Subtype=1).Create()
            Domoticz.Device(Name="RoomTemp",  Unit=2, Type=242,  Subtype=2).Create()
            
        self.atagConn = Domoticz.Connection(Name=self.Address, Transport="TCP/IP", Protocol="HTTP", Address=Parameters["Address"], Port=self.HTTP_CLIENT_PORT)
        self.atagConn.Connect()
        Domoticz.Log("onStart called")

    def onStop(self):
        Domoticz.Log("onStop called")

    def onConnect(self, Connection, Status, Description):
        if (Status == 0):
            Domoticz.Debug("Atag One connected successfully.")
            payload = { "retrieve_message": { "seqnr":0, 
                                              "account_auth" : { "user_account": "",
                                                                 "mac_address": "xx" },
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
            Connection.Send(sendData)
        else:
            Domoticz.Log("Failed to connect ("+str(Status)+") to: "+Parameters["Address"]+":"+str(self.HTTP_CLIENT_PORT)+" with error: "+Description)
        Domoticz.Log("onConnect called")

    def onMessage(self, Connection, Data):
        Status = int(Data["Status"])
        if (Status == 200):            
            strData = Data["Data"].decode("utf-8", "ignore")
            atagResponse = json.load(strData)['retrieve_reply']
            roomTemp = float(atagResponse['report']['room_temp'])
            targetTemp = float(atagResponse['control']['ch_mode_temp'])
            boilerStatus = int(atagResponse['report']['boiler_status'])
            Domoticz.Log('Atag One status retrieved: roomTemp='+str(roomTemp)+' targetTemp='+str(targetTemp)+' boilerStatus='+str(boilerStatus))
            UpdateDevice(1, targetTemp, str(targetTemp))
            UpdateDevice(2, roomTemp, str(roomTemp))
        else:
            Domoticz.Error('Atag One returned status='+Data['Status'])
        self.atagConn.Disconnect()
        self.atagConn = None
        self.countDown = 0
        Domoticz.Log("onMessage called")

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Log("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Log("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        Domoticz.Log("onDisconnect called")

    def onHeartbeat(self):
        self.countDown = self.countDown + 1
        if self.countDown == 3
            self.atagConn = Domoticz.Connection(Name=self.Address, Transport="TCP/IP", Protocol="HTTP", Address=Parameters["Address"], Port=self.HTTP_CLIENT_PORT)
            self.atagConn.Connect()
        Domoticz.Log("onHeartbeat called")

      
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
        if (Devices[Unit].nValue != nValue) or (Devices[Unit].sValue != sValue)):
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
