# **Autonomic Flexibility Analyzer**

The **Autonomic Flexibility Analyzer** is a Flask-based web application designed to evaluate the functional state of the Autonomic Nervous System (ANS). Unlike standard HRV trackers that offer static snapshots, this tool utilizes a **Multi-State Logic Model** to compare resting baseline data against entrained (resonant breathing) data.

This approach quantifies **Autonomic Flexibility**: the system's capacity to transition from a chaotic resting state to a highly organized, high-amplitude resonant state.

## **🧬 Scientific Foundations**

The analyzer evaluates the ANS through two primary physiological lenses:

### **1\. Integration (Signal Structure) via DFA Alpha-1**

Detrended Fluctuation Analysis (DFA Alpha-1) measures the fractal scaling properties of heart rate intervals.

* **Fractal Complexity:** A healthy resting system should exhibit ![][image1] noise (![][image2]), representing a balance between predictability and randomness.  
* **Autonomic Integration:** During resonant breathing, the system should shift toward a higher-order, "correlated" state (![][image3]), indicating successful neural integration and synchronization between the heart and the breath.  
* **States of Rigidity:** Values significantly above 1.25 at rest may indicate "Systemic Rigidity," where the system is locked into a high-focus or high-stress attractor state.

### **2\. Dynamics (Vagal Volume) via RMSSD & Vagal Gain**

While Alpha-1 measures *order*, RMSSD (Root Mean Square of Successive Differences) measures *power*.

* **Vagal Outflow:** RMSSD is the primary time-domain index of parasympathetic activity mediated by the vagus nerve.  
* **Vagal Gain:** This application calculates the ratio of **Entrained RMSSD / Baseline RMSSD**. A target gain of **\>1.5x** indicates a robust "Baroreflex" response, where the physical mechanics of breathing successfully recruit parasympathetic resources.

## **🚀 Key Features**

* **Integration & Dynamics Framework:** A tiered logic model that classifies physiological states based on baseline organization and the system's "shift capacity."  
* **FFT-Based Respiratory Detection:** Automatically estimates your breathing frequency (EDR) using Fast Fourier Transform logic to identify "Speed Limit" violations (breathing \> 5.7 bpm).  
* **Historical Benchmarking:** Calculates your personal historical mean and standard deviation (![][image4] SD), providing context for today's session within your unique "Normal Range."  
* **Intelligent Data Handling:** \* **Auto-Splitter:** Automatically detects transitions (\>10s pause) to separate baseline and entrained segments from a single file.  
  * **MAD Artifact Filter:** Uses Median Absolute Deviation to remove ectopic beats while preserving the large physiological swings of resonant breathing.  
* **State-Driven Insights:** Managed via states.json, providing clinical implications and actionable goals for 12 distinct autonomic states.

## **📊 The 12-State Interpretation Model**

The system categorizes results across three Tiers based on **Baseline Alpha-1**:

| Tier | Baseline α1​ | Characterization |
| :---- | :---- | :---- |
| **Tier III** | **![][image5]** | **High Structure:** High initial focus or systemic rigidity. |
| **Tier II** | **![][image6]** | **Available:** Optimal baseline for adaptation. |
| **Tier I** | **![][image7]** | **Low Structure:** Chaotic, depleted, or stressed baseline. |

**Success Criteria:**

* **Coherence Ratio:** (Entrained ![][image8] / Baseline ![][image8]) ![][image9].  
* **Vagal Gain:** (Entrained RMSSD / Baseline RMSSD) ![][image10].

## **⚙️ Installation & Setup**

Running the analyzer via Docker is the recommended method to ensure all mathematical and plotting dependencies are correctly configured.

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

Access the application at http://localhost:5000.

## **📂 Directory Structure**

HRV-flexibility/  
├── app.py           \# Flask backend & Signal processing logic  
├── templates/       \# UI Templates (Bootstrap 5\)  
├── data/  
│   ├── states.json  \# Clinical interpretations & logic mapping  
│   └── history.csv  \# Persisted session database  
└── static/          \# Generated session visualizations

## **📄 License & Disclaimer**

* **License:** Free for personal use. Commercial use is strictly prohibited without prior authorization.  
* **Medical Disclaimer:** This tool is for educational and self-optimization purposes only. It is not a medical diagnostic tool. Results represent a **Current Snapshot** of autonomic activity and are subject to rapid change based on environmental and psychological factors.

Built for physiological resilience and autonomic insight.

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB8AAAAYCAYAAAACqyaBAAACFklEQVR4Xu2Wv0sbYRjHL+hQUZFCYzC55C4JGISWTg5qwcUWF8FR6FxKM5WOugRBELdWakEE6eDW/0Bx6aadCi5uhXR0EZdSJP08ubvy5knv7r1INz/w5U2e57nneX8898Nx7rkDhUJhlCGn7f+darVa8H3/veu6I9pnIhMsl8svarXatBM3UT9gTdvjkFjP85rabsIECfG+ViqVbcafjM//OjHMSAJ0im5J+Nm4Nolh4nfleu0wIV9LiqMt1OlZnFyMYZVxHrVti8t1rOITP4e1LwL/Q+LO0UGxWHzELjzFPKTjJNkU+pGheDPtiGSC6Aq9074eshSXBpPVoKr2CeR4EOZ76QVHKb0xlc/nx3RslyzFiZtDO05M57LdC/j30Tf0Cx3Jfzp+Vsd2yVh8g7hlbddILmLP5ey1rwfb4pJIYqSBtM+k0WiMe0GXf3ESmrJLhuJLxLS0XVMqlVzytdG69vVhWTxHzA6a0w4Nk3xG3G/GFe3rw6Y4XV4i2WFs1xqQ5zX5rsN7O5moODpyYro4vGUSH6cRxH1AF4m9IWcYns0t6oS6odB3VvrECJXH6Udul8eG7Z/Ii4TYE8+m2WxgkjWS7ToWyaJmk63XvoGg+CvZdm03yOF/S9FjP3hXtG12KZW0x6lQr9cnmeClF7xI9tJeOtbICki46cQ0Yois/A06k+Phw2FCBwyEfIWQdFHb7xmEPx7VhejiqTrjAAAAAElFTkSuQmCC>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEcAAAAYCAYAAACoaOA9AAADX0lEQVR4Xu2Xz4tNYRjH73QpIj/iutxfZ+6dQbOwulI0IlEmKU1TaGRBIpGiadSMhfAHGLuJmSw0YWKhmJWVhdgYSWLB1ESzkBILxhif75xz7rzz3h/mXD8yOt/6dt7zPM/763uf93nPjURChAgRIkRg1LrYY9srob6+fkEmkznhOE43PANX2DEzFmymAR6F9+EY4ly1Y8ohm83SxRlEnEP0m0O7ifZL7Ovs2BkJicPGdvHcAIcDiDOL+MuwX23fyPsFBBpIpVJzjdi/h3w+P7uurm6ZnrbPhOeP2vZS0HGAQ9MVBwFyxL/j2W7asTXDz9jzpr0A0iqOcycTbVa62f5fQI3jHoGvcByOwS6deztQYA37tWnbXgpViLOV+O+2ONq3t7ZW066CthxjP7ytwsazAw6n0+m18pNqSbhySqcAYOJtjNeTTCaX6D0ej89jntOag+feiJElqgfaaC6XW1gYoAKqEGdChHLiTLF7xekZ7DbSXeeyzz+DtDtpNxY6BQQLPyKBbTtipRj7FhzR5uB1CQZ32LHlUIU47UUiuPYicfzipAVlrWAN8pFJt9PuNX9J/fL4DuBbZPYpBy/rCsXPQg1jr2K8k8yzz8+u6SKoOJrHFkEoEsdxr8P3jlW5PV+r4xaoXibeLZsWjq0P3oHPtTCzTyUkEomlxJ+HTxjvIhm72o7xgX/TdEUKKk6RCOXsvoGBD5uBpk9C2Ncbvrw2OV1xvOPzGHbRt4VnJ3wLL5UoysrmDl0Olr0kqhCnkfjRcuLA5gkDjSYZ5DADBS/4m37FEr5A4kh8ivtG0ybBa92iPAIPSkAdP9rd2M8SUmPGl8PPxFE5YO5ExBtPtY/4N7DLjNMaHfcUNUwYSPU0L6/gMSNO1+4W+MLxhNPCdSz8gKDiEH8cLrbtgo4Xvl7HveY/wDY7UytBa4BD8FrEEtQrA4PwC1zvmbW/c/ChX0d1ESHODWx9EbO8OK4Qr+FNeEWd4CnSPcbzLp0esfgB3Wp+n6Di/Alk3O8VXST6Zhr3+In1PkXcNYqJxWLztYeM+9egsH6J4u1Nt6NOTw98oCSYnGESUX25ekXQVD+qjLG/aP8FcX4DotoHbNFT73ZAVfhPxPm9qHX/wbbBe3DUcb+qm+y4ECFChAgRDD8AoyYEB57IegQAAAAASUVORK5CYII=>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFAAAAAYCAYAAABtGnqsAAAD1UlEQVR4Xu1XbWiOURh+1jtFPouZvR87e99Naz989SqR0EKWxpKyLH+mKCllSTEh/skvfrAmUdoPKz8w+yFEabZitCEmTeIXSiZiXtf1Pvfh7Nhsz/O+VtNz1dXznPvc537Ouc59Ph7HCRAgQIAAYx5FLqpt+9+glCoAD4ANYF04HI6Z9QwI++ZIJBJFMYTi+Hg8Pq+wsHAb303fMQkMrgzcAd4A+zGoc7bPUIAIlWjTQkFKSkry8H4E/AJu0D54XwJ+BVMG+8C1ZqzRQqi0tHSybcwEGEgZRKuSgb4eqYDMHvhfBT+AC2iDoAm8vwW7kYkzxJZE+TH4FOxEu8N4FgyMNkqIRqMT8PHj4BXM+lyYcmwfv+CgwF6PAl5SbtauoI3LlJMAvkD/8mkTAU8MaDwc2JjpzcD/Yp2jo9PRqWPgHbAcppDt4xVeBSQ4NvbFkYlEeQ1i/AAbUcylzZOACDALzs2cGbxX47mfMxKLxRayHhkUAWfb7fwC+84UxK8H2/C99U4GQvoR0ASzD21vI0aHHBhpiIDM1PNgD8qvwINcTWZ7Zh3qVRfYkEwmx4k5F+UmNGiV5VeP96UDGmYB+fn5ExF3l3L3mto/OjcC+BWwuLh4pnJXApfufR4ojrG1UEDwHvpUwjIzFt9ot3RKC9UoQeLaSKDxXtg+Mr3xfjaRSEzVdRw4B4y6aWYbv5BJqvUjpF8BTaB9OfgZMQ5pcfjkOC2/fco9mRdrA68C78BmR9a+4VwD9lE8BN5Em+xhTeBlGWzWTiV2GN/agpg9+F6VXT8U2AeVoYC8ISg3G/vRh1V2vYYkVQrcrQ28D6Xw8e2W7686imVnhOwPndkQ0Mg+xvOUfYRXAbmSmGloU+MYS5btOV6KJInSAXZxqWsfLSCfaQMKFWKo1E4aIuB3BF4+SF3GAhr7Hw+SanNf8YLhBKRgOAzDjohlJEav7n9eXt4kvN+incmkYypLQOUu4RTirUsb+PsCw3Nwp3YCcpS7J/ACmRaXp5O+YBKZCJjtq4wx2AuOdb+Ubz1Uxr4lfX8PHtWTxoMC5TfgEzmJc+F3CmIu0rEkc3laXzfPA72BvgQvgmfANrBOfnFa0KgdwVp5Wus2fgSkL3gSvCkdy+gyjT6sVO7h169+/2p9QuxHEGQOfSSzWuD7zOg/E4S/gN3KzSju9Q+Uu/fO1/HldsJJ5mRvFZ+75lXHRIipal4utZ2ZZy8vrwLKXet0PMt/IZlAlvZqjGUjx+MMshI4bvR5GX0w1rLBfHzBq4ABBEXuf+Qe8Br4Tbl/LxW2X4AAAQIE+P/xE18oL3xcq3urAAAAAElFTkSuQmCC>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABkAAAAXCAYAAAD+4+QTAAAArklEQVR4XmNgGAVDBigoKAjIycmFApmM6HK4gLy8vKGsrKwbujhOANQgCbRooaioKA+6HDIAqjEHOqYMqP40EP8HssvR1eAEJFriC1TvBcRfaWIJDAANNx4BloiLi3MDJVYA8SNkDNTwDIh/AfETLHJN6ObgtQQXoKpPcIFRS+hiCRBXocsxyMjICAEV7MCSgvClrlqYfqBDMqBq/yPhd0B8WFlZWQzZrlEwCqgPAEdsXdz58iVBAAAAAElFTkSuQmCC>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAUCAYAAADLP76nAAAAr0lEQVR4Xu2VvQoCMRCEk87e6gjkx8buWp/BJxN7xUJ8AtuDKywOxAdzBlLtC9wN7AcDR3aLTDKbC8FxHGd1aq07yq7LkHM+lFI+MHFNKe1tXYXYWhthZIZeULMNMsDIEQbeFL9tXQbeAm8D0fpCJyxF2yMBTAzQXdoIhxvD/oCRH0xUW98s/fRv0CJ1+j3/T2ji6xRENi77lEbGgzHpcRlsw6bBhs8Y0IvyX9hZiz9XXyGWheDw7gAAAABJRU5ErkJggg==>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFEAAAAUCAYAAAD1GtHpAAACzElEQVR4Xu2XXYhNURTHzwlFyOd1m/t1zr03bkLkhpTkgTIPpChiMm88efbxpCblK0WhvPgoSvLgYZRMmceRJ+VSah4ozdPkBYU0fmvO3nfWbOeMaKJzO/9anXP+6793d/3P3uvs63kZMmTIkOEXlEqlOUEQHCRuEOer1WrD1cShUqkcI84yfjnjunTU6/VlSGaEYTgbzeFyubxa7oUrFosluCM8h86U6UStVltA0U+JvlwuN4+61nH/mtjral2gvY1uLCFahUJhKZqFGPY8Jn+x2WzOcudMJSjwOAW94LrIcjwfIt6wIvNaqyGGo+kn7gbRCh4P5rnFdSQwL0HpXhHDksfYTaR8Z8p0QowTA2VFaZ6ttwH+E9fdmtcIom17zWzRNnjeD3/BMyaZ1S0rtkvrOgYUtpIYdU3E3Cb8Z+KM5jXog4vJr9cc41bB3ZMWYbmON9GalWSiy08Fs20fmK06iYe7T+5SEG3pD8z/CC7UutSCYnZR1Jhr1t+YyJgeWYXcztS8mEjuiWxzL9riPro+uLf03EBrUwmK6Z4OE80Xfgj9UTcH/EajMV+uljA99wv60xOyyZAvt3zYpA38Luxxyp3jnyDJrCQ+Ceh2ip5xW9xcHFTPHcjn83PdvCCMjlrtr/5Ugfbyf2sPFFPjR4y4ZqkiT2k+CeiuiF7GuTnmPkfuO7kdllPzD8p21/rUwXwMBon+UB1VKHI73De5Wk62LNuw4DnnO1lJaAfkZchL0TmBvCByP7SJdjvD3fQ64bxIIT3Ee4qqGmq88RND9qjC37QlPL8kvhKb1XBP/pXAtYh3QcwxBhMPECe8CbN8nk+i/UjP26ik6YU0cEy8TlHPKG6PMbAlPclqzIp9XIn5oprmP5xkoswPf5V4yJy9XO8Qo0S3q007fFbdCkzahylb//Q/LQfvNYxb6yVvzfb8GLlNt44MGTJMB34CNo7UHac4kUsAAAAASUVORK5CYII=>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAUCAYAAADLP76nAAAAyUlEQVR4XmNgGAWjYBSMgiEFxMXFuY2NjVnRxQc9UFRUVJeXl18NxMtUVFRE0eUHK2BUUFAwBzp6PxBPkZKSkkVXMFgBM9DBTkB8GIi7paWlhdEVDFbADAxxf6CjTwBxDTCp8KErGJQAlCmBDo8AOvqcnJxcPiijoqsZ1ADocEcgfgD0RIaMjAwnuvyQAGixUDZkkg8WAMsHp4daBkYHKEUoEEuiKxgqgBFYiekBPbAdiOcCsSK6giEDQI4H4i5gRldBlxsFIxUAAOFbIu6MHE+QAAAAAElFTkSuQmCC>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABQAAAAYCAYAAAD6S912AAABUUlEQVR4Xu2Tuy8EURjFZ2MlREHiMWveL4V6lJsQlS22JtFpNDoRBX+JEKWCRCHBnyBbKUQkCo1WI1GR8PuYkTvXrCxRKOYkJ/Pd79xz5rvzMIwKFf4hwjA0Pc9rB0EwBwd0vWdgbvi+fwSPqZe4bsF713VnRHccx4ZTuq8UTIXXv4I7aZr2Z+066wOmPSdokHqbulkwdoEYd2UaGKoCAZv0Hpl4gXo/iqLhXDNNcwhtBW1E9Rg0p+GDHJdlXdOW4ZOEYVyUnm3bozI5PIHXcFL1yBRtmq8YVguCoolZjq1pKf3LL4E0WmISc0EwPgNfuNlsiVYeaFmWS/MWrintGut5eJPfjKM67B3LN3QNFGTmO3gI9+AFXE+SZJzrKRN25G3L15B7vg3M0BfH8YQ8dOqa2pfJlM/pHb0E/gh/Fii/IyEb8Aw++x9/V0vfV+H3eAPrUlRqEww96QAAAABJRU5ErkJggg==>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC0AAAAXCAYAAACf+8ZRAAAB+ElEQVR4Xu2VzysEYRjHZ1oHIoq2TftjdtaW9uIiXB047GFLKQd7lJuTA0cHSQ4UkSIHSpRyUnugCP+Ci5wUBwc3chGfx74zpteuNbt70nzr287z632++8y872sYAQIE8ItQIpEYSwI9UA6xWKzJsqxxuAXXqB/CHdLz6gppSqMcOldp+gBfsHv1vFJIpVJt5B+TPxmPx7v4ncN+hwWJuYks3ij01NYENaksaw6qpn8WTe4U3Eun063KZWLPww/WmHUTMVI4T2myFI1GO9xAHSCN/IhGw64IhNOOj4n3Yb/Cs0gk0uzNN23b7pHXAHeg7Q1WiypEj5B/Q/6w45NaWQNehMPhFm++C8R3k3AklGc97gd+RZcC9Xk1/WU99gMybZk6//4SDuAy9ZxKqFW0bD7pT/0tA7T0eFnQtBNuVCO+RtEmdTPU38GMHqwI2aAssEnxNcKTerwcahFN3Si88tPvC2rK6/Dc75QF1YpWggscn+1iywbEzid/O5qt4ve8DU/kVDF8inVQQXRIpqgLoV8/NfveywQ7Q96qUUJH3Y89JfpVzlo9hn/CKp4KB5gNypexit/wE7X3DrGf4YK33pRXj/PcKn4Knd6gX8gFQKND1UhEOXyEK04eOTnsN9lshppg8vtyKcW82wQjS+FivW/DAAEC/GN8AufUlNENIdXbAAAAAElFTkSuQmCC>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC0AAAAXCAYAAACf+8ZRAAACEUlEQVR4Xu2Vv0scQRTHZ7kEFBMIhOOQ+7G3W7iNpFnU9hoLCzsxqZIikD9Bk0rBIgSCIEQsRDQ2KmIhKBIiGEKa9KkCKU2XpFKEIObz2B3dG1fcWU9IsV/4sjfvfd+8783OzihVoEABW5QajcZ4E5iJNCDrQv+0Xq/3y29CpWq1WiP2IuscuVCr1bppMkqPOdd1D+ER49DUpYGaB2i/UnNm8G0YhneTwq74X3UEYpomI8zZwsCUjelyuXwP/S78Bn9Qt8I8Q6ScNiEJH8FHkm94FQ/bkjcEc0/amsbHe2p6zVwaHM/zHiHeg0vQMwV5cNumz4H5gKJNofw28zbIaXqDmtl4ixxSu535I5TVllVH/zl1X2VAHtNoP9DvsYr6OdTPEPvOArqm/krIq4LzeczbmgZOEAT35akDHH8DzHFM7+kLWQbIB0rjBYq/ZH5VKpfpS5BamQPuVyqVHjN/CfEqv4MHtqsssDUtJxj6v+iHdSxh+pNsn6S+DW60nxfhjpwqytKsxjWmS/LWmok7ohmdHKdJ03p7EFtWKT4cMeh28NiLTR9LYzNH/Lkb3XZrDO9IDNNP4Et1Yc5h/ArNH7wN6lqdGCJx4EZbwe6MNCD7DrPrzPM7NqX5E85qHZpRxic8J1RsUq5qYvNwC0/PeK7CX3DkvIFAAhS+7vRteAM4vu/34WkM463k9ilQoMB/gn/UU5OSvQrF8gAAAABJRU5ErkJggg==>
