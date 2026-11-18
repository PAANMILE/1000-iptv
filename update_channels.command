#!/bin/bash
cd "$(dirname "$0")"

echo "=========================================="
echo "  กำลังอัปเดตลิงก์ช่องรายการจาก TrueID"
echo "=========================================="

python3 fetch_streams.py

echo ""
echo "กำลังอัปโหลดขึ้น GitHub..."
git add channels.json fetch_streams.py update_channels.command true_tv.m3u
git commit -m "Update TrueID stream tokens"
git push origin main

echo ""
echo "เสร็จสิ้น! สามารถกด Refresh ใน Sparkle TV ได้เลย"
