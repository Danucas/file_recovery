## File Recovery tool

Restore deleted files from your disks

### Requirements
- Git [Install](https://www.git-scm.com/downloads)
- Python [Downloads](https://www.python.org/downloads/)
- Pip It comes with Python
- Windows OS

Clone the repo and install dependencies

Use the PowerShell

```powershell
pip install -r requirements.txt
```

Run the application as administrator

```powershell
start-process -filepath python -verb runas -argumentlist app.py
```
Open the [File Recovery WebApp](http://127.0.0.1:5000)
