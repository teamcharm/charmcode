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
import plotly as plt 
import plotly.figure_factory as ff
import plotly.express as px
import io

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
    # Remove first row of data because first flash is usually due to Arduino connecting to power, not cosmic ray
    data = data[1:]
    event_number = data[:,0].astype(float)
    Ardn_time_ms = data[:,1].astype(float)
    adc = data[:,2].astype(float)
    sipm = data[:,3].astype(float)
    deadtime = data[:,4].astype(float)
    temperature = data[:,5].astype(float)
    return event_number, Ardn_time_ms, adc, sipm, deadtime, temperature


#code for data analysis page when using one detector 


def one_home():
    st.subheader("Mode: One Detector")
    thedata = st.file_uploader(label="Upload data file(s)", accept_multiple_files=False) 
    if thedata is not None: 
        event_number, Ardn_time_ms, adc, sipm, deadtime, temperature = getdata(thedata)
        st.table([("Event number", event_number[0]), ("Ardn_time_ms", Ardn_time_ms[0]), ("adc", adc[0]), ("sipm", sipm[0]), ("deadtime", deadtime[0]), ("temperature", temperature[0])])
    
    # line graph showing SiPM reading spikes (voltage) against time elapsed 

    # histogram of events per 5 minutes 

    # Rate vs calculated SiPM peak voltage line graph 


#code for data analysis page when using two detectors 


def two_home(): 
    st.subheader("Mode: Two Detectors Coincidence") 
    thedata = st.file_uploader(label="Upload data file(s) in this order: master, second", accept_multiple_files=True) 
    parsed_data = {} 
    if thedata: 
        for i, file in enumerate(thedata):  # i = 0, 1, 2, ...
            event_number, Ardn_time_ms, adc, sipm, deadtime, temperature = getdata(file)

            # Store everything in the dict
            parsed_data[i] = {
                "event_number": event_number,
                "Ardn_time_ms": Ardn_time_ms,
                "adc": adc,
                "sipm": sipm,
                "deadtime": deadtime,
                "temperature": temperature
            } 
        
        #simple graph of master + coincidence, sipm values to see how different interactions produced vastly different spikes in sipm voltage
        masterdata = pd.DataFrame(parsed_data[0]) 
        seconddata = pd.DataFrame(parsed_data[1])
        st.write(masterdata)
        st.write(seconddata)
        distplot = px.line(masterdata, x="event_number", y="sipm", color_discrete_sequence=['blue']) 
        distplot.add_scatter(x=seconddata["event_number"], y=seconddata["sipm"], line=dict(color='#AA00CC'))
        st.plotly_chart(distplot)
    # 0 = first file, 1 = second file 
    # ignore this line it is not useful 0 = event_number, 1 = Ardn_time_ms, 2 = adc, 3 = sipm, 4 = deadtime, 5 = temperature  

    # first file will be master file, second file will be the one that determines coincidence; only gets data if triggered 30 microseconds within the master's detection 
    
    # line graph with 2 lines for 2 detectors showing SiPM reading spikes/voltages vs. time elapsed 
    # Histogram of detections in files that have the same time


#code for data analysis page when using three detectors 


def three_home():
    st.subheader("Mode: Three Detectors Coincidence") 
    thedata = st.file_uploader(label="Upload data file(s)", accept_multiple_files=True)
    parsed_data = {}
    if thedata:
        for i, file in enumerate(thedata):  
            parsed_data[i] = getdata(file)
            st.write(parsed_data[i])
    # 0 = first file, 1 = second file, 2 = third file
    # 0 = event_number, 1 = Ardn_time_ms, 2 = adc, 3 = sipm, 4 = deadtime, 5 = temperature