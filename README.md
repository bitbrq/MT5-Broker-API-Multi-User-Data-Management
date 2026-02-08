# MT5-Broker-API-Multi-User-Data-Management
A FastAPI-based broker API that fetches trading data from MetaTrader 5 and stores it in separate SQLite databases for each user. This modular system ensures data isolation while providing real-time market data updates.
# 📊 MT5 Broker API - Demo Data Platform

> **⚠️ Important Security Notice:** This repository contains **manipulated sample data** for demonstration purposes only. All user credentials, trading data, and financial information have been anonymized and modified. **You must install MetaTrader 5 and configure your own broker accounts** to use this system with real data.

## 🚨 Before You Begin

### **CRITICAL FIRST STEPS:**
1. **DO NOT USE PROVIDED CREDENTIALS** - All sample credentials are fake/modified
2. **INSTALL MT5 FIRST** - Download and install MetaTrader 5 from your broker
3. **USE YOUR OWN ACCOUNTS** - Configure with your real trading accounts
4. **PROTECT YOUR DATA** - Never commit real credentials or sensitive data

## 📋 Quick Installation Guide

### Step 1: Install MetaTrader 5
```bash
# Windows (from your broker)
# Download MT5 installer from your broker's website
# Install and create demo/real account

# Linux (using Wine)
sudo apt-get install wine
# Download Windows MT5 installer and run with Wine
```

### Step 2: Clone and Setup
```bash
git clone <this-repository>
cd mt5-broker-api

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure Your Own Accounts
```bash
# Copy example environment file
copy .env.example .env  # Windows
cp .env.example .env    # Linux/Mac

# Edit .env with YOUR REAL credentials
# NEVER commit this file to version control!
```

## 🔧 Configuration File (.env)
```
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379

# API Settings
API_HOST=0.0.0.0
API_PORT=4090
SECRET_KEY=your_secure_secret_key_here
```

## 🛡️ Security Warning

### **What's Been Modified in This Repository:**
- ✅ All user credentials replaced with `[REDACTED]`
- ✅ Trading data anonymized for demonstration
- ✅ Personal information removed
- ✅ Sample databases contain only test data
- ✅ API keys and secrets removed

### **What YOU Must Do:**
```python
# ❌ NEVER DO THIS:
MT5_LOGIN = "sample_user_123"  # FAKE - DON'T USE
MT5_PASSWORD = "fake_password" # FAKE - DON'T USE

# ✅ ALWAYS DO THIS:
MT5_LOGIN = os.getenv("MT5_LOGIN")    # YOUR REAL LOGIN
MT5_PASSWORD = os.getenv("MT5_PASSWORD") # YOUR REAL PASSWORD
```

## 🚀 Running the Application

### First Time Setup:
```bash
# 1. Install Redis (if not installed)
# Windows: Download from https://github.com/microsoftarchive/redis/releases
# Linux: sudo apt-get install redis-server

# 2. Start Redis
redis-server

# 3. In a NEW terminal, activate environment and run:
python main.py
```

### Verify MT5 Connection:
```python
import MetaTrader5 as mt5

# Test with YOUR credentials
if not mt5.initialize(
    login=your_real_login,
    password=your_real_password,
    server=your_real_server
):
    print("Failed to connect to MT5")
    print("Check: 1) MT5 is running, 2) Correct credentials, 3) Internet connection")
```

## 🔒 Security Best Practices

1. **Never hardcode credentials** - Always use environment variables
2. **Use `.gitignore`** - Ensure sensitive files aren't tracked
3. **Regular audits** - Check what data you're storing
4. **Access control** - Limit who can access the API
5. **Encryption** - Consider encrypting sensitive database fields

## 🆘 Troubleshooting

### "MT5 initialize() failed"
- ✅ Is MetaTrader 5 installed?
- ✅ Are you using YOUR correct credentials?
- ✅ Is the MT5 terminal running?
- ✅ Does your account allow API access?

### "No data in database"
- ✅ Did you run `data_updater.py`?
- ✅ Is Redis running?
- ✅ Are you querying the correct user database?
- ✅ Check `databases/your_user_id.db` exists

### "Authentication failed"
- ✅ Check your `.env` file values
- ✅ Verify MT5 account is active
- ✅ Ensure no firewall blocking connections

## 📄 License & Disclaimer

**Disclaimer**: This software is provided for educational and demonstration purposes. The maintainers are not responsible for any financial losses, data breaches, or issues arising from using real trading accounts. Always test with demo accounts first.

**Important**: By using this software with your real accounts, you acknowledge that you are responsible for:
- Securing your own credentials
- Protecting your financial data
- Complying with your broker's terms of service
- Managing your own risk exposure

---

## 🔗 Useful Resources

- [MetaTrader 5 Python Documentation](https://www.mql5.com/en/docs/integration/python_metatrader5)
- [FastAPI Security Tutorial](https://fastapi.tiangolo.com/tutorial/security/)
- [SQLite with Python Guide](https://docs.python.org/3/library/sqlite3.html)
- [Redis Installation Guide](https://redis.io/docs/getting-started/)

## 🆘 Getting Help

If you encounter issues:
1. Check the troubleshooting section above
2. Verify MT5 is properly installed with your accounts
3. Ensure all environment variables are set correctly
4. Consult the FastAPI and MT5 documentation

---

**Remember**: This repository contains only framework and demonstration code. All financial data and user credentials must be provided by you, the end user, through proper configuration with your own broker accounts.
