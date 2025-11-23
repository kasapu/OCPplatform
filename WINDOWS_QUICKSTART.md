# 🚀 Windows Quick Start (5 Minutes)

## What You Need

1. **Windows 10/11** (64-bit)
2. **Docker Desktop** - [Download here](https://www.docker.com/products/docker-desktop)

---

## Step 1: Install Docker Desktop

1. Download Docker Desktop from: https://www.docker.com/products/docker-desktop
2. Run the installer
3. Follow the prompts (it will install WSL 2 automatically)
4. **Restart your computer** when prompted

---

## Step 2: Start Docker Desktop

1. Find **Docker Desktop** in your Start Menu
2. Click to open it
3. **Wait** for the Docker icon in your system tray to turn **green**
4. This means Docker is ready!

---

## Step 3: Get the Code

### Option A: Download ZIP
1. Download the project as a ZIP file
2. Extract it to: `C:\Users\YourName\Documents\OCPplatform`

### Option B: Git Clone
```cmd
cd C:\Users\YourName\Documents
git clone <your-repo-url>
cd OCPplatform
```

---

## Step 4: Run It!

### Easiest Way: Double-click the batch file

Just double-click: **`start-windows.bat`**

That's it! The script will:
- ✅ Check Docker is running
- ✅ Create configuration files
- ✅ Download and build everything
- ✅ Start all services
- ✅ Tell you when it's ready

### Alternative: Use Command Prompt

1. Open **Command Prompt** (or PowerShell)
2. Navigate to the project folder:
   ```cmd
   cd C:\Users\YourName\Documents\OCPplatform
   ```
3. Run:
   ```cmd
   start-windows.bat
   ```

---

## Step 5: Test It!

Once the script finishes (2-3 minutes on first run):

1. Open your browser
2. Go to: **http://localhost:3000**
3. You should see the chat widget!
4. Type "Hello" to start chatting

---

## 🎉 That's It!

Your OCP Platform is now running!

### Access Points:
- **Chat Widget**: http://localhost:3000 ← **Start here!**
- **API Docs**: http://localhost:8000/docs
- **Database UI**: http://localhost:8080 (username: `ocpuser`, password: `ocppassword`)

---

## 🛑 How to Stop

When you're done:

```cmd
docker-compose down
```

Or just close Docker Desktop.

---

## ❓ Troubleshooting

### "Docker Desktop is not running"
- Make sure Docker Desktop is open
- Wait for the green whale icon in your system tray
- Try the script again

### "Port already in use"
- Something else is using port 3000, 8000, or 5432
- Restart your computer to free up ports
- Or change the ports in `docker-compose.yml`

### "Build failed"
- Make sure you have internet connection (needs to download images)
- Check you have at least 10GB free disk space
- Try running as Administrator

### Services won't start
- Open Command Prompt as Administrator
- Navigate to the project folder
- Run: `docker-compose down -v` (this resets everything)
- Run: `start-windows.bat` again

---

## 📚 Need More Help?

See the full **WINDOWS_SETUP.md** guide for:
- Detailed installation instructions
- Complete troubleshooting guide
- Advanced configuration options
- Network access from other devices

---

## 🔧 Useful Commands

```cmd
# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Restart a specific service
docker-compose restart orchestrator

# Check service status
docker-compose ps

# Clean restart (removes all data!)
docker-compose down -v
docker-compose up -d
```

---

**Ready to Chat?** → http://localhost:3000 🚀
