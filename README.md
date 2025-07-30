# SmartUserExport - Enhanced Telegram Users API

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-green)
![Telethon](https://img.shields.io/badge/Telethon-1.36.0-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/your-template-id?referralCode=your-referral-code)

**SmartUserExport** is a groundbreaking, high-performance FastAPI-based Telegram bot data extraction tool that you may have never seen before! Built by [@ISmartCoder](https://t.me/TheSmartDev), this asynchronous API leverages Telethon to fetch comprehensive data about your Telegram bot, its users, groups, and channels with unparalleled efficiency. With low memory usage, robust error handling, and unique features, it’s the ultimate tool for bot owners to manage and analyze their Telegram ecosystem.

> **Important**: If you wish to share or reupload this project, you **must** give credit to the original owner, [@ISmartCoder](https://t.me/ISmartCoder). **Forking the repository** is highly recommended to contribute or build upon this work while respecting the original author. Reuploading without credit is not permitted.

## 🌟 Core Features

- **Comprehensive Data Extraction**: Retrieve detailed bot info, chats (groups, channels, private), and user data (ID, names, usernames, premium status).
- **High Performance**: Asynchronous FastAPI with `uvloop` for blazing-fast processing and low latency.
- **Low Memory Footprint**: Efficient caching and client management using Telethon to handle large datasets.
- **Concurrent Client Handling**: Safely manages multiple Telegram clients with asyncio locks for thread safety.
- **Structured JSON Output**: Clean, well-defined JSON responses for seamless integration with other systems.
- **Scalable Deployment**: Easily deploy on VPS or platforms like Railway with minimal configuration.

## 🔥 Special Features Analysis

What makes SmartUserExport stand out? Here’s a deep dive into its unique capabilities:

- **Optimized Data Fetching**: Uses `GetDifferenceRequest` to incrementally fetch updates, reducing API calls and handling large datasets efficiently. The script processes chats and users in batches, with a maximum duration of 600 seconds and up to 1000 batches, ensuring scalability.
- **Smart Chat Type Normalization**: Automatically categorizes chats (e.g., group, channel, private) and handles forbidden chats gracefully, avoiding errors.
- **Participant Fetching for Small Groups**: For groups with fewer than 5000 members, it fetches detailed participant data, including premium status, while skipping large chats to optimize performance.
- **Robust Error Handling**: Handles Telegram-specific errors like `FloodWaitError`, `PersistentTimestampEmptyError`, and `AuthKeyPermEmptyError` with automatic retries, state recovery, and graceful client cleanup.
- **Background Client Cleanup**: Ensures resources are freed after each request using FastAPI’s `BackgroundTasks`, preventing memory leaks.
- **Customizable Limits**: Configurable parameters like `max_duration`, `max_batches`, and `max_no_data` allow fine-tuning for specific use cases.
- **Interactive API Docs**: Built-in `/docs` endpoint for easy testing and exploration of the API.

These features combine to create a tool that’s both powerful and developer-friendly, making it a unique solution in the Telegram bot ecosystem.

## 🚀 Benefits

- **Broadcast Messages**: Send targeted messages to all bot users.
- **Data Backup**: Export and store user and group data for future use.
- **User Migration**: Seamlessly migrate users to a new bot if needed.
- **Analytics**: Analyze user engagement, premium status, and chat activity.
- **Developer-Friendly**: Intuitive API with clear documentation and error handling.

## 📋 API Endpoints

### 1. `GET /`
**Description**: Returns API metadata, including name, version, status, and endpoint details.  
**Parameters**: None  
**Example Response**:
```json
{
    "api_name": "Enhanced Telegram Users API",
    "version": "2.1.0",
    "status": "running",
    "description": "High-performance API for Telegram bot data with improved concurrency",
    "owners": [
        {"username": "@ISmartCoder"},
        {"username": "@theSmartDev"}
    ],
    "endpoints": [
        {
            "path": "/tgusers",
            "method": "GET",
            "description": "Fetch bot data including bot info, chats, and users",
            "parameters": [
                {
                    "name": "token",
                    "type": "string",
                    "required": true,
                    "description": "Telegram Bot Token"
                }
            ]
        },
        {
            "path": "/health",
            "method": "GET",
            "description": "Health check endpoint"
        },
        {
            "path": "/docs",
            "method": "GET",
            "description": "Get interactive API documentation"
        }
    ],
    "contact": "Contact @ISmartCoder or @theSmartDev for support"
}
```

### 2. `GET /health`
**Description**: Checks the API’s health and reports the number of active Telegram clients.  
**Parameters**: None  
**Example Response**:
```json
{
    "status": "healthy",
    "timestamp": 1740920040.123,
    "active_clients": 2
}
```

### 3. `GET /tgusers`
**Description**: Fetches bot data, including bot info, chats, and users, for the provided Telegram bot token.  
**Parameters**:
- `token` (string, required): Telegram Bot Token  
**Example Response**:
```json
{
    "bot_info": {
        "first_name": "Twilio service",
        "id": 7955215646,
        "username": "Twilos_bot"
    },
    "chats": [
        {
            "id": 1228946795,
            "members_count": null,
            "title": "a user",
            "type": "channel",
            "username": "HiddenSender"
        }
    ],
    "users": [
        {
            "id": 5991909954,
            "first_name": "MR Ruhul",
            "last_name": "Amin",
            "username": "Ruhulxr",
            "is_premium": false
        },
        {
            "id": 7955215646,
            "first_name": "Twilio service",
            "last_name": null,
            "username": "Twilos_bot",
            "is_premium": false
        },
        ...
    ],
    "total_chats": 1,
    "total_users": 12,
    "processing_time": 8.125
}
```

### 4. `GET /docs`
**Description**: Provides interactive API documentation powered by FastAPI’s Swagger UI.  
**Parameters**: None  
**Response**: Redirects to an interactive web interface for testing endpoints.

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Telegram API ID and API Hash (from [my.telegram.org](https://my.telegram.org))
- Git, pip, and a terminal environment

### Steps
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/abirxdhack/SmartUserExport.git
   cd SmartUserExport
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**:
   - Create a `.env` file or set environment variables:
     ```bash
     export API_ID=your_api_id
     export API_HASH=your_api_hash
     export PORT=8000  # Optional
     export HOST=0.0.0.0  # Optional
     ```
   - Replace `YOUR_API_ID` and `YOUR_API_HASH` in `main.py` with your credentials.

4. **Run the API**:
   ```bash
   python3 main.py
   ```

5. **Access the API**:
   - API Info: `http://localhost:8000`
   - Documentation: `http://localhost:8000/docs`
   - Bot Data: `http://localhost:8000/tgusers?token=your_bot_token`

## ☁️ Deploy on Railway

Deploy with one click:

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/your-template-id?referralCode=your-referral-code)

### Railway Setup
1. Click the "Deploy on Railway" button.
2. Set environment variables in Railway:
   - `API_ID`: Your Telegram API ID
   - `API_HASH`: Your Telegram API Hash
   - `PORT`: (Optional) 8000
3. Deploy and access your API via the provided URL.

## 🛠️ Configuration

- **Bot Token**: Required for `/tgusers`. Obtain from [@BotFather](https://t.me/BotFather).
- **API Credentials**: Update `YOUR_API_ID` and `YOUR_API_HASH` in `main.py`.
- **Tuning**:
  - Adjust `max_duration` (600s), `max_batches` (1000), and `max_no_data` (5) in `get_chats_and_users_fast`.
  - Enable `uvloop` for better performance (auto-enabled if installed).

## 🤝 Contributing

We encourage contributions via forking:
1. Fork the repository at [github.com/abirxdhack/SmartUserExport](https://github.com/abirxdhack/SmartUserExport)
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -m 'Add your feature'`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request

**Note**: Always credit [@ISmartCoder](https://t.me/ISmartCoder) when sharing or modifying this project. Forking is the preferred method to ensure proper attribution.

## 📢 Updates and Support

- **Updates Channel**: [@TheSmartDev](https://t.me/TheSmartDev)
- **Contact**: [@ISmartCoder](https://t.me/ISmartCoder)
- **GitHub**: [abirxdhack/SmartUserExport](https://github.com/abirxdhack/SmartUserExport)

## 📜 License

MIT License. See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- Created by [@ISmartCoder](https://t.me/ISmartCoder)
- Powered by [FastAPI](https://fastapi.tiangolo.com), [Telethon](https://docs.telethon.dev), and [uvloop](https://github.com/MagicStack/uvloop)

---

⭐ **Star this repository** to support this unique project!  
Happy coding! 🚀
