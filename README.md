# Domoticz-AtagOne-Local
Domoticz python plugin for local access to Atag One thermostat

For the plugin to function it's needed that both the Atag One Thermostat and the Domoticz servers are on the same subnet or that they can reach each other.

The plugin is tested to works on a Raspberry Pi 3b.

To install the plugin login to the Raspberry Pi.
  
      cd /home/<username>/domoticz/plugin
  
      git clone https://github.com/Wizzard72/Domoticz-AtagOne
      
      sudo systemctl restart domoticz.service

The plugin requires the following information:
  
    IP Address of the Atag One Thermostat
    
    MAC Address of the Domoticz Server
