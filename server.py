import socket
import datetime
import json, requests
from flask import Flask, render_template, request, redirect, Response
from datetime import datetime

app = Flask(__name__)
localIP     = "localhost"
localPort   = 20001
bufferSize  = 1024
URL = "http://127.0.0.1:5000" 

#Initalize server
UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
UDPServerSocket.bind((localIP, localPort))
print("UDP server up and listening")
    
#Incoming datagrams
def incomingFeed():

    #Sets cars locked status to unlocked and updates booking table
    def unlockCar(input):
        #Get all required variables
        userIndex = input.find('_user_')
        passIndex = input.find ('_pass_')
        idCarIndex = input.find('_rentCar')
        email = input [userIndex + 6:passIndex]
        idCar = input [idCarIndex + 8:userIndex]
        
        #Set car status to unlocked
        result = requests.put("{}{}".format(URL, "/car"),params={"car_id": idCar, "user_id": email, "locked": 0})    
          
        #If successfully send DB response to client
        if result.status_code == 200:
            msgFromServer       = "successful"
            bytesToSend         = str.encode(msgFromServer)
            UDPServerSocket.sendto(bytesToSend, address)
           
        else:
            msgFromServer       = "unsuccessful"
            bytesToSend         = str.encode(msgFromServer)
            UDPServerSocket.sendto(bytesToSend, address)
        return
    
    #Sets cars locked status to locked and updates booking table
    def returnCar(input):
        userIndex = input.find('_user_')
        passIndex = input.find ('_pass_')
        email = input [userIndex + 6:passIndex]
        idCar = input [32:userIndex]
                                                                                                                                           
        #Query DB endpoint, if successful updates car locked status and updates booking
        result = requests.put("{}{}".format(URL, "/car"),params={"car_id": idCar, "user_id": email, "locked": 1})    
        
        #If successfully send DB response to client
        if result.status_code == 200:
            msgFromServer       = "successful"
            bytesToSend         = str.encode(msgFromServer)
            UDPServerSocket.sendto(bytesToSend, address)
           
        else:
            msgFromServer       = "unsuccessful"
            bytesToSend         = str.encode(msgFromServer)
            UDPServerSocket.sendto(bytesToSend, address)
        return
    
    #login into system, checks credentials
    def login(input):
        userIndex = input.find('_user_')
        passIndex = input.find ('_pass_')
        username = input [userIndex + 6:passIndex]
        password = input [passIndex + 6:-1]
        
        result = requests.get("{}{}".format(URL, "/users/authenticate"),params={"user_id": username, "password": password})    
       
        if result.status_code == 200:
            msgFromServer       = "successful"
            bytesToSend         = str.encode(msgFromServer)
            UDPServerSocket.sendto(bytesToSend, address)
        
        else:
            msgFromServer       = "unsuccessful"
            bytesToSend         = str.encode(msgFromServer)
            UDPServerSocket.sendto(bytesToSend, address)
        return
    
    #Updates car longitude and latitude (every 5 seconds)
    def getLocation(input):
        latitudeIndex = input.find('_location')
        longitudeIndex = input.find(',')
        idCarIndex = input.find("_id")
        car_id = input [idCarIndex + 3: -1]
        latitude = input [latitudeIndex + 9:longitudeIndex]
        longitude = input [longitudeIndex + 1: idCarIndex]                                                                         
        requests.put(URL + "/car", params={"car_id": car_id, "lat":latitude, "lng": longitude})
        return


    while(True):

        bytesAddressPair = UDPServerSocket.recvfrom(bufferSize)
        message = bytesAddressPair[0]
        address = bytesAddressPair[1]
        clientMsg = "Message from Client:{}".format(message)
        clientIP  = "Client IP Address:{}".format(address)
                
        #Translate response into a method
        while(True):
            if ("_rentCar" in clientMsg):
                unlockCar(clientMsg)
                break
           
            if ("_login" in clientMsg):
                login(clientMsg)
                break
            
            if ("_returnCar" in clientMsg):
                returnCar(clientMsg)
                break
            
            if ("_location" in clientMsg):
                getLocation(clientMsg)
                break  
    
if __name__ == '__main__':
    incomingFeed()
  


      
    
   
   
   
  
    
    
   

