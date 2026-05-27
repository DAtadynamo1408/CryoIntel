# start_prod.ps1
# Script to launch the production AI/ML Refrigeration Prediction Platform

echo "Starting Production Waitress Server in the background..."
Start-Process -NoNewWindow -FilePath "python" -ArgumentList "server.py"

Start-Sleep -Seconds 3

echo "Starting Cloudflare Tunnel for Live Hosting..."
.\cloudflared.exe tunnel --url http://127.0.0.1:5000

echo "Both services are running. Check the cloudflare output for the public URL."
