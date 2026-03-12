#!/bin/bash
# Clear all caches and restart the application

set -e

echo "🧹 Clearing all caches..."
echo ""

# Stop running servers
echo "1. Stopping servers..."
pkill -f "uvicorn" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
sleep 2
echo "   ✅ Servers stopped"
echo ""

# Clear frontend caches
echo "2. Clearing frontend caches..."
cd frontend
rm -rf node_modules/.vite
rm -rf dist
rm -rf .vite
echo "   ✅ Frontend caches cleared"
echo ""

# Go back to root
cd ..

# Clear Python cache
echo "3. Clearing Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
echo "   ✅ Python cache cleared"
echo ""

echo "✨ All caches cleared!"
echo ""
echo "📝 Next steps:"
echo "   1. Clear your browser cache (Ctrl+Shift+Delete or Cmd+Shift+Delete)"
echo "   2. Or use Incognito/Private mode"
echo "   3. Run: ./start.sh"
echo ""
echo "🔍 To verify CORS is working:"
echo "   Run: ./test_cors.sh"
echo ""

