import os
from aiohttp import web

# Ekdum Premium Animated HTML Page
html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VIP Bot Status</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            background: linear-gradient(-45deg, #0a0a15, #1a1a30, #0f0c29, #000000);
            background-size: 400% 400%;
            animation: gradientBG 10s ease infinite;
            font-family: 'Courier New', Courier, monospace;
            color: white;
            overflow: hidden;
        }
        @keyframes gradientBG {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        .container {
            text-align: center;
            background: rgba(255, 255, 255, 0.03);
            padding: 50px 70px;
            border-radius: 20px;
            box-shadow: 0 0 30px rgba(255, 215, 0, 0.1); /* Subtle Gold Shadow */
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 215, 0, 0.2);
        }
        h1 {
            font-size: 3em;
            margin: 0;
            text-transform: uppercase;
            letter-spacing: 6px;
            text-shadow: 0 0 10px #FFD700, 0 0 20px #FFD700; /* Gold Glow */
            animation: glow 2s ease-in-out infinite alternate;
        }
        @keyframes glow {
            from { text-shadow: 0 0 10px #FFD700, 0 0 20px #FFD700; }
            to { text-shadow: 0 0 20px #FFA500, 0 0 30px #FFA500, 0 0 40px #FFA500; }
        }
        .status-box {
            margin-top: 30px;
            font-size: 1.3em;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 15px;
            background: rgba(0, 0, 0, 0.5);
            padding: 15px 25px;
            border-radius: 10px;
        }
        .pulse-dot {
            width: 18px;
            height: 18px;
            background-color: #00ff00;
            border-radius: 50%;
            box-shadow: 0 0 15px #00ff00;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 255, 0, 0.7); }
            70% { transform: scale(1); box-shadow: 0 0 0 15px rgba(0, 255, 0, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 255, 0, 0); }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>VIP SYSTEM ONLINE</h1>
        <div class="status-box">
            <div class="pulse-dot"></div>
            <span>Bot is actively monitoring the server...</span>
        </div>
    </div>
</body>
</html>
"""

async def handle(request):
    """HTML page return karega jab koi URL visit karega."""
    return web.Response(text=html_content, content_type='text/html')

async def start_web_server():
    """Background me aiohttp web server start karega."""
    app = web.Application()
    app.router.add_get('/', handle)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render dynamic PORT assign karta hai, by default 8080 use hoga
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    await site.start()
    print(f"🌐 Keep-Alive Web Server started on port {port}...")