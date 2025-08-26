#!/bin/bash
# AI Chief of Staff - Data Backup Script

BACKUP_DIR="backups/$(date +%Y-%m-%d_%H-%M-%S)"
echo "🗄️  Creating backup at $BACKUP_DIR..."

mkdir -p "$BACKUP_DIR"

# Backup data directory
if [ -d "data" ]; then
    echo "Backing up data directory..."
    cp -r data "$BACKUP_DIR/"
fi

# Backup configuration files
echo "Backing up configuration..."
# Legacy scavenge config backup removed

# Create backup manifest
echo "Creating backup manifest..."
cat > "$BACKUP_DIR/manifest.txt" << EOF
AI Chief of Staff Backup
Created: $(date)
Data Directory Size: $(du -sh data 2>/dev/null | cut -f1 || echo "N/A")
EOF

echo "✅ Backup complete at $BACKUP_DIR"