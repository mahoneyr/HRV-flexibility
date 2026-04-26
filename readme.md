# Autonomic Flexibility Analyzer

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![Flask](https://img.shields.io/badge/flask-3.0-green.svg)
![License](https://img.shields.io/badge/license-GPL%20v3-blue.svg)
![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)

> Quantify your autonomic nervous system's ability to shift from chaos to coherence using HRV analysis

The **Autonomic Flexibility Analyzer** is a Flask-based web application designed to evaluate the functional state of the Autonomic Nervous System (ANS). Unlike standard HRV trackers that offer static snapshots, this tool utilizes a **Multi-State Logic Model** to compare resting baseline data against entrained (resonant breathing) data.

This approach quantifies **Autonomic Flexibility**: the system's capacity to transition from a chaotic resting state to a highly organized, high-amplitude resonant state.

---

## ⚠️ Disclaimer

**This project is for educational and research purposes only.** It is **not intended for medical diagnosis, treatment, or any clinical use**. Heart rate variability analysis provided by this tool should not be used as a substitute for professional medical advice. 

Always consult with a qualified healthcare provider regarding any health concerns or before making health-related decisions based on HRV data.

This tool does not provide medical diagnostics and should not be used to make medical decisions.

---

## 🎯 Why This Tool?

Standard HRV apps show you a single number (RMSSD or SDNN) from one state. But autonomic function isn't about a single snapshot—it's about **flexibility**: your system's capacity to shift states.

This analyzer:
- ✅ Compares resting vs. entrained states
- ✅ Quantifies shift capacity (coherence & vagal gain)
- ✅ Classifies into 12 physiological patterns
- ✅ Tracks your progress over time with personal benchmarks

Think of it as **stress-testing** your nervous system, not just measuring it at rest.

---

## ⚡ Quick Start

```bash
# Clone and run in 3 commands
git clone https://github.com/mahoneyr/HRV-flexibility.git
cd HRV-flexibility
docker build -t hrv-flexibility .

# Run the container
docker run -d -p 5000:5000 -v $(pwd)/data:/app/data --name hrv-analyzer hrv-flexibility
```

Then visit **http://localhost:5000** and upload your HRV data!

---

## 🧬 Scientific Foundations

The analyzer evaluates the ANS through two primary physiological lenses:

### **1. Integration (Signal Structure) via DFA Alpha-1**

Detrended Fluctuation Analysis (DFA Alpha-1) measures the fractal scaling properties of heart rate intervals.

* **Fractal Complexity:** A healthy resting system should exhibit pink noise, representing a balance between predictability and randomness.
* **Autonomic Integration:** During resonant breathing, the system should shift toward a higher-order, "correlated" state, indicating successful neural integration and synchronization between the heart and the breath.
* **States of Rigidity:** Values significantly above 1.25 at rest may indicate "Systemic Rigidity," where the system is locked into a high-focus or high-stress attractor state.

### **2. Dynamics (Vagal Volume) via RMSSD & Vagal Gain**

While Alpha-1 measures *order*, RMSSD (Root Mean Square of Successive Differences) measures *power*.

* **Vagal Outflow:** RMSSD is the primary time-domain index of parasympathetic activity mediated by the vagus nerve.
* **Vagal Gain:** This application calculates the ratio of **Entrained RMSSD / Baseline RMSSD**. A target gain of **> 1.5x** indicates a robust "Baroreflex" response, where the physical mechanics of breathing successfully recruit parasympathetic resources.

---

## 🚀 Key Features

* **Integration & Dynamics Framework:** A 12-state logic model that classifies physiological states based on baseline organization and the system's "shift capacity."
* **Historical Benchmarking:** Calculates your personal historical mean and standard deviation (±1 SD), providing context for today's session within your unique "Normal Range."
* **Intelligent Data Handling:**
  * **Auto-Splitter:** Automatically detects transitions (> 10s pause) to separate baseline and entrained segments from a single file.
  * **MAD Artifact Filter:** Uses Median Absolute Deviation to remove ectopic beats while preserving the large physiological swings of resonant breathing.
* **State-Driven Insights:** Managed via states.json, providing clinical implications and actionable goals.

---

## 📊 The 12-State Interpretation Model

The system uses a **two-dimensional classification framework**:
- **Integration (Structure):** Measured by DFA Alpha-1 at baseline
- **Dynamics (Range):** Measured by how much your system shifts during breathing

### **The Three-Tier Framework**

| Tier | Baseline α1 | Interpretation |
|------|-------------|----------------|
| **Tier III** | **> 1.25** | **High Structure:** Already organized at rest—either focused or rigid |
| **Tier II** | **0.75 - 1.25** | **Available:** Balanced baseline with room to adapt |
| **Tier I** | **< 0.75** | **Low Structure:** Chaotic or depleted at baseline |

---

### **The 12 Physiological States**

Your session gets classified into one of these states based on **how your system responds** to breathing:

#### **🟢 Tier III States: High Baseline Structure (α1 > 1.25)**

| State | Trigger Conditions | What It Means | Next Step |
|-------|-------------------|---------------|-----------|
| **🎯 Laser Focus** | Vagal Gain > 1.5x | Peak performance state. High focus + massive vagal response. | Capitalize on this window for high-demand tasks. |
| **⚡ Attentive** | Entrained α1 > 1.35 | Alert and organized, but holding tension. May feel "wired." | Soften physical tension—drop shoulders, relax jaw. |
| **🔒 Stuck** | Poor Coherence Response | Rigid system resisting the breath. Trying too hard. | Break the pattern with movement before trying again. |

#### **🟡 Tier II States: Available Baseline (0.75 ≤ α1 ≤ 1.25)**

| State | Trigger Conditions | What It Means | Next Step |
|-------|-------------------|---------------|-----------|
| **✨ Feeling the Flow** | Coherence > 1.2 + Vagal Gain > 1.5x + α1 > 1.35 | **OPTIMAL STATE.** Deep recovery and high function. | Maintain exactly what you're doing. |
| **🌿 Fragile Calm** | Coherence > 1.2 + Low Vagal Gain + α1 > 1.35 | Calm timing but shallow breathing. | Try slightly fuller inhalations to recruit more vagal tone. |
| **🟢 Open for Business** | Coherence > 1.2 + α1 > 1.35 (other) | Steady and balanced. Not pushing limits. | Extend exhalation if you want deeper recovery. |
| **⚔️ Tug of War** | Vagal Gain > 1.5x + α1 < 1.35 | Body generating energy but pattern is messy. | Allow the turbulence—relax abdomen, don't force. |
| **🔥 Burned Out** | α1 < 1.35 + Low Vagal Gain | System deteriorated during session—perceived as stress. | Stop. You need rest, not more training. |

#### **🔴 Tier I States: Low Baseline Structure (α1 < 0.75)**

| State | Trigger Conditions | What It Means | Next Step |
|-------|-------------------|---------------|-----------|
| **🏃 Relying on Reserves** | Coherence Ratio ≥ 1.2 | Starting depleted but forcing alignment through effort. | Acute recovery: prioritize rest after this session. |
| **⚠️ Running Low** | Vagal Gain > 1.5x + α1 < 1.35 | Body is working, mind is tired. Hard to find rhythm. | Reduce session length or slow breathing rate. |
| **❌ Running on Fumes** | Poor response across all metrics | Internal battery critically low. System can't rebound. | Stop training. Focus on sleep, hydration, nutrition. |

---

### **Special Cases**

| State | Condition | Meaning |
|-------|-----------|---------|
| **🌊 Surfing the Wave** | Baseline RMSSD already very high | Started with excellent vagal tone—"low gain" is data artifact, not failure. |
| **❓ Unknown** | Invalid data or sensor error | Check connection and data quality. |

---

### **Understanding the Logic**

The classification uses **three key metrics**:

1. **Coherence Index** = Entrained α1 / Baseline α1  
   → Target: **> 1.2** (20% improvement in structure)

2. **Vagal Gain** = Entrained RMSSD / Baseline RMSSD  
   → Target: **> 1.5x** (50% increase in vagal power)

3. **Entrained α1**  
   → Target: **> 1.35** (highly organized pattern)

**Your state depends on which targets you hit and where you started.**

---

### **Quick Reference: What Do I Need?**

| To Achieve | You Need |
|-----------|----------|
| **Optimal Recovery** (Feeling the Flow) | Balanced baseline (0.75-1.25) + hit all 3 targets |
| **High Performance** (Laser Focus) | High baseline (>1.25) + high vagal gain |
| **Avoid Training** (Running on Fumes, Burned Out) | When starting depleted and getting poor response |

---

## 📋 Input Data Format

The analyzer requires **CSV files** with raw RR interval data. Here's what you need to know:

### **CSV Requirements**
- **Column name:** Must have a column labeled `RR` (case-insensitive)
- **Values:** RR intervals in **milliseconds** (typical range: 300–2000ms)
- **Minimum data:** 30 heartbeats per session (1–2 minutes of data)
- **No header required** but recommended for clarity

### **Example CSV Format**
```
RR
850
820
875
900
...
```

### **Upload Your Files**
Upload **two separate CSV files:**
1. **Baseline file:** RR intervals from your resting session
2. **Entrained file:** RR intervals from your resonant breathing session

**Optional:** If you recorded both sessions in one continuous file with a 10–30s pause between them, you can upload the same file twice and the app will auto-detect and split it.

---

## 📱 How to Use the Web Application

### **1. Access the Dashboard**

Once the container is running, navigate to http://localhost:5000. You will see the upload interface and your session history.

### **2. Uploading Data**

Upload your two CSV files:
* **Baseline file:** Your resting RR intervals (CSV with RR column)
* **Entrained file:** Your breathing RR intervals (CSV with RR column)

**Alternative:** If both sessions are in one file, you can upload it twice and the app will auto-detect the gap between them.

### **3. Reviewing the Results**

After clicking **Analyze**, you will be redirected to the Analysis Report:

* **The Interpretation Card:** Provides a summary of your physiological state and suggested "Next Steps."
* **Primary Scores:** Check your **Coherence Index** (Target > 1.2) and **Vagal Gain** (Target > 1.5x).
* **Detailed Graphs:** Bar charts show your current performance against **Black Error Bars** (Historical Mean ± 1 SD).

---

## 📂 Data Acquisition Guide

To analyze your autonomic flexibility, you need raw RR interval data exported in CSV format.

### **Recommended Apps**

* **Camera Heart Rate Variability (Highly Recommended):** Available at [hrv.tools](https://www.hrv.tools/). This app allows for high-quality RR interval capture using your phone's camera and provides easy CSV export.
* **HRV Logger:** Use with a chest strap.
* **Elite HRV:** Use "Open Reading" mode and export the raw RR intervals.

### **Recommended Hardware**

* **Polar H10 Chest Strap:** The gold standard for mobile RR interval accuracy. Not needed for Camera HRV.

### **Testing Protocol**

1. **Baseline**: Sit quietly and breathe shallowly but regularly. One minute is a minimum but longer sessions give better results.
2. **Entrained**: Perform resonant deep breathing (e.g., 6 breaths per minute) for at least one minute. Breathe deeply and regularly. Again, the longer the better.

---

## ⚙️ Installation & Setup

### **System Requirements**

- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- 2GB free disk space
- Chrome, Firefox, or Safari (any modern browser)

### **1. Clone the Repository**

```bash
git clone https://github.com/mahoneyr/HRV-flexibility.git
cd HRV-flexibility
```

### **2. Build and Run with Docker**

```bash
# Build the image
docker build -t hrv-flexibility .

# Create a local data folder for persistence
mkdir -p data

# Run the container
docker run -d -p 5000:5000 -v $(pwd)/data:/app/data --name hrv-analyzer hrv-flexibility
```

The application will be available at **http://localhost:5000**

### **3. Stopping the Container**

```bash
# Stop the container
docker stop hrv-analyzer

# Remove the container
docker rm hrv-analyzer
```

---

## 🔧 Troubleshooting

### **"Error processing files"**
- Ensure your CSV has an "RR" column with heart rate intervals
- Check that values are in milliseconds (300-2000 range)
- Verify at least 30-60 seconds of data (minimum 30 beats)

### **Docker container won't start**
- Ensure port 5000 isn't already in use: `lsof -i :5000` (Mac/Linux) or `netstat -ano | findstr :5000` (Windows)
- Check Docker is running: `docker ps`
- Check logs: `docker logs hrv-analyzer`

### **Auto-split not working**
- Ensure there's a 10+ second gap between baseline and breathing sessions
- Check that timestamps in your CSV are continuous
- Verify both files are identical (same file uploaded twice)

### **Graphs not showing**
- Check browser console for errors (F12)
- Ensure the `static/` directory has write permissions
- Try a different browser

### **Data looks wrong**
- Verify your CSV uses milliseconds, not seconds (values should be 300-2000)
- Check for missing data or large gaps in recording
- Review the artifact filter log messages

---

## ⚙️ Known Limitations

- **Minimum session length:** Baseline and entrained sessions should be at least 1 minute each (longer is better for accuracy)
- **RR interval range:** Values outside 300–2000ms are filtered as artifacts; extreme arrhythmias may not process correctly
- **Sampling rate:** Requires consistent RR interval capture; gaps >5 seconds may indicate recording issues
- **Auto-split accuracy:** Relies on >10 second pause to detect baseline/breathing transition; inconsistent pauses may fail to split
- **Historical benchmarking:** Requires multiple sessions to establish meaningful "Normal Range" (±1 SD)
- **Not FDA approved:** This tool has not undergone clinical validation and should not be used for medical diagnosis
- **Artifact filtering:** The MAD filter removes outliers but may miss some ectopic beats in highly irregular recordings
- **Data persistence:** Session data is stored locally; migrating Docker containers may lose history without proper volume setup

---

## 💡 About This Tool

This is an **open-source research tool** for exploring autonomic nervous system flexibility through HRV analysis.

- ✅ Open-source under GPL v3
- ✅ Free for personal and commercial use (with copyleft requirements)
- ✅ Open for feedback and scientific discussion
- ⚠️ Community-driven; contributions welcome
- ‼️ Not a medical device; for educational and research purposes only

*If you use this in research, please cite this repository.*

---

## 📄 License & Disclaimer

**License:** GNU General Public License v3 (GPL v3)

This project is licensed under GPL v3, meaning:
- ✅ You can use, modify, and distribute this software freely
- ✅ Any derivatives must also be open-source under GPL v3
- ✅ Commercial use is permitted, but modifications must be shared

See the LICENSE file for full details.

**Medical Disclaimer:** This tool is for educational and research purposes only. It is NOT:
- A medical diagnostic device
- A substitute for professional medical advice
- FDA approved or clinically validated

Always consult healthcare professionals for medical decisions.

**Citation:** If you use this tool in research, please cite:
```
Mahoney, R. (2026). Autonomic Flexibility Analyzer: Multi-State HRV Analysis Tool. 
GitHub. https://github.com/mahoneyr/HRV-flexibility
```

---

## 📚 Related Resources

**Learn More About HRV Science:**
- Search PubMed for "DFA alpha-1 heart rate variability"
- Search PubMed for "RMSSD parasympathetic nervous system"
- Search PubMed for "respiratory sinus arrhythmia"

**Similar Tools:**
- [HRV4Training](https://www.hrv4training.com/)
- [Elite HRV](https://elitehrv.com/)
- [Kubios HRV](https://www.kubios.com/)

---

## 🤝 Contributing

This is a personal research tool, but I welcome:
- 🐛 Bug reports
- 💡 Feature suggestions
- 🧬 Scientific feedback on the HRV algorithms

Open an issue to discuss!

---

*Built for physiological resilience and autonomic insight.*
