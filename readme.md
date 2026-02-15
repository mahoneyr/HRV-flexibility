# **Autonomic Flexibility Analyzer**

The **Autonomic Flexibility Analyzer** is a Flask-based web application designed to evaluate the functional state of the Autonomic Nervous System (ANS). Unlike standard HRV trackers that offer static snapshots, this tool utilizes a **Multi-State Logic Model** to compare resting baseline data against entrained (resonant breathing) data.

This approach quantifies **Autonomic Flexibility**: the system's capacity to transition from a chaotic resting state to a highly organized, high-amplitude resonant state.

## **🧬 Scientific Foundations**

The analyzer evaluates the ANS through two primary physiological lenses:

### **1\. Integration (Signal Structure) via DFA Alpha-1**

Detrended Fluctuation Analysis (DFA Alpha-1) measures the fractal scaling properties of heart rate intervals.

* **Fractal Complexity:** A healthy resting system should exhibit pink noise, representing a balance between predictability and randomness.  
* **Autonomic Integration:** During resonant breathing, the system should shift toward a higher-order, "correlated" state, indicating successful neural integration and synchronization between the heart and the breath.  
* **States of Rigidity:** Values significantly above 1.25 at rest may indicate "Systemic Rigidity," where the system is locked into a high-focus or high-stress attractor state.

### **2\. Dynamics (Vagal Volume) via RMSSD & Vagal Gain**

While Alpha-1 measures *order*, RMSSD (Root Mean Square of Successive Differences) measures *power*.

* **Vagal Outflow:** RMSSD is the primary time-domain index of parasympathetic activity mediated by the vagus nerve.  
* **Vagal Gain:** This application calculates the ratio of **Entrained RMSSD / Baseline RMSSD**. A target gain of **\> 1.5x** indicates a robust "Baroreflex" response, where the physical mechanics of breathing successfully recruit parasympathetic resources.

## **🚀 Key Features**

* **Integration & Dynamics Framework:** A 12-state logic model that classifies physiological states based on baseline organization and the system's "shift capacity."  
* **FFT-Based Respiratory Detection:** Automatically estimates your breathing frequency (EDR) using Fast Fourier Transform logic to identify "Speed Limit" violations (breathing \> 5.7 bpm).  
* **Historical Benchmarking:** Calculates your personal historical mean and standard deviation (±1 SD), providing context for today's session within your unique "Normal Range."  
* **Intelligent Data Handling:** \* **Auto-Splitter:** Automatically detects transitions (\> 10s pause) to separate baseline and entrained segments from a single file.  
  * **MAD Artifact Filter:** Uses Median Absolute Deviation to remove ectopic beats while preserving the large physiological swings of resonant breathing.  
* **State-Driven Insights:** Managed via states.json, providing clinical implications and actionable goals.

## **📱 How to Use the Web Application**

### **1\. Access the Dashboard**

Once the container is running, navigate to http://localhost:5000. You will see the upload interface and your session history.

### **2\. Uploading Data**

The analyzer supports two workflow modes:

* **Dual File Mode:** Select your 5-minute Baseline CSV in the first slot and your 5-minute Entrained (Breathing) CSV in the second slot.  
* **Single File Mode (Auto-Split):** If you recorded both sessions in one continuous file with a short break (10–30s) in between, simply upload the **same file** to both the Baseline and Entrained inputs. The app will detect the gap and split the data for you.

### **3\. Reviewing the Results**

After clicking **Analyze**, you will be redirected to the Analysis Report:

* **The Interpretation Card:** Provides a summary of your physiological state and suggested "Next Steps."  
* **Primary Scores:** Check your **Coherence Index** (Target \> 1.2) and **Vagal Gain** (Target \> 1.5x).  
* **Detailed Graphs:** Bar charts show your current performance against **Black Error Bars** (Historical Mean ± 1 SD).

## **📂 Data Acquisition Guide**

To analyze your autonomic flexibility, you need raw RR interval data exported in CSV format.

### **Recommended Apps**

* **Camera Heart Rate Variability (Highly Recommended):** Available at [hrv.tools](https://www.hrv.tools/). This app allows for high-quality RR interval capture using your phone's camera and provides easy CSV export.  
* **HRV Logger:** Use with a chest strap. Ensure "Write to Apple Health" is **OFF** to keep experimental data separate from your fitness history.  
* **Elite HRV:** Use "Open Reading" mode and export the raw RR intervals.

### **Recommended Hardware**

* **Polar H10 Chest Strap:** The gold standard for mobile RR interval accuracy.

### **Testing Protocol**

1. **Baseline**: Sit quietly for 5 minutes.  
2. **Break**: Stand up or move for 30–60 seconds (creates the required time gap for the auto-splitter).  
3. **Entrained**: Perform resonant breathing (e.g., 5.5 to 6 breaths per minute) for 5 minutes.

## **📊 The 12-State Interpretation Model**

The system categorizes results across three Tiers based on **Baseline Alpha-1**:

| Tier | Baseline α1 | Characterization |
| :---- | :---- | :---- |
| **Tier III** | **\> 1.25** | **High Structure:** High initial focus or systemic rigidity. |
| **Tier II** | **0.75 \- 1.25** | **Available:** Optimal baseline for adaptation. |
| **Tier I** | **\< 0.75** | **Low Structure:** Chaotic, depleted, or stressed baseline. |

## **⚙️ Installation & Setup**

Running the analyzer via Docker is the recommended method.

### **1\. Clone the repository**

git clone \[https://github.com/mahoneyr/HRV-flexibility.git\](https://github.com/mahoneyr/HRV-flexibility.git)  
cd HRV-flexibility

### **2\. Build and Run with Docker**

\# Build the image  
docker build \-t hrv-flexibility .

\# Create a local data folder for persistence  
mkdir \-p data

\# Run the container  
docker run \-d \-p 5000:5000 \-v $(pwd)/data:/app/data \--name hrv-analyzer hrv-flexibility

## **📄 License & Disclaimer**

* **License:** Free for personal use. Commercial use is strictly prohibited without prior authorization.  
* **Medical Disclaimer:** This tool is for educational purposes only. It is not a medical diagnostic tool.

Built for physiological resilience and autonomic insight.
