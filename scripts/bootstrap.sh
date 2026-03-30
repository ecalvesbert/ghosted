#!/bin/bash
# Bootstrap the first admin account for Ghosted

API_URL="https://backend-production-1dee2.up.railway.app"

echo "=== Ghosted Admin Bootstrap ==="
echo ""

read -p "Email: " EMAIL
read -s -p "Password: " PASSWORD
echo ""
read -s -p "Admin Secret: " ADMIN_SECRET
echo ""
echo ""

echo "Creating admin account..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/api/admin/bootstrap" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"admin_secret\":\"$ADMIN_SECRET\"}")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
  echo "Admin account created successfully!"
  echo ""
  echo "Response: $BODY"
else
  echo "Failed (HTTP $HTTP_CODE)"
  echo "$BODY"
fi
