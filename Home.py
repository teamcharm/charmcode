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

#For magnetic field experiment, filter out coincidence measurements from both data files and graph them side-by-side 

import streamlit as st 
from PIL import Image


#page setup: tab icon, page name, sidebar is automatically created
appicon = Image.open('public/appicon.png')
st.set_page_config(
    page_title="Team Charm Muon Detector",
    page_icon=appicon
)

st.title("Team Charm Muon Detector")
st.subheader("1-2 sentences about the project") 
with st.popover(label="Help", icon=":material/help:"):
    st.markdown("this will explain how to use the app")
datatype = st.radio(label="Choose detection data type: ", options=["1 detector", "2 detectors", "3 detectors"])

import homepages
if datatype == "1 detector":
    homepages.one_home()
elif datatype == "2 detectors": 
    homepages.two_home()
else: 
    homepages.three_home()