

import csv
import datetime
import os
import numpy as np
from fCalculation import tdom, fdom  # Importing feature calculation functions
from statistics import mode, StatisticsError  # Importing mode function and StatisticsError exception
from SFt_List import getSensors, getFeatures  # Importing helper functions

def createHeader(sensorList, ftList, t_stamp):
    """
    Creates the header for the feature file.

    Args:
        sensorList (list): List of sensor names.
        ftList (list): List of feature names.
        t_stamp (bool): Indicates if timestamps should be included in the header.

    Returns:
        list: Header for the feature file.
    """
    final = [[]]
    if t_stamp:
        final[0].append('Timestamp')
        
    for sensor in sensorList:
        for feature in ftList:
            final[0].append(sensor + feature)
    final[0].append('Subject')
    final[0].append('Activity')
    final[0].append('Trial')
    final[0].append('Tag')
    return final

def extractSensor(location, temp):
    
    sensorData = []
    for row in temp:
        sensorData.append(row[location])
    return sensorData

def getTime(row):
   
    year = int(row[0][0:4])
    month = int(row[0][5:7])
    day = int(row[0][8:10])
    hour = int(row[0][11:13])
    minute = int(row[0][14:16])
    second = int(row[0][17:19])
    microsecond = int(row[0][20:26])
    return datetime.datetime(year, month, day, hour, minute, second, microsecond)

def get_datetime(row):
    
    base_date = datetime.date(2000, 1, 1)
    cell_value = row[0]
    time_components = cell_value.split(".")
    seconds = int(time_components[0])
    milliseconds = int(time_components[1]) 
    dt = datetime.datetime.combine(base_date, datetime.time()) + datetime.timedelta(seconds=seconds, milliseconds=milliseconds)
    return dt

def process_file(datafile, finaloc, sub, act, trl, actn, twnd, t_stamp=False):
    
    tlen = twnd.split('&')
    st1 = float(tlen[0])
    st2 = float(tlen[1])
    #Opens a csv file and puts it into an array 
    csvFile = open(datafile)
    csvArray = []
    for row in csvFile:
        row = row.split(',')
        csvArray.append(row)
    csvFile.close()
    csvArray = [[item.strip('\n') for item in array]for array in csvArray]
    # Verifica o comprimento de csvArray antes de atribuir starttime
    #Obtains Starting and Ending timestamp of trial
    
    starttime = get_datetime(csvArray[2])
    finaltime = get_datetime(csvArray[len(csvArray)-1])
    
    temp = []
    subSensors = []
    sensorList = getSensors()
    ftList = getFeatures()
    final = createHeader(sensorList, ftList,t_stamp)
    j = 1 
    #To know if a sensor has presented an error:
    i_prev = -1
    #While loop that runs from starttime to finaltime
    while starttime+datetime.timedelta(seconds=st1) <= finaltime:
        
        #Data is collected within st1 second windows, with the starttime increasing by st2 seconds
        for row in csvArray[2:]:
            if starttime <= get_datetime(row) and get_datetime(row) <= starttime+datetime.timedelta(seconds=st1):
                temp.append(row)
        #All data is seperated into individial lists containing only data from a single sensor (i.e. Ankle Accelerometer x-axis)
        try:
            for i in range(len(temp[0])):
                subSensors.append([])
                for row in temp:
                    subSensors[i].append(row[i])
            
            #A new list is added to put calculated data in
            final.append([])
            if t_stamp:
                #The start time of the window is added
                final[j].append(datetime.datetime.strftime(starttime, '%S.%f'))
            #For loop going though each individual sensor's data
            i_sensor = 0
            for row in subSensors[1:len(sensorList)+1]:
                try:
                    #Converts row into floats
                    nrow = list(map(float, row))
                    #Extracts features
                    features = tdom(nrow,ftList)
                    #Extract frquency features
                    frequency = fdom(nrow,subSensors[0],ftList)
                    #Add features to final array
                    for dat in features:
                        final[j].append(dat)
                    #Add frequency features to final array
                    for dat1 in frequency:
                        final[j].append(dat1)
                except ValueError as e:
                    if i_sensor != i_prev:
                        print('---------Error with ' + sensorList[i_sensor] +': ' + str(e))
                        i_prev = i_sensor
                    for i in range(0,len(ftList)):
                        final[j].append('')
                i_sensor += 1
            #Add Subject,Activity,Trial,and Tag at the end of row
            final[j].append(int(mode(subSensors[len(subSensors)-4])))
            final[j].append(int(mode(subSensors[len(subSensors)-3])))
            final[j].append(int(mode(subSensors[len(subSensors)-2])))
            try:
                final[j].append(int(mode(subSensors[len(subSensors)-1])))
            except StatisticsError:
                final[j].append(actn)
            j+=1
        #Exception for when the st1 second window exceeds data timestamps
        except Exception as ex:
            if str(ex) == 'list index out of range':
                print('------Possible data absence between timestamps: ')
                nexttime = starttime + datetime.timedelta(seconds = st2)
                print('-----------' +str(starttime)+ ' and ' + str(nexttime))
            else:
                print('---Unexpected error: ' + str(ex))
        #st2 seconds are added for overlapping windowing
        starttime += datetime.timedelta(seconds = st2)
        #temp and subSensor arrays are reset
        temp = []
        subSensors = []     
        

    # Remove rows with empty or non-numeric values
    final_cleaned = [final[0]] + [row for row in final[1:] if not any(val == '' or np.isnan(float(val)) for val in row)]

    if len(final_cleaned) <= 1:
        os.remove(datafile)
    else:
        os.makedirs(finaloc, exist_ok=True)
        with open(os.path.join(finaloc, f'WEDAFALL_{sub}_{act}_{trl}_Features{twnd}.csv'), 'w', newline='') as newDataSet:
            csv.writer(newDataSet).writerows(final_cleaned)


def extract_features_WEDA(d_base_path, features_path, window, n_sub=(1, 31), n_act=(1, 20), n_trl=(1, 4), t_stamp=False):
    
    if not os.path.exists(features_path):
        os.makedirs(features_path)
        
    t_window=(window)
    for twnd in t_window:
        print(twnd)
        for i in range(n_sub[0], n_sub[1] + 1):
            sub = f'Subject{i}'
            print(f'{twnd}-{sub}')
            for j in range(n_act[0], n_act[1] + 1):
                act = f'Activity{j}'
                print(f'{twnd}-{i}--{act}')
                for k in range(n_trl[0], n_trl[1] + 1):
                    trl = f'Trial{k}'
                    subloc = f'{sub}/{act}/'
                    path1 = os.path.join(d_base_path, subloc, trl, f'WEDAFALL_{sub}{act}{trl}.csv')
                    print(f"Full path: {path1}")

                    path2 = os.path.join(features_path, subloc, trl)
                    print(f'------{trl} - {twnd}')

                    try:
                        with open(path1) as csv_file:
                            csv_reader = csv.reader(csv_file)
                            num_lines = sum(1 for _ in csv_reader)

                        if num_lines >= 4:
                            print('---------------------DONE')
                            process_file(path1, path2, sub, act, trl, j, twnd, t_stamp)
                            print('---------------------DONE')
                        else:
                            print('File ignored: (less than 4 lines)')

                    except FileNotFoundError:
                        print('File not found: ')
                    except OSError:
                        print('Error accessing file or directory: ')

       
def main():
    d_base_path = '/Users/nityareddy/Desktop/AIML PROJECT/normalized'
    features_path = d_base_path
    window = ('6&3',)
    # Extract features from data files
    try:
        extract_features_WEDA(d_base_path, features_path, window)
    except:
        print('Feature extraction completed')

if __name__ == "__main__":
    main()
    