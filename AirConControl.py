import socket, json, time
from requests import post
import paho.mqtt.client as mqtt

# Sets Variables as an irrelevent starting value
Old_Bedroom_AC_Info = "0"
Old_LivingRoom_AC_Info = "0"
SelectUnit = None

# Information to connect to AC Unit
Bedroom_TCP_IP = '10.1.2.110'
LivingRoom_TCP_IP = '10.1.2.111'

# MQTT broker server (in my case, my Homeassistant device)
mqttBroker = "homeassistant.locala" 
client = mqtt.Client("AC_Information")
client.username_pw_set("mqtt", "password")
client.connect(mqttBroker) 

# Function that takes variable 
def GetACInfo():
    # While loop will try to get information and loop if it fails until it gets an expected result
    while True:
        try:
            # Swaps the AC Units so the calls are alternating between the 2 units.
            # Can't set SelectUnit as Unit_Swap requires a starting value
            Unit = Unit_Swap()

            # Now the units have swapped, we set the names back to their operating names
            SelectUnit = Unit

            # Port the AC units are listening on
            TCP_PORT = 30000

            # This command gets all information that is user adjustable
            command = '{"get":"state"}\n'

            # Create a TCP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # Set a longer timeout (e.g., 10 seconds)
            sock.settimeout(10)

            # Connect to the server
            sock.connect((SelectUnit, TCP_PORT))

            # Send the command to the server
            sock.sendall(command.encode())

            # Receive the response from the server
            response = sock.recv(1024)

            # Decode the response
            response = response.decode()

            # Parse the JSON response
            data = json.loads(response)

            # Close the socket
            sock.close()

            # More often than not an invalid response is returned. However "power" should always return. Check returned value contains power, if it doesn't something went wrong it will try again
            if "power" in data:
                
                # Returns the result to the function
                return data, SelectUnit
                
                # Exits while loop with successful data extraction
                break
            
            # Pause script for 1 second and try again
            time.sleep(1)

        except socket.timeout:
            None
        except socket.error as e:
            None   

# Publish results to MQTT broker
def MQTT_Post(data, UnitName):
    for key, value in data.items():
        topic = f"homeassistant/climate/{UnitName}/{key}"  # Topic for each value
        message = str(value)  # Convert value to string if necessary
        client.publish(topic, message)

# Converts the IP address to a Name
def Get_Unit_Name():
    if SelectUnit == Bedroom_TCP_IP:
        UnitName = "Bedroom_AC"
    elif SelectUnit == LivingRoom_TCP_IP:
        UnitName = "LivingRoom_AC"   
    else:
        print("Something fucked up in Get_Unit_Name")
    return UnitName

# Swaps the AC Units to get the info for the other unit
def Unit_Swap():
    global SelectUnit    
    if SelectUnit == Bedroom_TCP_IP:
        SelectUnit = LivingRoom_TCP_IP
    elif SelectUnit == LivingRoom_TCP_IP:
        SelectUnit = Bedroom_TCP_IP
    elif SelectUnit == None:
        print("Setting starting unit to Living Room")
        SelectUnit = LivingRoom_TCP_IP
    else:
        print("Something fucked up in Unit_Swap")
        SelectUnit = Bedroom_TCP_IP
    # Adds a pause so info isnt fetched to often
    time.sleep(1)

    return SelectUnit

# the try is there as way to stop the program
try:
    # Loop the is the actaul proram that loops forever
    while True:
        # Runs the function Get AC Info and the result it gets inside the function is brought outside for use
        data, SelectUnit = GetACInfo()
        
        #Runs Get_Unit_Name to get the current name
        Unit_Name = Get_Unit_Name()

        # Compares if data has changed and only posts to MQTT if it has
        if Unit_Name == "Bedroom_AC":
            New_Bedroom_AC_Info = data
            if New_Bedroom_AC_Info != Old_Bedroom_AC_Info:
                MQTT_Post(data, Unit_Name)
                print(data)
                Old_Bedroom_AC_Info = New_Bedroom_AC_Info          
        elif Unit_Name == "LivingRoom_AC":
            New_LivingRoom_AC_Info = data
            if New_LivingRoom_AC_Info != Old_LivingRoom_AC_Info:
                MQTT_Post(data, Unit_Name)
                print(data)
                Old_LivingRoom_AC_Info = New_LivingRoom_AC_Info
        else:
            print("Something fucked up")
            
        time.sleep(1)

# The actaul stop function
except KeyboardInterrupt:
    print("Program stopped by user input")

client.disconnect()