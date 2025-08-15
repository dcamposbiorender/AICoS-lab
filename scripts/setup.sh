#!/bin/bash
# AI Chief of Staff - Initial Setup Script

echo "🚀 Setting up AI Chief of Staff..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "Ensuring data directories exist..."
mkdir -p data/{archive/{slack,calendar,drive_changelog},facts,indices,insights,memory,state,logs}

# Set permissions
chmod +x scripts/*.sh

echo "✅ Setup complete! Run 'source venv/bin/activate' to activate the environment."