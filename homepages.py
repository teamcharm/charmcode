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
import plotly.graph_objects as go
import plotly.express as px
import io 
import statsmodels.api as sm

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

    # Set variable arrays
    event_number = data[:,0].astype(float)
    Ardn_time_ms = data[:,1].astype(float)
    adc = data[:,2].astype(float)
    sipm = data[:,3].astype(float)
    deadtime = data[:,4].astype(float)
    temperature = data[:,5].astype(float) 

    # Output of function
    return event_number, Ardn_time_ms, adc, sipm, deadtime, temperature


#code for data analysis page when using one detector 


def one_home():
    st.subheader("Mode: One Detector")
    thedata = st.file_uploader(label="Upload data file", accept_multiple_files=False) 

    if thedata is not None: 
        # Get data arrays
        event_number, Ardn_time_ms, adc, sipm, deadtime, temperature = getdata(thedata) 
        # Convert Arduino time from ms to minutes 
        ardn_time_min = Ardn_time_ms / 60000.0 
        data = {
            "event number": event_number,
            "ardn time": ardn_time_min,
            "adc": adc,
            "sipm": sipm,
            "deadtime": deadtime,
            "temp": temperature
        }

        # Let the user pick legends for detectors 
        line_color = st.color_picker("Pick a line color for SiPM voltage plot", "#1f77b4")

        #Number of events per time histogram

        # Step 1: Set bin size (1 minute)
        bin_size = 1.0  # minutes
        time = ardn_time_min

        # Step 2: Create DataFrame with just time
        df_time = pd.DataFrame({"time": time})

        # Step 3: Plot histogram
        fig2 = px.histogram(
            df_time,
            x="time",
            nbins=int((time[-1] - time[0]) / bin_size),
            title="Event Count per Minute",
        )

        fig2.update_traces(
            marker_color=line_color,
            marker_line_width=1,
            marker_line_color="black",
            opacity=0.8,
            hovertemplate=
                "Time: %{x} min<br>" +
                "Events: %{y}<br>" +
                "<extra></extra>"
        )

        fig2.update_layout(
            xaxis=dict(
                title="Time [minutes]",
            ),
            yaxis=dict(
                title="Number of Events",
            ),
            bargap=0.05,
            width=800,
            height=500
        )

        st.plotly_chart(fig2, use_container_width=True) 
        
        #Rate vs. Calculated SiPM Peak Voltage Histogram 

        # Step 1: Set up values and bin parameters
        bin_size = 0.25  # 15 second intervals 
        time = ardn_time_min  
        sipm_values = sipm

        rate = []
        peakV = []

        curr_time = time[0]
        start_index = 0
        peak = 0

        # Step 2: Loop through data to collect per-bin peak voltage and rate
        for i in range(1, len(time)):
            if time[i] - curr_time >= bin_size:
                peak = max(sipm_values[peak:(i+1)])
                duration = time[i] - curr_time
                r = (i - start_index) / (duration * 60)  # Convert from per minute to per second (Hz)
                rate.append(r)
                peakV.append(peak)
                curr_time = time[i]
                start_index = i
                peak = i

        # Step 3: Create histogram from peakV, weighted by rate
        df_hist = pd.DataFrame({
            "peak": peakV,
            "rate": rate
        })

        fig = px.histogram(
            df_hist,
            x="peak",
            y="rate",
            title="SiPM Peak Voltages vs. Detection Rate",
        )

        fig.update_traces(
            marker_color=line_color,
            marker_line_width=1,
            marker_line_color="black",
            opacity=0.7,
            hovertemplate=
                "Peak Voltage: %{x} mV<br>" +
                "Rate: %{y:.4f} s⁻¹<br>" +
                "<extra></extra>"
        )

        fig.update_layout(
            xaxis=dict(
                title="Calculated SiPM peak voltage [mV]",
                #type="log"
            ),
            yaxis=dict(
                title="Rate/bin [s⁻¹]",
                #type="log"
            ),
            bargap=0.05,
            width=800,
            height=500
        )

        st.plotly_chart(fig, use_container_width=True)

        # Dark count rate (noise) against temperature 
        dark_threshold = float(st.text_input("Enter threshold (in mV) for dark counts: ", value="90")) #mV

        # Step 1: Filter for "dark counts" — events with peak SiPM voltage < threshold (e.g., 200 mV)
        bin_size = 1
        dark_rates = []
        dark_temps = []
        curr_time = ardn_time_min[0]
        start_index = 0
        peak = 0

        for i in range(1, len(ardn_time_min)):
            if ardn_time_min[i] - curr_time >= bin_size:
                peak = max(sipm[start_index:i+1])
                avg_temp = np.mean(data["temp"][start_index:i+1])
                duration = ardn_time_min[i] - curr_time
                r = (i - start_index) / (duration * 60)  # Hz

                # If the peak SiPM voltage is low, treat as dark count
                if peak < dark_threshold:
                    dark_rates.append(r)
                    dark_temps.append(avg_temp)

                curr_time = ardn_time_min[i]
                start_index = i

        # Step 2: Make DataFrame
        df_dark = pd.DataFrame({
            "temperature": dark_temps,
            "dark_rate": dark_rates
        })

        # Step 3: Scatter + trend line
        # Step 1: Apply LOWESS smoothing
        lowess_result = sm.nonparametric.lowess(
            endog=df_dark["dark_rate"],
            exog=df_dark["temperature"],
            frac=0.3  # Smoothing parameter (adjust as needed)
        )

        # Step 2: Create scatter plot
        fig = px.scatter(
            df_dark,
            x="temperature",
            y="dark_rate",
            title="Dark Count Rate vs Temperature",
            labels={"temperature": "Temperature [°C]", "dark_rate": "Dark Rate [Hz]"},
        )

        # Step 3: Add smoothed line manually
        fig.add_trace(go.Scatter(
            x=lowess_result[:, 0],
            y=lowess_result[:, 1],
            mode="lines",
            name="Trend",
            line=dict(color="red", width=2, dash="solid")
        ))

        # Step 4: Update layout
        fig.update_layout(
            width=800,
            height=500
        )

        st.plotly_chart(fig, use_container_width=True)

        # Sipm Voltages vs. Time graph 

        # Line of best fit using 1st-degree polynomial 
        coeffs = np.polyfit(ardn_time_min, sipm, deg=1)
        poly = np.poly1d(coeffs)
        trend_y = poly(ardn_time_min)

        # Create plot
        fig = go.Figure()

        # Add main SiPM voltage line first (so trend appears above)
        fig.add_trace(go.Scatter(
            x=ardn_time_min,
            y=sipm,
            mode="lines",
            name="SiPM Voltage",
            line=dict(color=line_color),
            hovertemplate="Time elapsed = %{x:.2f} min<br>SiPM voltage = %{y:.2f} mV<extra></extra>"
        ))

        # Add polynomial trend line
        fig.add_trace(go.Scatter(
            x=ardn_time_min,
            y=trend_y,
            mode="lines",
            name="Best Fit Trend",
            line=dict(color="orange", width=3, dash="dot"),
            hovertemplate="Trend (best fit) = %{y:.2f} mV<extra></extra>"
        ))

        # Final layout
        fig.update_layout(
            title="SiPM Voltage Over Time",
            xaxis_title="Time Elapsed (min)",
            yaxis_title="SiPM Voltage (mV)",
            width=700,
            height=500
        )

        # Display SiPM Voltage vs Time graph
        st.plotly_chart(fig, use_container_width=True) 


#code for data analysis page when using two detectors 


def two_home():
    st.subheader("Mode: Two Detectors")
    thedata = st.file_uploader(label="Upload data file(s)", accept_multiple_files=True)
    if thedata and len(thedata) == 2:
        parsed_data = {}
        for i, file in enumerate(thedata):
            event_number, Ardn_time_ms, adc, sipm, deadtime, temperature = getdata(file)
            ardn_time_min = Ardn_time_ms / 60000.0
            parsed_data[i] = {
                "event_number": event_number,
                "ardn_time_min": ardn_time_min,
                "adc": adc,
                "sipm": sipm,
                "deadtime": deadtime,
                "temperature": temperature
            }

        # Coincidence checkbox
        is_coincidence = st.checkbox("Were the detectors in coincidence mode?")

        # Labels and colors for detectors
        label0 = st.text_input("Label for Detector 1", value="Detector 1")
        color0 = st.color_picker("Color for Detector 1", value="#1f77b4")
        label1 = st.text_input("Label for Detector 2", value="Detector 2")
        color1 = st.color_picker("Color for Detector 2", value="#ff7f0e")

        if not is_coincidence:
            st.write("Upcoming feature: choose experiment type")
            experiment_type = st.radio("Choose experiment type:", ["Temperature", "Altitude", "Shielding"])
        
        # ---- Graph: Number of Events Per Minute ----
        fig_time = go.Figure()
        for i, (label, color) in enumerate([(label0, color0), (label1, color1)]):
            time = parsed_data[i]["ardn_time_min"]
            fig_time.add_trace(go.Histogram(
                x=time,
                name=label,
                marker_color=color,
                opacity=0.7,
                xbins=dict(size=1.0)
            ))
        fig_time.update_layout(title="Event Count per Minute",
                               xaxis_title="Time [minutes]",
                               yaxis_title="Number of Events",
                               barmode="overlay",
                               width=800,
                               height=500)
        st.plotly_chart(fig_time, use_container_width=True)

        # ---- Graph: SiPM Peak Voltages vs Detection Rate ----
        fig_peak = go.Figure()
        for i, (label, color) in enumerate([(label0, color0), (label1, color1)]):
            time = parsed_data[i]["ardn_time_min"]
            sipm = parsed_data[i]["sipm"]
            rate, peakV = [], []
            bin_size = 0.25
            curr_time = time[0]
            start_index = 0
            peak = 0
            for j in range(1, len(time)):
                if time[j] - curr_time >= bin_size:
                    peak = max(sipm[peak:(j+1)])
                    duration = time[j] - curr_time
                    r = (j - start_index) / (duration * 60)
                    rate.append(r)
                    peakV.append(peak)
                    curr_time = time[j]
                    start_index = j
                    peak = j
            fig_peak.add_trace(go.Histogram(
                x=peakV,
                y=rate,
                name=label,
                marker_color=color,
                histfunc="sum",
                opacity=0.7,
                xbins=dict(size=10)
            ))
        fig_peak.update_layout(title="SiPM Peak Voltages vs Detection Rate",
                               xaxis_title="Calculated SiPM peak voltage [mV]",
                               yaxis_title="Rate/bin [s⁻¹]",
                               barmode="overlay",
                               width=800,
                               height=500)
        st.plotly_chart(fig_peak, use_container_width=True)

        # ---- Graph: Dark Count Rate vs Temperature ----
        fig_dark = go.Figure()
        threshold0 = float(st.text_input(f"Threshold (mV) for dark counts ({label0}):", value="90"))
        threshold1 = float(st.text_input(f"Threshold (mV) for dark counts ({label1}):", value="90"))
        for i, (label, color, threshold) in enumerate([(label0, color0, threshold0), (label1, color1, threshold1)]):
            time = parsed_data[i]["ardn_time_min"]
            sipm = parsed_data[i]["sipm"]
            temp = parsed_data[i]["temperature"]
            dark_rates = []
            dark_temps = []
            curr_time = time[0]
            start_index = 0
            for j in range(1, len(time)):
                if time[j] - curr_time >= 1:
                    peak = max(sipm[start_index:j+1])
                    avg_temp = np.mean(temp[start_index:j+1])
                    duration = time[j] - curr_time
                    r = (j - start_index) / (duration * 60)
                    if peak < threshold:
                        dark_rates.append(r)
                        dark_temps.append(avg_temp)
                    curr_time = time[j]
                    start_index = j
            fig_dark.add_trace(go.Scatter(
                x=dark_temps,
                y=dark_rates,
                mode="markers",
                name=label,
                marker=dict(color=color, size=6)
            ))
        fig_dark.update_layout(title="Dark Count Rate vs Temperature",
                               xaxis_title="Temperature [°C]",
                               yaxis_title="Dark Rate [Hz]",
                               width=800,
                               height=500)
        st.plotly_chart(fig_dark, use_container_width=True)

        # ---- Graph: SiPM Voltage vs Time + Trendline ----
        fig_trend = go.Figure()
        trend_colors = ["#555555", "#AAAAAA"]
        for i, (label, color, trend_color) in enumerate(zip([label0, label1], [color0, color1], trend_colors)):
            time = parsed_data[i]["ardn_time_min"]
            sipm = parsed_data[i]["sipm"]
            coeffs = np.polyfit(time, sipm, deg=1)
            poly = np.poly1d(coeffs)
            trend_y = poly(time)
            fig_trend.add_trace(go.Scatter(x=time, y=sipm, mode="lines", name=label,
                                           line=dict(color=color)))
            fig_trend.add_trace(go.Scatter(x=time, y=trend_y, mode="lines", name=f"{label} Trend",
                                           line=dict(color=trend_color, dash="dot")))
        fig_trend.update_layout(title="SiPM Voltage Over Time",
                                xaxis_title="Time Elapsed (min)",
                                yaxis_title="SiPM Voltage (mV)",
                                width=800,
                                height=500)
        st.plotly_chart(fig_trend, use_container_width=True)

        # ---- Graph: Muon Count Rate per Second (10s Bins) ----
        fig_muonrate = go.Figure()
        trend_colors = ["#555555", "#AAAAAA"]

        for i, (label, color, trend_color) in enumerate(zip([label0, label1], [color0, color1], trend_colors)):
            time_sec = parsed_data[i]["ardn_time_min"] * 60  # convert minutes to seconds
            rate_values = []
            bin_times = []

            bin_size = 10  # seconds
            curr_time = time_sec[0]
            start_index = 0

            for j in range(1, len(time_sec)):
                if time_sec[j] - curr_time >= bin_size:
                    duration = time_sec[j] - curr_time
                    rate = (j - start_index) / duration  # Hz
                    rate_values.append(rate)
                    bin_times.append(curr_time)
                    curr_time = time_sec[j]
                    start_index = j

            # Add bar graph of actual data
            fig_muonrate.add_trace(go.Bar(
                x=bin_times,
                y=rate_values,
                name=label,
                marker_color=color,
                opacity=0.7
            ))

            # Add trendline
            if len(bin_times) > 1:
                coeffs = np.polyfit(bin_times, rate_values, deg=1)
                poly = np.poly1d(coeffs)
                trend_y = poly(bin_times)

                fig_muonrate.add_trace(go.Scatter(
                    x=bin_times,
                    y=trend_y,
                    mode="lines",
                    name=f"{label} Trend",
                    line=dict(color=trend_color, dash="dot")
                ))

        fig_muonrate.update_layout(title="Muon Count Rate per Second (10s Bins)",
                                   xaxis_title="Time [seconds]",
                                   yaxis_title="Muon Rate [Hz]",
                                   barmode="overlay",
                                   width=800,
                                   height=500)
        st.plotly_chart(fig_muonrate, use_container_width=True)


        if is_coincidence:
            st.markdown("**[TODO] Add coincidence-specific visualizations here.**")


#code for data analysis page when using three detectors 


def three_home():
    st.subheader("Mode: Three Detectors (Fridge, Room, Heating Pad)")
    thedata = st.file_uploader(label="Upload data file(s)", accept_multiple_files=True)

    if thedata and len(thedata) == 3:
        labels = ["Fridge", "Room", "Heating Pad"]
        default_colors = ["#1f77b4", "#2ca02c", "#d62728"]
        parsed_data = {}

        for i, file in enumerate(thedata):
            event_number, Ardn_time_ms, adc, sipm, deadtime, temperature = getdata(file)
            ardn_time_min = Ardn_time_ms / 60000.0
            parsed_data[i] = {
                "event_number": event_number,
                "ardn_time_min": ardn_time_min,
                "adc": adc,
                "sipm": sipm,
                "deadtime": deadtime,
                "temperature": temperature
            }

        label_inputs = [st.text_input(f"Label for {labels[i]}", value=labels[i]) for i in range(3)]
        color_inputs = [st.color_picker(f"Color for {labels[i]}", value=default_colors[i]) for i in range(3)]

        # ---- Graph: Number of Events Per Minute ----
        fig_time = go.Figure()
        for i in range(3):
            time = parsed_data[i]["ardn_time_min"]
            fig_time.add_trace(go.Histogram(
                x=time,
                name=label_inputs[i],
                marker_color=color_inputs[i],
                opacity=0.7,
                xbins=dict(size=1.0)
            ))
        fig_time.update_layout(title="Event Count per Minute",
                               xaxis_title="Time [minutes]",
                               yaxis_title="Number of Events",
                               barmode="overlay",
                               width=800,
                               height=500)
        st.plotly_chart(fig_time, use_container_width=True)

        # ---- Graph: SiPM Peak Voltages vs Detection Rate ----
        fig_peak = go.Figure()
        for i in range(3):
            time = parsed_data[i]["ardn_time_min"]
            sipm = parsed_data[i]["sipm"]
            rate, peakV = [], []
            bin_size = 0.25
            curr_time = time[0]
            start_index = 0
            peak = 0
            for j in range(1, len(time)):
                if time[j] - curr_time >= bin_size:
                    peak = max(sipm[peak:(j+1)])
                    duration = time[j] - curr_time
                    r = (j - start_index) / (duration * 60)
                    rate.append(r)
                    peakV.append(peak)
                    curr_time = time[j]
                    start_index = j
                    peak = j
            fig_peak.add_trace(go.Histogram(
                x=peakV,
                y=rate,
                name=label_inputs[i],
                marker_color=color_inputs[i],
                histfunc="sum",
                opacity=0.7,
                xbins=dict(size=10)
            ))
        fig_peak.update_layout(title="SiPM Peak Voltages vs Detection Rate",
                               xaxis_title="Calculated SiPM peak voltage [mV]",
                               yaxis_title="Rate/bin [s⁻¹]",
                               barmode="overlay",
                               width=800,
                               height=500)
        st.plotly_chart(fig_peak, use_container_width=True)

        # ---- Graph: Dark Count Rate vs Temperature ----
        fig_dark = go.Figure()
        thresholds = [float(st.text_input(f"Threshold (mV) for dark counts ({label_inputs[i]}):", value="90")) for i in range(3)]

        for i in range(3):
            time = parsed_data[i]["ardn_time_min"]
            sipm = parsed_data[i]["sipm"]
            temp = parsed_data[i]["temperature"]
            dark_rates = []
            dark_temps = []
            curr_time = time[0]
            start_index = 0
            for j in range(1, len(time)):
                if time[j] - curr_time >= 1:
                    peak = max(sipm[start_index:j+1])
                    avg_temp = np.mean(temp[start_index:j+1])
                    duration = time[j] - curr_time
                    r = (j - start_index) / (duration * 60)
                    if peak < thresholds[i]:
                        dark_rates.append(r)
                        dark_temps.append(avg_temp)
                    curr_time = time[j]
                    start_index = j
            fig_dark.add_trace(go.Scatter(
                x=dark_temps,
                y=dark_rates,
                mode="markers",
                name=label_inputs[i],
                marker=dict(color=color_inputs[i], size=6)
            ))
        fig_dark.update_layout(title="Dark Count Rate vs Temperature",
                               xaxis_title="Temperature [°C]",
                               yaxis_title="Dark Rate [Hz]",
                               width=800,
                               height=500)
        st.plotly_chart(fig_dark, use_container_width=True)

        # ---- Graph: SiPM Voltage vs Time + Trendline ----
        fig_trend = go.Figure()
        trend_colors = ["#555555", "#888888", "#AAAAAA"]
        for i in range(3):
            time = parsed_data[i]["ardn_time_min"]
            sipm = parsed_data[i]["sipm"]
            coeffs = np.polyfit(time, sipm, deg=1)
            poly = np.poly1d(coeffs)
            trend_y = poly(time)
            fig_trend.add_trace(go.Scatter(x=time, y=sipm, mode="lines", name=label_inputs[i],
                                           line=dict(color=color_inputs[i])))
            fig_trend.add_trace(go.Scatter(x=time, y=trend_y, mode="lines", name=f"{label_inputs[i]} Trend",
                                           line=dict(color=trend_colors[i], dash="dot")))
        fig_trend.update_layout(title="SiPM Voltage Over Time",
                                xaxis_title="Time Elapsed (min)",
                                yaxis_title="SiPM Voltage (mV)",
                                width=800,
                                height=500)
        st.plotly_chart(fig_trend, use_container_width=True)
