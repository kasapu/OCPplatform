# 🪟 Windows Setup Guide - OCP Platform

## Quick Start for Windows

### ✅ Prerequisites

1. **Windows 10/11** (64-bit)
2. **Docker Desktop** for Windows
3. **WSL 2** (Windows Subsystem for Linux)

---

## Step 1: Install Docker Desktop

### Download Docker Desktop

1. Go to: https://www.docker.com/products/docker-desktop
2. Click **Download for Windows**
3. Run the installer: `Docker Desktop Installer.exe`
4. Follow the installation wizard

### Enable WSL 2

Docker Desktop requires WSL 2. If you don't have it:

1. Open **PowerShell as Administrator**
2. Run these commands:

```powershell
# Enable WSL
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

# Enable Virtual Machine Platform
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# Restart your computer
shutdown /r /t 0
```

3. After restart, download WSL 2 kernel update:
   - https://aka.ms/wsl2kernel

4. Install it and set WSL 2 as default:

```powershell
wsl --set-default-version 2
```

### Start Docker Desktop

1. Find **Docker Desktop** in Start Menu
2. Launch it
3. Wait for Docker to start (green icon in system tray)
4. You may need to accept the service agreement

---

## Step 2: Verify Docker is Working

Open **PowerShell** or **Command Prompt** and run:

```powershell
docker --version
docker-compose --version
docker info
```

You should see version numbers and system info.

---

## Step 3: Get the Project

### Option A: Clone from Git

```powershell
cd C:\Users\YourName\Documents
git clone <your-repo-url>
cd OCPplatform
```

### Option B: Download ZIP

1. Download the project ZIP
2. Extract to `C:\Users\YourName\Documents\OCPplatform`
3. Open folder in PowerShell:

```powershell
cd C:\Users\YourName\Documents\OCPplatform
```

---

## Step 4: Start the Platform

### Using the Windows Script (Easiest!)

Double-click: **`start-windows.bat`**

Or run in Command Prompt:

```cmd
start-windows.bat
```

### Or Use Docker Compose Directly

In PowerShell:

```powershell
# Copy environment file
copy .env.example .env

# Start infrastructure
docker-compose up -d postgres redis adminer

# Wait 30 seconds
Start-Sleep -Seconds 30

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

---

## Step 5: Access the Platform

Once started, open your browser:

👉 **http://localhost:3000**

You should see the chat widget!

Other URLs:
- API Docs: http://localhost:8000/docs
- NLU Docs: http://localhost:8001/docs
- Database UI: http://localhost:8080

---

## 🐛 Troubleshooting

### Problem 1: "Docker is not running"

**Error:**
```
error during connect: This error may indicate that the docker daemon is not running
```

**Solution:**
1. Open **Docker Desktop** from Start Menu
2. Wait for it to fully start (green whale icon in system tray)
3. Try again

### Problem 2: "Port already in use"

**Error:**
```
Bind for 0.0.0.0:3000 failed: port is already allocated
```

**Solution:**

Find what's using the port:
```powershell
netstat -ano | findstr :3000
```

Kill the process:
```powershell
taskkill /PID <PID> /F
```

Or change the port in `docker-compose.yml`:
```yaml
ports:
  - "3001:3000"  # Use port 3001 instead
```

### Problem 3: "WSL 2 installation is incomplete"

**Solution:**

1. Download WSL 2 kernel: https://aka.ms/wsl2kernel
2. Install it
3. Restart Docker Desktop

### Problem 4: "Virtualization is not enabled"

**Error:**
```
Hardware assisted virtualization and data execution protection must be enabled in the BIOS
```

**Solution:**

1. Restart your PC
2. Enter BIOS (usually press F2, F10, or Del during boot)
3. Find **Virtualization Technology** (Intel VT-x / AMD-V)
4. Enable it
5. Save and exit BIOS

### Problem 5: "Permission denied" or "Access denied"

**Solution:**

Run PowerShell or Command Prompt **as Administrator**:

1. Right-click PowerShell/CMD
2. Select "Run as administrator"
3. Navigate to project folder
4. Run commands again

### Problem 6: Services won't start

**Check logs:**
```powershell
docker-compose logs orchestrator
docker-compose logs nlu-service
docker-compose logs postgres
```

**Restart services:**
```powershell
docker-compose down
docker-compose up -d
```

**Clean restart (removes data!):**
```powershell
docker-compose down -v
docker-compose up -d
```

### Problem 7: "Network error" or "Cannot connect"

**Check Docker network:**
```powershell
docker network ls
docker network inspect ocplatform_ocp-network
```

**Recreate network:**
```powershell
docker-compose down
docker network prune
docker-compose up -d
```

### Problem 8: Chat widget shows "Connecting..." forever

**Wait 60 seconds** for services to fully start.

**Check service health:**
```powershell
# Check all containers are running
docker-compose ps

# Check orchestrator
curl http://localhost:8000/health

# Check chat-connector
curl http://localhost:8004/health
```

**View logs:**
```powershell
docker-compose logs chat-connector
docker-compose logs orchestrator
```

---

## 🎯 Common Windows-Specific Tips

### File Permissions

Windows doesn't have the same permissions as Linux. If you see permission errors:

1. Make sure Docker Desktop has access to your drive
2. Go to: Docker Desktop → Settings → Resources → File Sharing
3. Add your project folder location
4. Click "Apply & Restart"

### Line Endings

If you edit files on Windows, make sure they use LF (not CRLF):

In VS Code:
1. Click "CRLF" in bottom-right
2. Select "LF"
3. Save all files

Or use Git:
```powershell
git config --global core.autocrlf input
```

### PowerShell vs Command Prompt

Both work, but PowerShell is recommended. Use:
- **PowerShell 7** (recommended): https://github.com/PowerShell/PowerShell
- Windows PowerShell (built-in)
- Command Prompt (cmd.exe)

### Windows Defender / Antivirus

Sometimes Windows Defender slows down Docker.

Add exclusion:
1. Open Windows Security
2. Virus & threat protection → Manage settings
3. Add or remove exclusions → Add an exclusion
4. Folder → Select your project folder

---

## ✅ Verification Checklist

Before starting, verify:

- [ ] Windows 10/11 (64-bit)
- [ ] Virtualization enabled in BIOS
- [ ] WSL 2 installed and updated
- [ ] Docker Desktop installed
- [ ] Docker Desktop is running (green icon)
- [ ] Ports 3000, 8000, 8001, 8004, 5432, 6379, 8080 are free

Check with:
```powershell
# Check Docker
docker --version
docker-compose --version
docker info

# Check ports
netstat -ano | findstr ":3000 :8000 :8001 :8004 :5432 :6379 :8080"
```

---

## 🚀 Start the Platform

### Method 1: Batch File (Easiest)

```cmd
start-windows.bat
```

### Method 2: PowerShell

```powershell
# Navigate to project
cd C:\Users\YourName\Documents\OCPplatform

# Copy .env
copy .env.example .env

# Start everything
docker-compose up -d

# View logs
docker-compose logs -f
```

### Method 3: Manual Step-by-Step

```powershell
# 1. Start infrastructure
docker-compose up -d postgres redis

# 2. Wait for PostgreSQL
Start-Sleep -Seconds 30

# 3. Start services
docker-compose up -d

# 4. Check status
docker-compose ps
```

---

## 📱 Accessing from Other Devices

To access from your phone/tablet on the same network:

1. Find your PC's IP address:
```powershell
ipconfig
```

Look for "IPv4 Address" (e.g., 192.168.1.100)

2. Open on other device:
   - http://192.168.1.100:3000

3. Update CORS in `.env`:
```
CORS_ORIGINS=http://localhost:3000,http://192.168.1.100:3000
```

4. Restart services:
```powershell
docker-compose restart
```

---

## 🔧 Useful Windows Commands

```powershell
# View all containers
docker ps -a

# Stop all containers
docker-compose down

# Restart a service
docker-compose restart orchestrator

# View logs
docker-compose logs -f orchestrator

# Remove all data and start fresh
docker-compose down -v
docker system prune -a --volumes

# Check Docker disk usage
docker system df

# Free up space
docker system prune
```

---

## 📚 Additional Resources

- Docker Desktop Docs: https://docs.docker.com/desktop/windows/
- WSL 2 Guide: https://docs.microsoft.com/en-us/windows/wsl/
- Docker Compose Docs: https://docs.docker.com/compose/

---

## 🆘 Still Having Issues?

1. **Check Docker Desktop is running** (green whale icon)
2. **Restart Docker Desktop**
3. **Restart your computer**
4. **Run as Administrator**
5. **Check firewall/antivirus isn't blocking Docker**
6. **Check Windows updates are installed**

If still stuck, run diagnostic:
```powershell
# Save diagnostic info
docker-compose ps > diagnostic.txt
docker-compose logs >> diagnostic.txt
docker info >> diagnostic.txt
```

---

**Once everything is running, open: http://localhost:3000** 🚀
