# Autonomic Flexibility Analyzer

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![Flask](https://img.shields.io/badge/flask-3.0-green.svg)
![License](https://img.shields.io/badge/license-Personal%20Use-orange.svg)
![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)

> Quantify your autonomic nervous system's ability to shift from chaos to coherence using HRV analysis

The **Autonomic Flexibility Analyzer** is a Flask-based web application designed to evaluate the functional state of the Autonomic Nervous System (ANS). Unlike standard HRV trackers that offer static snapshots, this tool utilizes a **Multi-State Logic Model** to compare resting baseline data against entrained (resonant breathing) data.

This approach quantifies **Autonomic Flexibility**: the system's capacity to transition from a chaotic resting state to a highly organized, high-amplitude resonant state.

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

## 📱 How to Use the Web Application

### **1. Access the Dashboard**

Once the container is running, navigate to http://localhost:5000. You will see the upload interface and your session history.

### **2. Uploading Data**

The analyzer supports two workflow modes:

* **Dual File Mode:** Select your Baseline CSV in the first slot and your Entrained (Breathing) CSV in the second slot.
* **Single File Mode (Auto-Split):** If you recorded both sessions in one continuous file with a short break (10–30s) in between, simply upload the **same file** to both the Baseline and Entrained inputs. The app will detect the gap and split the data for you.

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

## 📊 The 12-State Interpretation Model

The system categorizes results across three Tiers based on **Baseline Alpha-1**:

| Tier | Baseline α1 | Characterization |
|------|-------------|------------------|
| **Tier III** | **> 1.25** | **High Structure:** High initial focus or systemic rigidity. |
| **Tier II** | **0.75 - 1.25** | **Available:** Optimal baseline for adaptation. |
| **Tier I** | **< 0.75** | **Low Structure:** Chaotic, depleted, or stressed baseline. |

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

## 💡 About This Tool

This is a **personal research tool** shared for transparency and to help others interested in HRV analysis.

- ✅ Free for personal use
- ✅ Open for feedback and scientific discussion
- ⚠️ Designed only for private use. Not designed for public use
- ❗ Not a medical device, and not intended to diagnose or treat any medical condition

If you use this in research, please cite this repository.

---

## 📄 License & Disclaimer

**License:** Free for personal use. Commercial use is strictly prohibited without prior authorization.

**Medical Disclaimer:** This tool is for educational and research purposes only. It is NOT:
- A medical diagnostic device
- A substitute for professional medical advice
- FDA approved or clinically validated

Always consult healthcare professionals for medical decisions.

**Citation:** If you use this tool in research, please cite:
```
Mahoney, R. (2025). Autonomic Flexibility Analyzer: Multi-State HRV Analysis Tool. 
GitHub. https://github.com/mahoneyr/HRV-flexibility
```

---

## 📚 Related Resources

**Scientific Background:**
- [Heart Rate Variability Analysis](https://pubmed.ncbi.nlm.nih.gov/8737210/) - Task Force guidelines
- [DFA in Exercise Science](https://pubmed.ncbi.nlm.nih.gov/31498541/) - Gronwald et al., 2019
- [HRV and Autonomic Function](https://pubmed.ncbi.nlm.nih.gov/17201590/) - Thayer et al., 2007

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

Built for physiological resilience and autonomic insight.
