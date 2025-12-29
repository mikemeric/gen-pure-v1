#!/bin/bash
echo "🚀 Setting up Detection System..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
mkdir -p keys logs tmp/uploads
echo "✅ Setup complete!"
