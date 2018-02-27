'''
updated on 11 Feb 2018

v0.3

@author: Stephen Rawlings

Final Year Project
'''
from io import StringIO
import winreg # to use windows registry to ID guids given by netifaces
import netifaces # used to identify netwrok interafces on a system and returning the ocrresponding guid
import pickle # used to save the model for further testing and use
import csv #python standard for csv work
import pyshark # tshark wrapper used to capture and parse packets
import time
import datetime
import pandas # data handler
from builtins import int
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics import matthews_corrcoef
from timeit import default_timer as timer
from sklearn.metrics.classification import matthews_corrcoef
from sklearn.preprocessing import LabelEncoder

def main():
        print(__doc__)
        int = netifaces.interfaces()
        mlp_live_iteration = 0
        #cap = pyshark.FileCapture('test.pcap') # For training 

        def get_ip_layer_name(pkt): #allows the program to differentiate between ipv4 and ipv6, needed for correct parsing of packets
            for layer in pkt.layers:
                if layer._layer_name == 'ip':
                    return 4
                elif layer._layer_name == 'ipv6':
                    return 6
        
        def packet_info(cap): # Goes through each packet in capture or live_capture, displays various information about each packet
            start_time = time.time()
            try:
                i = 1
                for pkt in cap:
                    i += 1  
                    if pkt.highest_layer != 'ARP':
                        ip = None
                        ip_layer = get_ip_layer_name(pkt)
                        if ip_layer == 4:
                            ip = pkt.ip
                        elif ip_layer == 6:
                            ip = pkt.ipv6
                        print ('Packet %d' % i)
                        print (pkt.highest_layer)
                        print (pkt.transport_layer)
                        print ('Time', pkt.sniff_time)
                        print ('Layer: ipv%d' % get_ip_layer_name(pkt))
                        print ('Source IP:', ip.src)
                        print ('Destination IP:', ip.dst)
                        try:
                            print ('Source Port', pkt[pkt.transport_layer].srcport)
                            print ('Destination Port', pkt[pkt.transport_layer].dstport)
                        except AttributeError:
                            print ('Source Port: ', 0)
                            print ('Destination Port: ', 0)
                        print (i/(time.time() - start_time))
                        print ('')
                    else:
                        arp = pkt.arp
                        print(pkt.highest_layer)
                        print(pkt.transport_layer)
                        print('Layer: ipv4' )
                        print('Time', pkt.sniff_time)
                        print('Source IP: ', arp.src_proto_ipv4)
                        print('Destination IP: ', arp.dst_proto_ipv4)
                        print ('Source Port: ', 0)
                        print ('Destination Port: ', 0)
                        print (i/(time.time() - start_time))
                        print()             
                return
            except KeyboardInterrupt:
                pass
       
        def csvgather(cap): # creates/rewrites 'test.csv' file - writes header row - goes through packets, writing a row to the csv for each packet
            start_time = time.time()
            try:
                with open ('test.csv', 'w', newline='') as csvfile:
                    filewriter = csv.writer(csvfile, delimiter=',' , quotechar='|', quoting=csv.QUOTE_MINIMAL)
                    filewriter.writerow(['Packet', 'Highest Layer', 'Transport Layer', 'Source IP', 'Dest IP', 'Source Port', 'Dest Port', 'Time', 'Packets/Time', 'target' ])
                    tcp_count = 0
                    udp_count = 0
                    icmp_count = 0
                    other_count = 0

                    
                    i = 0
                   
                    for pkt in cap:
                        if pkt.highest_layer != 'ARP':                
                            print ("Time: ", time.time() - start_time)
                            i += 1
                            print("Packets Collected:", i)
                            if pkt.highest_layer != 'ARP':
                                ip = None
                                ip_layer = get_ip_layer_name(pkt)
                                if ip_layer == 4:
                                    ip = pkt.ip
                                    ipv4_count += 1
                                    ipv = 0 # target test
                                    if pkt.transport_layer == None:
                                        transport_layer = 'None'
                                    else:
                                        transport_layer = pkt.transport_layer
                                elif ip_layer == 6:
                                    ip = pkt.ipv6
                                    ipv = 1 # target test
                                    ipv6_count += 1 
                                                                   
                                try:
                                    filewriter.writerow([i, pkt.highest_layer, transport_layer, ip.src, ip.dst, pkt[pkt.transport_layer].srcport, pkt[pkt.transport_layer].dstport, pkt.sniff_time, i/(time.time() - start_time), ipv ])
                                except AttributeError:
                                    filewriter.writerow([i, pkt.highest_layer, transport_layer, ip.src, ip.dst, 0, 0, pkt.sniff_time, i/(time.time() - start_time), ipv ])
                            
                            else:
                                arp = pkt.arp
                                filewriter.writerow([i, pkt.highest_layer , transport_layer, arp.src_proto_ipv4, arp.dst_proto_ipv4, 0, 0, pkt.sniff_time, i/(time.time() - start_time), 0])
                        
            except KeyboardInterrupt:
                pass                
         
        def int_names(int_guids): # Looks up the GUID of the network interfaces found in the registry, then converts them into an identifiable format
            int_names = int_names = ['(unknown)' for i in range(len(int_guids))]
            reg = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
            reg_key = winreg.OpenKey(reg, r'SYSTEM\CurrentControlSet\Control\Network\{4d36e972-e325-11ce-bfc1-08002be10318}')
            for i in range(len(int_guids)):
                try:
                    reg_subkey = winreg.OpenKey(reg_key, int_guids[i] + r'\Connection')
                    int_names[i] = winreg.QueryValueEx(reg_subkey, 'Name')[0]
                except FileNotFoundError:
                    pass
            return int_names
                
        def LabelEncoding(data): # encodes the categorical data within the csv used for training, turns the categorical values into integer values
                
            data = pandas.read_csv('test.csv', delimiter=',') 
            columnsToEncode = list(data.select_dtypes(include=['category', 'object']))  
            print(data.dtypes)
            print(columnsToEncode)
            
            le = LabelEncoder()
            for feature in columnsToEncode:
                try:
                    data[feature] = le.fit_transform(data[feature])
                   # print(data[feature])
                except:
                    print ('error' + feature)
            return data
        
        def csv_data_check(): # Displays the data within the chosen csv, allows the user to view ALL data, ONLY NUMERICAL or ONLY CATEGORICAL
            l_data = input("Name of csv file: ")
            data = pandas.read_csv(l_data, delimiter=',')
            read_choice = input("""How would you like to view the data?
                                
                                All (a)
                                Numerical Only (n)
                                Categorical Only (c)
                                
                                """)
            if read_choice == "a":
                print(data)
            elif read_choice == "n":
                print(data._get_numeric_data())
            elif read_choice == "c":
                print(data.select_dtypes(include='object'))
        
        def Load_model(): # loads a saved model to use for both training 

            filename = input("Model to load?")
            loaded_model = pickle.load(open(filename, 'rb'))
            print(loaded_model.coefs_)
            print(loaded_model.loss_)
            
            return loaded_model

        def int_choice(): #allows the user to choose interface
            for i, value in enumerate(int_names(int)):
                print(i, value)
            print('\n')
            t = input("Please select interface: ")
            cap = pyshark.LiveCapture(interface= t)
            cap.sniff_continuously(packet_count=None)
            
            return cap  

        def MLP(): #Primarily used for training either a new model or updating a previous model

            l_data = input("Name of CSV file? ")
            
            load = input("Load model?")
            if load == 'y':
                mlp = Load_model()

            else:
                from sklearn.neural_network import MLPClassifier
                mlp = MLPClassifier(hidden_layer_sizes=(5), activation='logistic', max_iter=1000) # number of hidden layers = 1 layer of 10 nodes
  
            
            data = pandas.read_csv(l_data, delimiter=',')# reads CSV
            data_copy =  pandas.read_csv(l_data, delimiter=',')
            #data = data._get_numeric_data() #parses only numerical data in csv
            data = LabelEncoding(data)
            print(data) # entire block for testing and checking values
           # print(data.keys())
            #print(data[['Packet','Packets/Time']])
            #print(data['target'])
            
            X = data[['Packet', 'Highest Layer', 'Transport Layer', 'Source IP', 'Dest IP', 'Source Port', 'Dest Port', 'Time', 'Packets/Time', 'target' ]] # Data used to train
            print (X)
            y = data['target'] # targets for the MLP
            print (y)
            
            from sklearn.model_selection import train_test_split
            from sklearn.preprocessing import StandardScaler
            X_train, X_test, y_train, y_test = train_test_split(X, y)
            scaler = StandardScaler()
            
            scaler.fit(X_train)
            X_train = scaler.transform(X_train)
            X_test = scaler.transform(X_test)
            
            print(X_train)
            print(X_test)

            mlp.fit(X_train, y_train)
            #print(mlp.predict(X_test))
            
            
            predictions = mlp.predict(X_test)
            print(mlp.predict(X_test)[0:20])
            print(mlp.predict_proba(X_test)[0:20])
            hostile = 0
            safe = 0
            for check in predictions:
                if check == 1:
                    hostile += 1
                else:
                    safe += 1
            print(hostile)
            print(safe)
            
            if hostile >= ((safe + hostile)/2):
                print ("DDoS ATTACK DETECTED!")
                return
            else:                               
                from sklearn.metrics import classification_report,confusion_matrix
                print(confusion_matrix(y_test,predictions))
                print (classification_report(y_test,predictions))
    
                ci = input("do you want to see weights and intercepts?" )
                if ci == 'y':
                    print(mlp.coefs_)
                    print(mlp.intercepts_)
                else:
                    pass
                
                save = input("Save model?")
                if save == 's':
                            filename = input("Filename for saving?: ")
                            pickle.dump(mlp, open(filename, 'wb'))
            
        def MLP_Live_predict(cap, modelname, mlp_live_iteration):  # similar to MLP(), used for real-time classification and not for training             
                
            data = pandas.read_csv('LiveAnn.csv', delimiter=',') # reads CSV 
            #data = data._get_numeric_data() #parses only numerical data in csv
            #print(data)
            data = LiveLabelEncoding(data)
            print("Processing Data", "\n")
            print(data)
            X = data[['Packet', 'Highest Layer', 'Transport Layer', 'Source IP', 'Dest IP', 'Source Port', 'Dest Port', 'Time', 'Packets/Time', 'target' ]] # Data used to train
            y = data['target'] # targets for the MLP
            from sklearn.model_selection import train_test_split
            from sklearn.preprocessing import StandardScaler
            #print ("Data: " , "\n")
            #print (X, "\n")
            #print("Targets:", "\n")
            #print (y, "\n")

            
            scaler = StandardScaler()            
            scaler.fit(X)
            X = scaler.transform(X)
            
            loaded_model = pickle.load(open(modelname, 'rb')) # loads model
            print("Model Coeffcients", loaded_model.coefs_) # load model coefs
            
            lmlp = loaded_model
            
            predictions = lmlp.predict(X) # preditcions made by model
            
            hostile = 0 # this block counts how many 'hostile' packets have been predicted by the model
            safe = 0
            for check in predictions:
                if check == 0: # change to 0 to force ddos attack
                    hostile += 1
                else:
                    safe += 1
            print("Safe Packets: ", safe)
            print("Possible Hostile Packets: ", hostile)
            print(100 * hostile/(safe + hostile))
            print ("\n")
            mlp_live_iteration += 1
            
            if hostile >= ((safe + hostile)/2):
                return ("Attack")
            else:
                return mlp_live_iteration
            #print("Predictions")
            #print (predictions)
            #from sklearn.metrics import classification_report,confusion_matrix

            #print(confusion_matrix(y,predictions))
            #print(classification_report(y,predictions))
            

        def csv_interval_gather(cap): # creates/rewrites 'Live.csv' file with 30 second intervals- writes header row - goes through packets, writing a row to the csv for each packet
            start_time = time.time()
            with open ('LiveAnn.csv', 'w', newline='') as csvfile:
                filewriter = csv.writer(csvfile, delimiter=',' , quotechar='|', quoting=csv.QUOTE_MINIMAL)
                filewriter.writerow(['Packet', 'Highest Layer', 'Transport Layer', 'Source IP', 'Dest IP', 'Source Port', 'Dest Port', 'Time', 'Packets/Time', 'target' ])
                tcp_count = 0
                udp_count = 0
                icmp_count = 0
                other_count = 0
                
                i = 0
                start = timer()
                for pkt in cap:
                    end = timer()     
                    if (end - start < 30):                
                        if pkt.highest_layer != 'ARP':                
                            print ("Time: ", time.time() - start_time)
                            i += 1
                            print("Packets Collected:", i)
                            if pkt.highest_layer != 'ARP':
                                ip = None
                                ip_layer = get_ip_layer_name(pkt)
                                if ip_layer == 4:
                                    ip = pkt.ip
                                    #ipv4_count += 1
                                    ipv = 0 # target test
                                    if pkt.transport_layer == None:
                                        transport_layer = 'None'
                                    else:
                                        transport_layer = pkt.transport_layer
                                elif ip_layer == 6:
                                    ip = pkt.ipv6
                                    ipv = 1 # target test
                                    #ipv6_count += 1 
                                                                   
                                try:
                                    filewriter.writerow([i, pkt.highest_layer, transport_layer, ip.src, ip.dst, pkt[pkt.transport_layer].srcport, pkt[pkt.transport_layer].dstport, pkt.sniff_time, i/(time.time() - start_time), ipv ])
                                except AttributeError:
                                    filewriter.writerow([i, pkt.highest_layer, transport_layer, ip.src, ip.dst, 0, 0, pkt.sniff_time, i/(time.time() - start_time), ipv ])
                            
                            else:
                                arp = pkt.arp
                                filewriter.writerow([i, pkt.highest_layer , transport_layer, arp.src_proto_ipv4, arp.dst_proto_ipv4, 0, 0, pkt.sniff_time, i/(time.time() - start_time), 0])
                    else:
                        return
                    
        def LiveLabelEncoding(data): # same as LabelEncoding(), but use fir reaktime
            data = pandas.read_csv('LiveAnn.csv', delimiter=',') 
            columnsToEncode = list(data.select_dtypes(include=['category', 'object']))  
            print(columnsToEncode)
            le = LabelEncoder()
            for feature in columnsToEncode:
                try:
                    data[feature] = le.fit_transform(data[feature])
                   # print(data[feature])
                except:
                    print ('error ' + feature)
            return data
        
        def menu():            
            ans = True
            live = True
            while ans:
                print ("""
                1. Visual Packet Sniffer
                2. ANN Data gatherer
                3. Neural Network Trainer
                4. Data Check
                5. Live Neural Network
                6. Exit
                """)
    
                ans = input("What would you like to do? ") 
                if ans=="1":
                    cap = int_choice()
                    packet_info(cap)
                elif ans=="2":
                    cap = int_choice()
                    print("Now Gathering data....")
                    csvgather(cap)
                elif ans=="3":
                    MLP()
                elif ans =="4":
                    csv_data_check()
                elif ans == "5":
                    cap = int_choice()
                    modelname = input("Please input model: ")
                    try:
                        while live:                                      
                            csv_interval_gather(cap)
                            MLP_Live_predict(cap, modelname, mlp_live_iteration)
                            if MLP_Live_predict(cap, modelname, mlp_live_iteration) == "Attack":
                                live = False
                                print("DDoS ATTACK DETECTED! @ ", datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
                    except KeyboardInterrupt:
                        pass                            
                            
    
                elif ans == "6":
                    break
        menu()
main()