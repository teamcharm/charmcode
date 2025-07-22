#Upload data file(s) 
#Choose data mode by number of detectors (1, 2, 3) 
#Choose experiment: magnetic field, altitude, time of day, etc.
#View file dropdown shows first and last 5 rows
#Have buttons to show means, modes, medians of variable data (e.g. avg sipm energy)
#Raw graphs if 1 scintillator: 
    #Rate vs calculated SiPM peak voltage line graph, also 3 lines from 3 diff scintillators
    #Coincidence graph: Count rate vs time line graph, also 3 lines from 3 diff scintillators
    #Number of signals by timestamp histogram if time of day experiment
#Coincidence data filtering 
#Graph of coincident measurements 
#Visual experiment simulation with javascript (like interactive PhET where you can apply magnetic field, reposition scintillators, and model it all online)

#For magnetic field experiment, filter out coincidence measurements from both data files and graph them side-by-side 

import streamlit as st 
import pandas as pd 
import numpy as np
import io
#code for data analysis page when using one detector 

#st.cache_data means that once you choose your file, it will be saved until you close/refresh the tab or pick a different file
@st.cache_data
def getdata(datafile):
    file = io.StringIO(datafile.getvalue().decode("utf-8"))
    lines = file.readlines()
    
    header_lines = 0
    column_array = range(2,8) 
    for i in range(min(len(lines), 1000)):
        if 'Device' in lines[i]:
            header_lines = i + 1

    file.seek(0)  # rewind the file so genfromtxt works
    data = np.genfromtxt(file, dtype=str, delimiter=' ', usecols=column_array,
                        invalid_raise=False, skip_header=header_lines)

    # If only one row is loaded, make it 2D
    if data.ndim == 1:
        data = data.reshape(1, -1)

    event_number = data[:,0].astype(float)
    Ardn_time_ms = data[:,1].astype(float)
    adc = data[:,2].astype(float)
    sipm = data[:,3].astype(float)
    deadtime = data[:,4].astype(float)
    temperature = data[:,5].astype(float)
    return event_number, Ardn_time_ms, adc, sipm, deadtime, temperature







#code for data analysis page when using two detectors 





#code for data analysis page when using three detectors 











def one_home():
    st.write("hello")
    thedata = st.file_uploader(label="Upload data file(s)", accept_multiple_files=False) 
    if thedata is not None: 
        event_number, Ardn_time_ms, adc, sipm, deadtime, temperature = getdata(thedata)
        st.table([("Event number", event_number[0]), ("Ardn_time_ms", Ardn_time_ms[0]), ("adc", adc[0]), ("sipm", sipm[0]), ("deadtime", deadtime[0]), ("temperature", temperature[0])])
        # st.write("Event number, Ardn_time_ms, adc, sipm, deadtime, temperature")
        # st.write(event_number[0], Ardn_time_ms[0], adc[0], sipm[0], deadtime[0], temperature[0])
    
    # line graph showing SiPM reading spikes (voltage) against time elapsed 

    # histogram of events per 5 minutes 

    # Rate vs calculated SiPM peak voltage line graph 


def two_home():
    st.write("goodbye")

def three_home():
    st.write("sup")